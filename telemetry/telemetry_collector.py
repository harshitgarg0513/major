"""
Unified link telemetry collector — single OS-Ken app.

Merges OpenFlow counter polling, LLDP-style latency probes, and tc/netem
queue backlog into ONE complete link_telemetry row per (link, poll cycle).
"""

from __future__ import annotations

import os
import sqlite3
import struct
import time
import uuid
from typing import Any

import yaml
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.lib.packet import ethernet, packet
from os_ken.ofproto import ofproto_v1_3

try:
    from pyroute2 import IPRoute
except ImportError:  # pragma: no cover — local Mac dev without Linux tc
    IPRoute = None  # type: ignore[misc, assignment]

POLL_INTERVAL_MS = 1000
PROBE_ETHERTYPE = 0x07C3
CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "../contracts")
DB_PATH = os.path.join(os.path.dirname(__file__), "../test.db")


def mininet_iface(node_id: str, port: int) -> str:
    """Mininet default veth naming: s1-eth1, h1-eth0, etc."""
    if node_id.startswith("s"):
        return f"{node_id}-eth{port}"
    return f"{node_id}-eth{port - 1}"


def read_queue_length(ifnames: list[str]) -> int:
    """Read tc/netem qdisc backlog (packets) via pyroute2; 0 if unavailable."""
    if IPRoute is None or not ifnames:
        return 0

    max_qlen = 0
    try:
        with IPRoute() as ip:
            for ifname in ifnames:
                idx_list = ip.link_lookup(ifname=ifname)
                if not idx_list:
                    continue
                idx = idx_list[0]
                for qdisc in ip.get_qdiscs(index=idx):
                    qlen = 0
                    tca_stats = qdisc.get_attr('TCA_STATS')
                    if tca_stats and isinstance(tca_stats, dict):
                        qlen = tca_stats.get('qlen', 0) or tca_stats.get('backlog', 0)
                    else:
                        tca_stats2 = qdisc.get_attr('TCA_STATS2')
                        if tca_stats2 and hasattr(tca_stats2, 'get_attr'):
                            queue_stats = tca_stats2.get_attr('TCA_STATS_QUEUE')
                            if queue_stats and isinstance(queue_stats, dict):
                                qlen = queue_stats.get('qlen', 0) or queue_stats.get('backlog', 0)
                    
                    max_qlen = max(max_qlen, int(qlen))
    except OSError:
        return 0
    return max_qlen


