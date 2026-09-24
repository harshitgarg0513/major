from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

class MyTopo(Topo):
    def build(self):
        s_core = self.addSwitch("s1", protocols="OpenFlow13")
        s_edge1 = self.addSwitch("s2", protocols="OpenFlow13")
        s_edge2 = self.addSwitch("s3", protocols="OpenFlow13")

        h_sensor1 = self.addHost("h_sensor1")
        h_camera1 = self.addHost("h_camera1")
        h_sensor2 = self.addHost("h_sensor2")
        h_server = self.addHost("h_server")

        # L1: Core <-> Edge1
        self.addLink(
            s_core,
            s_edge1,
            port1=1,
            port2=1,
            cls=TCLink,
            bw=1000,
            delay="5ms",
            max_queue_size=100,
        )

        # L2: Core <-> Edge2
        self.addLink(
            s_core,
            s_edge2,
            port1=2,
            port2=1,
            cls=TCLink,
            bw=1000,
            delay="5ms",
            max_queue_size=100,
        )

        # Connect hosts to Edge1
        self.addLink(h_sensor1, s_edge1, port1=1, port2=2, cls=TCLink, bw=10, delay="2ms")
        self.addLink(h_camera1, s_edge1, port1=1, port2=3, cls=TCLink, bw=100, delay="2ms")

        # Connect hosts to Edge2
        self.addLink(h_sensor2, s_edge2, port1=1, port2=2, cls=TCLink, bw=10, delay="2ms")
        self.addLink(h_server, s_edge2, port1=1, port2=3, cls=TCLink, bw=1000, delay="1ms")


topos = {"mytopo": MyTopo}


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
    print("Example traffic: h_server iperf3 -s -D && h_camera1 iperf3 -c h_server -b 10M -t 120")
    CLI(net)
    net.stop()
