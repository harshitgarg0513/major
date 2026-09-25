#!/usr/bin/env python3
"""
Phase 2 — Path Computation with Constraints (CSPF)
"""

from __future__ import annotations

import sys
import os
import yaml
import networkx as nx

def build_registry_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'contracts', 'topology_registry.yaml')
    with open(config_path, 'r') as f:
        topo = yaml.safe_load(f)
    for link in topo.get('links', []):
        u = link['endpoint_a']['node_id']
        v = link['endpoint_b']['node_id']
        cap = link.get('capacity_mbps', 0)
        dly = link.get('configured_delay_ms', 0.0)
        g.add_edge(u, v, weight=1, capacity=cap, delay=dly)
        g.add_edge(v, u, weight=1, capacity=cap, delay=dly)
    return g

def build_sample_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # edges: (u, v, weight, capacity_mbps, delay_ms)
    edges = [
        ("h1", "s1", 1, 100, 2),
        ("s1", "s2", 2, 10, 5),
        ("s1", "s3", 3, 100, 5),
        ("s2", "h2", 1, 100, 2),
        ("s2", "s4", 4, 10, 10),
        ("s3", "s4", 1, 100, 5),
        ("s4", "h2", 2, 100, 2),
    ]
    for u, v, w, cap, dly in edges:
        g.add_edge(u, v, weight=w, capacity=cap, delay=dly)
    return g

def cspf_path(g: nx.DiGraph, source: str, target: str, min_bw: float = 0, max_delay_per_link: float = float('inf')) -> tuple[list[str], float]:
    """Constraint-Shortest Path First filtering links that do not meet constraints."""
    filtered_g = nx.DiGraph()
    for u, v, data in g.edges(data=True):
        if data.get('capacity', 0) >= min_bw and data.get('delay', 0) <= max_delay_per_link:
            filtered_g.add_edge(u, v, **data)
    
    if not nx.has_path(filtered_g, source, target):
        return [], float('inf')
        
    path = nx.dijkstra_path(filtered_g, source, target, weight="weight")
    cost = nx.dijkstra_path_length(filtered_g, source, target, weight="weight")
    return path, cost

def main() -> int:
    print("=== Phase 2 / Path computation with constraints ===")
    g = build_sample_graph()
    
    # 1. No constraints
    path, cost = cspf_path(g, "h1", "h2")
    print(f"No constraints: {' -> '.join(path)} (cost {cost})")
    
    # 2. Bandwidth constraint (>10)
    path_bw, cost_bw = cspf_path(g, "h1", "h2", min_bw=50)
    print(f"Min BW 50: {' -> '.join(path_bw)} (cost {cost_bw})")

    return 0

if __name__ == "__main__":
    sys.exit(main())
