import time
import uuid
import yaml
import sqlite3
import os
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.ofproto import ofproto_v1_3

POLL_INTERVAL_MS = 1000

class TelemetryPoller(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TelemetryPoller, self).__init__(*args, **kwargs)
        self.datapaths = {}
        
        # Load topology to map dpid+port to link_id
        # We assume dpid is the integer part of the node_id (e.g. s1 -> 1)
        # We expect to run from within the telemetry/ folder or project root
        topo_path = os.path.join(os.path.dirname(__file__), '../Day-0/topology_registry.yaml')
        if not os.path.exists(topo_path):
            topo_path = os.path.join(os.path.dirname(__file__), '../../Day-0/topology_registry.yaml')
            
        with open(topo_path, 'r') as f:
            self.topology = yaml.safe_load(f)

        self.port_to_link = {}
        self.link_endpoints = {}
        
        for link in self.topology.get('links', []):
            link_id = link['link_id']
            
            def get_dpid_port(endpoint):
                dpid = int(endpoint['node_id'].replace('s', ''))
                return dpid, endpoint['port']
                
            ep_a = get_dpid_port(link['endpoint_a'])
            ep_b = get_dpid_port(link['endpoint_b'])
            
            self.port_to_link[ep_a] = link_id
            self.port_to_link[ep_b] = link_id
            self.link_endpoints[link_id] = [ep_a, ep_b]

        # State tracking for counter deltas
        # (dpid, port) -> {'ts': float, 'tx_bytes': int, 'tx_packets': int, 'tx_dropped': int}
        self.port_stats = {}
        
        # Ephemeral storage for aggregated metrics per cycle
        self.current_poll_stats = {}

        # SQLite Connection
        db_path = os.path.join(os.path.dirname(__file__), '../test.db')
        self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.db_conn.execute('PRAGMA journal_mode=WAL;')

        # Start polling thread
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info('Register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        else:
            if datapath.id in self.datapaths:
                self.logger.info('Unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            # Prepare new cycle aggregation
            self.current_poll_stats = {
                link_id: {
                    'tx_bytes_delta': 0, 'tx_dropped_delta': 0, 'tx_packets_delta': 0, 
                    'active_flows': 0, 'ep_count': 0, 'delta_time_sum': 0.0
                }
                for link_id in self.link_endpoints
            }
            
            for dp in self.datapaths.values():
                self._request_stats(dp)
            
            # Wait for interval (also gives switches time to reply asynchronously)
            hub.sleep(POLL_INTERVAL_MS / 1000.0)
            
            # After waiting, we compute and persist the collected deltas
            self._write_telemetry()

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Request Port stats
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

        # Request Flow stats
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        now = time.time()
        
        for stat in body:
            port_no = stat.port_no
            key = (dpid, port_no)
            
            if key not in self.port_to_link:
                continue
                
            link_id = self.port_to_link[key]
            
            if key in self.port_stats:
                prev = self.port_stats[key]
                delta_time = now - prev['ts']
                
                # We only process if time delta makes sense
                if delta_time > 0:
                    delta_tx_bytes = stat.tx_bytes - prev['tx_bytes']
                    delta_tx_packets = stat.tx_packets - prev['tx_packets']
                    delta_tx_dropped = stat.tx_dropped - prev['tx_dropped']
                    
                    # Accumulate for this link across both endpoints
                    ls = self.current_poll_stats[link_id]
                    ls['tx_bytes_delta'] += max(0, delta_tx_bytes)
                    ls['tx_dropped_delta'] += max(0, delta_tx_dropped)
                    ls['tx_packets_delta'] += max(0, delta_tx_packets)
                    ls['ep_count'] += 1
                    ls['delta_time_sum'] += delta_time

            # Update state for next poll
            self.port_stats[key] = {
                'ts': now,
                'tx_bytes': stat.tx_bytes,
                'tx_packets': stat.tx_packets,
                'tx_dropped': stat.tx_dropped
            }

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        ofproto = ev.msg.datapath.ofproto
        
        # Count active flows pointing to each port
        port_flows = {}
        for stat in body:
            for inst in stat.instructions:
                if inst.type == ofproto.OFPIT_APPLY_ACTIONS:
                    for action in inst.actions:
                        if action.type == ofproto.OFPAT_OUTPUT:
                            port_no = action.port
                            port_flows[port_no] = port_flows.get(port_no, 0) + 1
                            
        for port_no, count in port_flows.items():
            key = (dpid, port_no)
            if key in self.port_to_link:
                link_id = self.port_to_link[key]
                # Increment active flows mapping to this link
                self.current_poll_stats[link_id]['active_flows'] += count

    def _write_telemetry(self):
        cursor = self.db_conn.cursor()
        now_ms = int(time.time() * 1000)
        
        for link_id, stats in self.current_poll_stats.items():
            if stats['ep_count'] == 0:
                continue # Skip if no data received for this link
                
            avg_delta_time = stats['delta_time_sum'] / stats['ep_count']
            
            # throughput_mbps = (bytes * 8) / seconds / 1,000,000
            throughput_mbps = (stats['tx_bytes_delta'] * 8) / avg_delta_time / 1000000.0
            
            # packet_loss_pct = drops / (packets + drops)
            total_pkts = stats['tx_packets_delta'] + stats['tx_dropped_delta']
            packet_loss_pct = 0.0
            if total_pkts > 0:
                packet_loss_pct = (stats['tx_dropped_delta'] / float(total_pkts)) * 100.0
                
            active_flows = stats['active_flows']
            
            record_id = str(uuid.uuid4())
            
            try:
                cursor.execute(
                    '''
                    INSERT INTO link_telemetry (
                        record_id, ts_epoch_ms, link_id, latency_ms, latency_method, 
                        packet_loss_pct, throughput_mbps, utilization_pct, 
                        queue_length, active_flows, poll_interval_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        record_id, now_ms, link_id, 
                        0.0, 'lldp_probe', # Latency placeholders
                        packet_loss_pct, throughput_mbps, 
                        0.0, 0, # Utilization/Queue placeholders
                        active_flows, POLL_INTERVAL_MS
                    )
                )
            except Exception as e:
                self.logger.error("DB Insert failed: %s", e)
                
        self.db_conn.commit()
