#!/usr/bin/env python3
"""
Phase 1 — Member 4 proof: Dijkstra + k-shortest paths on a hand-drawn 6-node sample graph.

Graph (directed edge weights = cost):
        h1
         | 1
        s1 --3-- s3 --2-- s4
         | 2       | 1
        s2 --4-----+
         |
         h2

Nodes: h1, s1, s2, s3, s4, h2  (6 nodes)
Primary path h1->h2: h1-s1-s2-h2 (cost 1+2+1=4)
Alternate via s3/s4 should be longer but valid.
"""

from __future__ import annotations

import sys

import networkx as nx


def build_sample_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    edges = [
        ("h1", "s1", 1),
        ("s1", "s2", 2),
        ("s1", "s3", 3),
        ("s2", "h2", 1),
        ("s2", "s4", 4),
        ("s3", "s4", 1),
        ("s4", "h2", 2),
    ]
    for u, v, w in edges:
        g.add_edge(u, v, weight=w)
    return g


def dijkstra_path(g: nx.DiGraph, source: str, target: str) -> tuple[list[str], float]:
    path = nx.dijkstra_path(g, source, target, weight="weight")
    cost = nx.dijkstra_path_length(g, source, target, weight="weight")
    return path, cost


def k_shortest_paths(g: nx.DiGraph, source: str, target: str, k: int = 3) -> list[tuple[list[str], float]]:
    paths = []
    for path in nx.shortest_simple_paths(g, source, target, weight="weight"):
        cost = sum(g[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))
        paths.append((path, cost))
        if len(paths) >= k:
            break
    return paths


def main() -> int:
    print("=== Phase 1 / Member 4 — Path algorithms demo ===")
    g = build_sample_graph()
    print(f"Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} directed edges")

    primary, primary_cost = dijkstra_path(g, "h1", "h2")
    print(f"Dijkstra h1->h2: {' -> '.join(primary)} (cost {primary_cost})")

    alts = k_shortest_paths(g, "h1", "h2", k=3)
    print("K-shortest paths (k=3):")
    for i, (path, cost) in enumerate(alts, 1):
        print(f"  {i}. {' -> '.join(path)} (cost {cost})")

    expected_primary = ["h1", "s1", "s2", "h2"]
    if primary != expected_primary:
        print(f"FAIL: expected primary path {expected_primary}, got {primary}")
        return 1

    if len(alts) < 2:
        print("FAIL: expected at least 2 distinct simple paths")
        return 1

    if alts[0][0] != primary:
        print("FAIL: k-shortest first path should match Dijkstra")
        return 1

    print("PASS: Dijkstra and k-shortest paths return sane alternates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
