import time
import struct
import uuid
import yaml
import sqlite3
import os

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet

POLL_INTERVAL_MS = 1000
PROBE_ETHERTYPE = 0x07C3

class LatencyProbe(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LatencyProbe, self).__init__(*args, **kwargs)
        self.datapaths = {}

        # Load topology
        topo_path = os.path.join(os.path.dirname(__file__), '../contracts/topology_registry.yaml')
        with open(topo_path, 'r') as f:
            self.topology = yaml.safe_load(f)

        self.links = self.topology.get('links', [])
        
        # SQLite Connection
        db_path = os.path.join(os.path.dirname(__file__), '../test.db')
        self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.db_conn.execute('PRAGMA journal_mode=WAL;')
        self.db_conn.execute('PRAGMA foreign_keys=ON;')

        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

        # Install rule to catch our custom probe packets
        match = parser.OFPMatch(eth_type=PROBE_ETHERTYPE)
        # Send to controller, no buffer
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # Priority must be high enough to match before generic forwarding
        mod = parser.OFPFlowMod(datapath=datapath, priority=65000, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state != MAIN_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('Unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for link in self.links:
                self._send_probe(link)
            hub.sleep(POLL_INTERVAL_MS / 1000.0)

    def _send_probe(self, link):
        link_id = link['link_id']
        ep_a = link['endpoint_a']
        
        dpid_a = int(ep_a['node_id'].replace('s', ''))
        port_a = ep_a['port']
        
        if dpid_a not in self.datapaths:
            return
            
        datapath = self.datapaths[dpid_a]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Build packet
        pkt = packet.Packet()
        eth = ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff',
                                src='00:00:00:00:00:00', # Dummy source
                                ethertype=PROBE_ETHERTYPE)
        pkt.add_protocol(eth)
        
        # Payload: double precision timestamp (8 bytes) + link_id string (up to 16 bytes for padding)
        now = time.time()
        link_id_bytes = link_id.encode('utf-8').ljust(16, b'\x00')
        payload = struct.pack('!d16s', now, link_id_bytes)
        pkt.add_protocol(payload)
        pkt.serialize()

        actions = [parser.OFPActionOutput(port_a)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=pkt.data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        if not eth or eth.ethertype != PROBE_ETHERTYPE:
            return
            
        recv_time = time.time()
        
        # Extract payload
        # os_ken pkt.protocols[-1] is the raw bytes if no specific protocol is parsed
        raw_payload = pkt.protocols[-1]
        if type(raw_payload) == bytes and len(raw_payload) >= 24:
            send_time, link_id_bytes = struct.unpack('!d16s', raw_payload[:24])
            link_id = link_id_bytes.rstrip(b'\x00').decode('utf-8')
            
            # The calculation specified by the user: (receive_time - send_time) / 2
            # Converted to milliseconds
            latency_ms = ((recv_time - send_time) * 1000.0) / 2.0
            
            self._write_latency(link_id, latency_ms)

    def _write_latency(self, link_id, latency_ms):
        cursor = self.db_conn.cursor()
        now_ms = int(time.time() * 1000)
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
                    record_id, now_ms, link_id, latency_ms, 'lldp_probe', 
                    0.0, 0.0, 0.0, 
                    0, 0, POLL_INTERVAL_MS
                )
            )
            self.db_conn.commit()
        except Exception as e:
            self.logger.error("DB Insert failed: %s", e)