class LinkTelemetryCollector(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.datapaths: dict[int, Any] = {}
        self.mac_to_port: dict[int, dict[str, int]] = {}

        with open(os.path.join(CONTRACTS_DIR, "topology_registry.yaml"), encoding="utf-8") as f:
            self.topology = yaml.safe_load(f)

        self.port_to_link: dict[tuple[int, int], str] = {}
        self.link_meta: dict[str, dict[str, Any]] = {}
        self.link_endpoints: dict[str, list[tuple[int, int]]] = {}

        for link in self.topology.get("links", []):
            link_id = link["link_id"]

            def dpid_port(endpoint: dict) -> tuple[int, int]:
                return int(endpoint["node_id"].replace("s", "")), endpoint["port"]

            ep_a = dpid_port(link["endpoint_a"])
            ep_b = dpid_port(link["endpoint_b"])
            self.port_to_link[ep_a] = link_id
            self.port_to_link[ep_b] = link_id
            self.link_endpoints[link_id] = [ep_a, ep_b]

            ifaces = link.get("mininet_ifaces")
            if not ifaces:
                ifaces = [
                    mininet_iface(link["endpoint_a"]["node_id"], link["endpoint_a"]["port"]),
                    mininet_iface(link["endpoint_b"]["node_id"], link["endpoint_b"]["port"]),
                ]

            self.link_meta[link_id] = {
                "capacity_mbps": link.get("capacity_mbps", 100),
                "configured_delay_ms": link.get("configured_delay_ms"),
                "endpoint_a": link["endpoint_a"],
                "endpoint_b": link["endpoint_b"],
                "ifaces": ifaces,
            }

        # Per-port counter history for delta math
        self.port_stats: dict[tuple[int, int], dict[str, Any]] = {}

        # Latest probe latency per link (carried forward between cycles)
        self.last_latency: dict[str, tuple[float, str]] = {}

        # Latency measured during the current poll window
        self.cycle_latency: dict[str, tuple[float, str]] = {}

        # Aggregated OpenFlow stats for the current poll window
        self.current_poll_stats: dict[str, dict[str, Any]] = {}

        self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db_conn.execute("PRAGMA journal_mode=WAL;")
        self.db_conn.execute("PRAGMA foreign_keys=ON;")

        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev: Any) -> None:
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

        match = parser.OFPMatch(eth_type=PROBE_ETHERTYPE)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=65000, match=match, instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER])
    def _state_change_handler(self, ev: Any) -> None:
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("Register datapath: %016x", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif datapath.id in self.datapaths:
            self.logger.info("Unregister datapath: %016x", datapath.id)
            del self.datapaths[datapath.id]

    def _monitor(self) -> None:
        while True:
            self.cycle_latency = {}
            self.current_poll_stats = {
                link_id: {
                    "tx_bytes_delta": 0,
                    "tx_packets_delta": 0,
                    "rx_packets_delta": 0,
                    "active_flows": 0,
                    "ep_count": 0,
                    "delta_time_sum": 0.0,
                    "port_deltas": {},
                }
                for link_id in self.link_endpoints
            }

            for dp in self.datapaths.values():
                self._request_stats(dp)

            for link_id, meta in self.link_meta.items():
                self._send_probe(link_id, meta["endpoint_a"])

            hub.sleep(POLL_INTERVAL_MS / 1000.0)
            self._write_telemetry()

    def _request_stats(self, datapath: Any) -> None:
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        datapath.send_msg(parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY))
        datapath.send_msg(parser.OFPFlowStatsRequest(datapath))

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev: Any) -> None:
        dpid = ev.msg.datapath.id
        now = time.time()

        for stat in ev.msg.body:
            key = (dpid, stat.port_no)
            if key not in self.port_to_link:
                continue

            link_id = self.port_to_link[key]
            ls = self.current_poll_stats[link_id]

            if key in self.port_stats:
                prev = self.port_stats[key]
                delta_time = now - prev["ts"]
                if delta_time > 0:
                    ls["tx_bytes_delta"] += max(0, stat.tx_bytes - prev["tx_bytes"])
                    ls["tx_packets_delta"] += max(0, stat.tx_packets - prev["tx_packets"])
                    ls["rx_packets_delta"] += max(0, stat.rx_packets - prev["rx_packets"])
                    ls["ep_count"] += 1
                    ls["delta_time_sum"] += delta_time
                    ls["port_deltas"][key] = {
                        "tx_packets": max(0, stat.tx_packets - prev["tx_packets"]),
                        "rx_packets": max(0, stat.rx_packets - prev["rx_packets"]),
                    }

            self.port_stats[key] = {
                "ts": now,
                "tx_bytes": stat.tx_bytes,
                "tx_packets": stat.tx_packets,
                "rx_packets": stat.rx_packets,
            }

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev: Any) -> None:
        dpid = ev.msg.datapath.id
        ofproto = ev.msg.datapath.ofproto
        port_flows: dict[int, int] = {}

        for stat in ev.msg.body:
            for inst in stat.instructions:
                if inst.type == ofproto.OFPIT_APPLY_ACTIONS:
                    for action in inst.actions:
                        if action.type == ofproto.OFPAT_OUTPUT:
                            port_flows[action.port] = port_flows.get(action.port, 0) + 1

        for port_no, count in port_flows.items():
            key = (dpid, port_no)
            if key in self.port_to_link:
                self.current_poll_stats[self.port_to_link[key]]["active_flows"] += count

    def _send_probe(self, link_id: str, endpoint: dict) -> None:
        dpid = int(endpoint["node_id"].replace("s", ""))
        port = endpoint["port"]
        if dpid not in self.datapaths:
            return

        datapath = self.datapaths[dpid]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet()
        eth = ethernet.ethernet(
            dst="ff:ff:ff:ff:ff:ff",
            src="00:00:00:00:00:00",
            ethertype=PROBE_ETHERTYPE,
        )
        pkt.add_protocol(eth)
        payload = struct.pack("!d16s", time.time(), link_id.encode("utf-8").ljust(16, b"\x00"))
        pkt.add_protocol(payload)
        pkt.serialize()

        datapath.send_msg(
            parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=ofproto.OFPP_CONTROLLER,
                actions=[parser.OFPActionOutput(port)],
                data=pkt.data,
            )
        )

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            buffer_id=buffer_id if buffer_id else ofproto.OFP_NO_BUFFER,
            priority=priority,
            match=match,
            instructions=inst,
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev: Any) -> None:
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth:
            return

        if eth.ethertype == PROBE_ETHERTYPE:
            raw = pkt.protocols[-1]
            if not isinstance(raw, (bytes, bytearray)) or len(raw) < 24:
                return

            send_time, link_id_bytes = struct.unpack("!d16s", raw[:24])
            link_id = link_id_bytes.rstrip(b"\x00").decode("utf-8")
            latency_ms = ((time.time() - send_time) * 1000.0) / 2.0
            self.cycle_latency[link_id] = (latency_ms, "lldp_probe")
            self.last_latency[link_id] = (latency_ms, "lldp_probe")
            return

        # L2 forwarding for normal traffic
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        if dst == "ff:ff:ff:ff:ff:ff":
            out_port = ofproto.OFPP_FLOOD
        else:
            self.mac_to_port[dpid][src] = in_port
            out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None,
        )
        datapath.send_msg(out)

    def _resolve_latency(self, link_id: str) -> tuple[float, str] | None:
        if link_id in self.cycle_latency:
            return self.cycle_latency[link_id]
        if link_id in self.last_latency:
            return self.last_latency[link_id]
        configured = self.link_meta[link_id].get("configured_delay_ms")
        if configured is not None:
            return float(configured), "configured_static"
        return None

    def _compute_packet_loss_pct(self, link_id: str, stats: dict[str, Any]) -> float:
        """
        End-to-end link loss proxy: compare tx on one endpoint vs rx on the peer.
        Not wire-level loss — measures forwarding mismatch across the link pair.
        """
        endpoints = self.link_endpoints.get(link_id, [])
        if len(endpoints) != 2:
            return 0.0

        port_deltas = stats.get("port_deltas", {})
        ep_a, ep_b = endpoints
        a_tx = port_deltas.get(ep_a, {}).get("tx_packets", 0)
        b_rx = port_deltas.get(ep_b, {}).get("rx_packets", 0)
        b_tx = port_deltas.get(ep_b, {}).get("tx_packets", 0)
        a_rx = port_deltas.get(ep_a, {}).get("rx_packets", 0)

        losses = []
        if a_tx > 0:
            losses.append(max(0.0, (a_tx - b_rx) / a_tx * 100.0))
        if b_tx > 0:
            losses.append(max(0.0, (b_tx - a_rx) / b_tx * 100.0))
        return min(100.0, max(losses)) if losses else 0.0

    def _write_telemetry(self) -> None:
        cursor = self.db_conn.cursor()
        now_ms = int(time.time() * 1000)

        for link_id, stats in self.current_poll_stats.items():
            if stats["ep_count"] == 0:
                continue

            expected_eps = len(self.link_endpoints.get(link_id, []))
            is_partial = stats["ep_count"] < expected_eps
            if is_partial:
                self.logger.warning(
                    "Partial OpenFlow stats for %s: ep_count=%d expected=%d",
                    link_id,
                    stats["ep_count"],
                    expected_eps,
                )

            latency = self._resolve_latency(link_id)
            if latency is None:
                self.logger.debug("Skipping %s — no latency available yet", link_id)
                continue

            latency_ms, latency_method = latency
            avg_delta_time = stats["delta_time_sum"] / stats["ep_count"]
            throughput_mbps = (stats["tx_bytes_delta"] * 8) / avg_delta_time / 1_000_000.0
            packet_loss_pct = self._compute_packet_loss_pct(link_id, stats)
            capacity = self.link_meta[link_id]["capacity_mbps"]
            utilization_pct = min(100.0, (throughput_mbps / capacity) * 100.0) if capacity else 0.0
            queue_length = read_queue_length(self.link_meta[link_id]["ifaces"])

            try:
                cursor.execute(
                    """
                    INSERT INTO link_telemetry (
                        record_id, ts_epoch_ms, link_id, latency_ms, latency_method,
                        packet_loss_pct, throughput_mbps, utilization_pct,
                        queue_length, active_flows, poll_interval_ms, is_partial
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        now_ms,
                        link_id,
                        latency_ms,
                        latency_method,
                        packet_loss_pct,
                        throughput_mbps,
                        utilization_pct,
                        queue_length,
                        stats["active_flows"],
                        POLL_INTERVAL_MS,
                        1 if is_partial else 0,
                    ),
                )
            except sqlite3.Error as exc:
                self.logger.error("DB insert failed for %s: %s", link_id, exc)

        self.db_conn.commit()
