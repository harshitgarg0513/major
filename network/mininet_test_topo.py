from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

# Inter-switch link capacity must match contracts/topology_registry.yaml capacity_mbps.
L1_BW_MBPS = 100
L1_DELAY = "10ms"
L1_MAX_QUEUE = 100  # packets — saturate with iperf to verify queue_length > 0


class MyTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")
        h1 = self.addHost("h1")
        h2 = self.addHost("h2")

        # L1: s1:1 <-> s2:1 (registry-backed link_id L1)
        self.addLink(
            s1,
            s2,
            port1=1,
            port2=1,
            cls=TCLink,
            bw=L1_BW_MBPS,
            delay=L1_DELAY,
            max_queue_size=L1_MAX_QUEUE,
        )

        self.addLink(h1, s1, port1=1, port2=2)
        self.addLink(h2, s2, port1=1, port2=2)


topos = {"mytopo": (MyTopo, {})}


if __name__ == "__main__":
    setLogLevel("info")
    topo = MyTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6653),
        link=TCLink,
    )
    net.start()
    print("Mininet topology started.")
    print("Generate registry: python3 network/topology_builder.py")
    print("Example traffic: h1 iperf3 -s -D && h2 iperf3 -c h1 -b 10M -t 120")
    CLI(net)
    net.stop()
