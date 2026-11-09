"""
J.A.R.V.I.S. Dependency Graph and Topology Engine.
Maintains directed microservice dependency topology with provenance tracking,
edge confidence scores, reachability walks, and inferred graph fallbacks.
"""

import networkx as nx
from typing import Dict, List, Set, Optional, Tuple
from .schema import TopologyGraph, TopologyNode, TopologyEdge
from .config import SERVICE_MANIFEST


class DependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.inferred_mode = False
        self._build_from_manifest()

    def _build_from_manifest(self):
        """Constructs canonical topology from declared manifest."""
        self.graph.clear()
        self.inferred_mode = False

        for name, data in SERVICE_MANIFEST.items():
            self.graph.add_node(
                name,
                tier=data["tier"],
                host=data["host"],
                is_external=data["is_external"]
            )

        for name, data in SERVICE_MANIFEST.items():
            for dep in data["dependencies"]:
                # Edge: Caller -> Callee (name depends on dep)
                self.graph.add_edge(
                    name,
                    dep,
                    provenance="manifest",
                    confidence=0.90,
                    latency_baseline_ms=15.0
                )

    def add_trace_edge(self, caller: str, callee: str):
        """Adds or reinforces an edge observed in distributed trace spans."""
        if not self.graph.has_node(caller):
            self.graph.add_node(caller, tier="service", host="unknown", is_external=False)
        if not self.graph.has_node(callee):
            self.graph.add_node(callee, tier="service", host="unknown", is_external=False)

        self.graph.add_edge(
            caller,
            callee,
            provenance="trace",
            confidence=0.95,
            latency_baseline_ms=20.0
        )

    def set_inferred_mode(self, inferred_edges: List[Tuple[str, str]]):
        """Used when telemetry has no declared topology: builds inferred graph and flags it."""
        self.inferred_mode = True
        self.graph.clear()
        for src, dst in inferred_edges:
            self.graph.add_node(src, tier="inferred", host="unknown", is_external=False)
            self.graph.add_node(dst, tier="inferred", host="unknown", is_external=False)
            self.graph.add_edge(src, dst, provenance="inferred", confidence=0.40, latency_baseline_ms=30.0)

    def get_callees(self, service: str) -> List[str]:
        """Services that `service` calls directly (its downstream dependencies)."""
        if not self.graph.has_node(service):
            return []
        return list(self.graph.successors(service))

    def get_callers(self, service: str) -> List[str]:
        """Services that call `service` directly (its upstream clients)."""
        if not self.graph.has_node(service):
            return []
        return list(self.graph.predecessors(service))

    def get_all_impacted_services(self, root_service: str) -> Set[str]:
        """
        Traverses reverse calling edges: if root_service fails,
        all services that directly or indirectly depend on it are impacted.
        """
        if not self.graph.has_node(root_service):
            return set()
        
        # Inverted graph: Callee -> Caller
        reversed_g = self.graph.reverse()
        impacted = nx.descendants(reversed_g, root_service)
        return impacted

    def get_shortest_path_distance(self, u: str, v: str) -> Optional[int]:
        """Undirected shortest path distance between two services."""
        if not self.graph.has_node(u) or not self.graph.has_node(v):
            return None
        undirected = self.graph.to_undirected()
        try:
            return nx.shortest_path_length(undirected, u, v)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def export_topology(self) -> TopologyGraph:
        """Exports graph in schema format for React Cytoscape/Force UI."""
        nodes = []
        for n, d in self.graph.nodes(data=True):
            nodes.append(TopologyNode(
                id=n,
                name=n,
                tier=d.get("tier", "service"),
                host=d.get("host", "node-1"),
                is_external=d.get("is_external", False)
            ))

        edges = []
        for u, v, d in self.graph.edges(data=True):
            edges.append(TopologyEdge(
                source=u,
                target=v,
                provenance=d.get("provenance", "manifest"),
                confidence=d.get("confidence", 0.90),
                latency_baseline_ms=d.get("latency_baseline_ms", 20.0)
            ))

        return TopologyGraph(nodes=nodes, edges=edges)


# Global topology graph singleton
dependency_graph = DependencyGraph()
