from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

class MyTopo(Topo):
    def build(self):
        # Add switches
        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        
        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        
        # Add links
        # L1 is s1 port 1 to s2 port 1 (according to topology_registry.yaml)
        # Adding a 10ms delay for latency probe verification
        self.addLink(s1, s2, port1=1, port2=1, delay='10ms')
        
        # Connect hosts (using port 2)
        self.addLink(h1, s1, port1=1, port2=2)
        self.addLink(h2, s2, port1=1, port2=2)

topos = {'mytopo': (MyTopo, {})}

if __name__ == '__main__':
    setLogLevel('info')
    topo = MyTopo()
    # Connect to local OS-Ken controller
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653), link=TCLink)

    
    net.start()
    print("Mininet topology started! You can now run iperf3 tests.")
    print("Example: mininet> h1 iperf3 -s -D")
    print("         mininet> h2 iperf3 -c h1 -b 10M -t 60")
    CLI(net)
    net.stop()
