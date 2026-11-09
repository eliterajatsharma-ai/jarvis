"""
J.A.R.V.I.S. Event Correlation & Incident Clustering Engine.
Transforms dozens of raw anomalies and alerts into unified incidents via
weighted pairwise affinity, causal lag validation, graph connected components,
and incident splitting for concurrent independent failures.
"""

import math
import uuid
import datetime
import networkx as nx
from typing import List, Dict, Set, Optional, Tuple, Any
from dateutil import parser as date_parser
from .schema import AnomalyEvent, Incident, UnifiedEvent
from .store import event_store
from .topology import dependency_graph


class IncidentCorrelator:
    def __init__(self):
        self.active_incidents: Dict[str, Incident] = {}

    def correlate_anomalies(self, anomalies: List[AnomalyEvent], raw_events: Optional[List[UnifiedEvent]] = None) -> List[Incident]:
        """
        Clusters active anomalies into 1 or more distinct incidents using
        pairwise temporal, topological, trace, and host affinity.
        """
        if not anomalies:
            return []

        raw_events = raw_events or []
        events_by_service: Dict[str, List[UnifiedEvent]] = {}
        for ev in raw_events:
            events_by_service.setdefault(ev.service, []).append(ev)

        # Build pairwise correlation graph
        G = nx.Graph()
        for anom in anomalies:
            G.add_node(anom.id, anomaly=anom)

        n = len(anomalies)
        for i in range(n):
            for j in range(i + 1, n):
                a1 = anomalies[i]
                a2 = anomalies[j]
                score = self._compute_affinity(a1, a2)
                if score >= 0.45:  # Threshold for clustering
                    G.add_edge(a1.id, a2.id, weight=score)

        # Find connected components (Incident Clusters)
        clusters = list(nx.connected_components(G))
        produced_incidents: List[Incident] = []
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for idx, cluster_nodes in enumerate(clusters):
            cluster_anoms = [G.nodes[node_id]["anomaly"] for node_id in cluster_nodes]
            services_in_cluster = sorted(list(set(a.service for a in cluster_anoms)))
            
            # Aggregate all evidence event IDs
            all_evidence_ids = []
            for a in cluster_anoms:
                all_evidence_ids.extend(a.evidence_ids)

            # Collect raw events corresponding to these services
            cluster_raw_events: List[UnifiedEvent] = []
            for s in services_in_cluster:
                cluster_raw_events.extend(events_by_service.get(s, []))

            # Earliest onset time in this cluster
            earliest_onset = min(a.onset_ts for a in cluster_anoms)
            max_severity = max(a.severity for a in cluster_anoms)
            sev_label = "P1" if max_severity > 0.8 else ("P2" if max_severity > 0.4 else "P3")

            # Determine title based on primary affected service
            primary_svc = services_in_cluster[0]
            if len(services_in_cluster) == 1:
                title = f"Isolated degradation on {primary_svc}"
            else:
                title = f"Cascading service degradation impacting {', '.join(services_in_cluster[:3])}"

            inc_id = f"inc_{earliest_onset[-8:].replace(':', '')}_{idx}"
            existing = self.active_incidents.get(inc_id)

            incident = Incident(
                id=existing.id if existing else inc_id,
                title=title,
                status="investigating",
                severity=sev_label,
                created_at=existing.created_at if existing else earliest_onset,
                updated_at=now_iso,
                services_involved=services_in_cluster,
                event_ids=list(set(all_evidence_ids + [e.id for e in cluster_raw_events])),
                alert_count=len(cluster_anoms) + len(cluster_raw_events),
                suppressed_count=max(0, len(cluster_raw_events) - len(cluster_anoms))
            )

            self.active_incidents[incident.id] = incident
            produced_incidents.append(incident)

        return produced_incidents

    def _compute_affinity(self, a1: AnomalyEvent, a2: AnomalyEvent) -> float:
        """
        Computes weighted affinity between two anomalies:
        - Temporal proximity (exponential decay)
        - Topology reachability (graph distance)
        - Causal lag plausibility (upstream onset before downstream)
        """
        # 1. Temporal Proximity
        try:
            t1 = date_parser.parse(a1.onset_ts).timestamp()
            t2 = date_parser.parse(a2.onset_ts).timestamp()
            time_diff = abs(t1 - t2)
            time_affinity = math.exp(-time_diff / 45.0)  # 45s decay half-life
        except Exception:
            time_affinity = 0.5

        # 2. Directed Causal Topology Proximity
        if a1.service == a2.service:
            topo_affinity = 1.0
            lag_affinity = 1.0
        else:
            is_a1_upstream = a2.service in dependency_graph.get_all_impacted_services(a1.service)
            is_a2_upstream = a1.service in dependency_graph.get_all_impacted_services(a2.service)
            
            # Callees or direct callers
            callees_1 = set(dependency_graph.get_callees(a1.service))
            callees_2 = set(dependency_graph.get_callees(a2.service))
            share_callee = bool(callees_1.intersection(callees_2))

            callers_1 = set(dependency_graph.get_callers(a1.service))
            callers_2 = set(dependency_graph.get_callers(a2.service))
            share_caller = bool(callers_1.intersection(callers_2))

            if is_a1_upstream or is_a2_upstream or share_callee or share_caller:
                # Plausible causal path exists
                hop_dist = dependency_graph.get_shortest_path_distance(a1.service, a2.service) or 2
                topo_affinity = 1.0 / (1.0 + hop_dist)
                
                if (is_a1_upstream and t1 <= t2 + 2.0) or (is_a2_upstream and t2 <= t1 + 2.0):
                    lag_affinity = 1.0
                else:
                    lag_affinity = 0.6
            else:
                # Disjoint causal paths: independent failures (Scenario 6)
                topo_affinity = 0.0
                lag_affinity = 0.0

        # Weighted combination
        score = 0.35 * time_affinity + 0.45 * topo_affinity + 0.20 * lag_affinity
        return score


# Global correlator singleton
incident_correlator = IncidentCorrelator()
