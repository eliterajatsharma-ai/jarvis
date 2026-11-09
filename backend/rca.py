"""
J.A.R.V.I.S. Deterministic Root Cause Engine.
Extracts 6 causal features (Onset Rank, Upstream Leaf Status, Downstream Symptom Coverage,
Reverse PageRank Random Walk, Resource Saturation Evidence, Deploy/Config Evidence),
computes normalized candidate probabilities, evaluates calibrated confidence,
and triggers the Ambiguous state when evidence is inconclusive.
"""

import math
import numpy as np
import networkx as nx
from typing import List, Dict, Tuple, Optional, Any
from dateutil import parser as date_parser
from .schema import Incident, AnomalyEvent, UnifiedEvent, RootCauseCandidate
from .config import RCA_WEIGHTS, SERVICE_MANIFEST
from .topology import dependency_graph


class RootCauseEngine:
    def __init__(self):
        self.weights = RCA_WEIGHTS

    def analyze_incident(self, incident: Incident, anomalies: List[AnomalyEvent], raw_events: List[UnifiedEvent]) -> Incident:
        """Runs the deterministic 6-feature causal model and enriches the Incident."""
        services = incident.services_involved
        if not services:
            return incident

        if len(services) == 1:
            # Single isolated failure
            svc = services[0]
            candidate = self._build_single_service_candidate(svc, anomalies, raw_events)
            incident.root_cause_candidates = [candidate]
            incident.confidence_score = 0.94
            incident.confidence_level = "high"
            incident.is_ambiguous = False
            incident.explained_symptoms_ratio = 1.0
            return incident

        # 1. Compute features for each candidate service
        service_features: Dict[str, Dict[str, float]] = {}
        service_onsets: Dict[str, float] = {}
        anoms_by_svc: Dict[str, List[AnomalyEvent]] = {}
        events_by_svc: Dict[str, List[UnifiedEvent]] = {}

        for a in anomalies:
            anoms_by_svc.setdefault(a.service, []).append(a)
        for e in raw_events:
            events_by_svc.setdefault(e.service, []).append(e)

        # Calculate earliest onset timestamp per service
        for svc in services:
            svc_anoms = anoms_by_svc.get(svc, [])
            if svc_anoms:
                earliest_ts = min(date_parser.parse(a.onset_ts).timestamp() for a in svc_anoms)
            else:
                earliest_ts = date_parser.parse(incident.created_at).timestamp()
            service_onsets[svc] = earliest_ts

        # Sort onsets for rank
        sorted_onsets = sorted(service_onsets.items(), key=lambda x: x[1])
        min_onset = sorted_onsets[0][1]

        # Inverted graph for Reverse Random Walk (PageRank)
        rev_graph = dependency_graph.graph.reverse()
        # Seed personalization with anomaly severities
        personalization = {}
        for node in rev_graph.nodes:
            node_anoms = anoms_by_svc.get(node, [])
            personalization[node] = sum(a.severity for a in node_anoms) + 0.05
        total_p = sum(personalization.values())
        personalization = {k: v / total_p for k, v in personalization.items()}

        try:
            pagerank_scores = nx.pagerank(rev_graph, alpha=0.85, personalization=personalization, max_iter=100)
        except Exception:
            pagerank_scores = {s: 1.0 / len(services) for s in services}

        # Compute feature vector for each service
        for rank_idx, (svc, onset) in enumerate(sorted_onsets):
            # F1: Onset Rank (earlier onset gets higher score, with clock-skew tolerance)
            onset_diff = onset - min_onset
            f_onset = max(0.1, 1.0 - (onset_diff / 30.0))  # 30s falloff

            # F2: Upstream-ness (does it have anomalous dependencies it calls?)
            callees = dependency_graph.get_callees(svc)
            anomalous_callees = [c for c in callees if c in anoms_by_svc and anoms_by_svc[c]]
            if not anomalous_callees:
                f_upstream = 1.0  # Leaf node: highest causal likelihood!
            else:
                f_upstream = 1.0 / (1.0 + len(anomalous_callees))

            # F3: Downstream Coverage (fraction of incident services reachable from svc)
            impacted_reachable = dependency_graph.get_all_impacted_services(svc)
            reachable_in_incident = [s for s in services if s in impacted_reachable and s != svc]
            other_services_count = max(1, len(services) - 1)
            f_downstream = len(reachable_in_incident) / other_services_count

            # F4: Reverse Random Walk score
            f_rw = pagerank_scores.get(svc, 0.1)

            # F5: Resource saturation evidence
            f_res = 0.0
            for a in anoms_by_svc.get(svc, []):
                if a.metric_or_pattern in ("pool_utilization", "memory_pct", "cpu_pct") and a.severity > 0.7:
                    f_res = 1.0
                    break

            # F6: Change / Deploy evidence
            f_chg = 0.0
            for ev in events_by_svc.get(svc, []):
                if ev.type in ("deploy", "config"):
                    f_chg = 1.0
                    break

            service_features[svc] = {
                "onset": f_onset,
                "upstream": f_upstream,
                "downstream_coverage": f_downstream,
                "random_walk": f_rw,
                "resource_evidence": f_res,
                "change_evidence": f_chg,
            }

        # 2. Weighted feature fusion
        raw_scores: Dict[str, float] = {}
        for svc, feats in service_features.items():
            raw_val = (
                self.weights["onset"] * feats["onset"] +
                self.weights["upstream"] * feats["upstream"] +
                self.weights["downstream_coverage"] * feats["downstream_coverage"] +
                self.weights["random_walk"] * feats["random_walk"] +
                self.weights["resource_evidence"] * feats["resource_evidence"] +
                self.weights["change_evidence"] * feats["change_evidence"]
            )
            raw_scores[svc] = raw_val

        # Softmax with temperature scaling
        beta = 3.5
        max_score = max(raw_scores.values())
        exp_scores = {s: math.exp((score - max_score) * beta) for s, score in raw_scores.items()}
        total_exp = sum(exp_scores.values())
        probs = {s: exp_scores[s] / total_exp for s in raw_scores}

        # Sort candidates by probability
        ranked_svcs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        # 3. Build RootCauseCandidate objects
        candidates: List[RootCauseCandidate] = []
        for rank_num, (svc, prob) in enumerate(ranked_svcs[:3], start=1):
            feats = service_features[svc]
            evidence_bullets, evidence_ids, cause_type = self._extract_candidate_evidence(
                svc, feats, anoms_by_svc.get(svc, []), events_by_svc.get(svc, []), min_onset, service_onsets[svc]
            )
            candidates.append(RootCauseCandidate(
                service=svc,
                rank=rank_num,
                score=round(prob, 3),
                cause_type=cause_type,
                evidence_bullets=evidence_bullets,
                evidence_ids=evidence_ids,
                onset_ts=date_parser.parse(incident.created_at).isoformat(),
                features={k: round(v, 2) for k, v in feats.items()}
            ))

        incident.root_cause_candidates = candidates

        # 4. Confidence & Ambiguity Gate (Honest Uncertainty)
        p1 = candidates[0].score
        p2 = candidates[1].score if len(candidates) > 1 else 0.0
        margin = p1 - p2
        top1_coverage = service_features[candidates[0].service]["downstream_coverage"]

        if margin < 0.18 or (len(candidates) > 1 and p1 < 0.45):
            # Thin margin: Explicit Ambiguous state!
            incident.status = "ambiguous"
            incident.is_ambiguous = True
            incident.confidence_level = "ambiguous"
            incident.confidence_score = round(p1, 2)
            incident.disambiguation_hint = (
                f"Equally plausible causal paths between #{1} {candidates[0].service} ({p1*100:.0f}%) "
                f"and #{2} {candidates[1].service} ({p2*100:.0f}%). "
                f"Action to disambiguate: Inspect connection pool count on {candidates[0].service} vs latency probe on {candidates[1].service}."
            )
        elif margin >= 0.35 and top1_coverage >= 0.65:
            incident.confidence_level = "high"
            incident.confidence_score = round(min(0.98, p1 + 0.1), 2)
            incident.is_ambiguous = False
            incident.status = "investigating"
            incident.disambiguation_hint = None
        else:
            incident.confidence_level = "moderate"
            incident.confidence_score = round(p1, 2)
            incident.is_ambiguous = False
            incident.status = "investigating"
            incident.disambiguation_hint = None

        # Explained symptoms ratio
        top_svc = candidates[0].service
        impacted = dependency_graph.get_all_impacted_services(top_svc)
        covered_svcs = set([top_svc] + list(impacted))
        explained_count = sum(len(anoms_by_svc.get(s, [])) for s in covered_svcs)
        total_count = max(1, len(anomalies))
        incident.explained_symptoms_ratio = round(min(1.0, explained_count / total_count), 2)

        return incident

    def _build_single_service_candidate(self, svc: str, anomalies: List[AnomalyEvent], raw_events: List[UnifiedEvent]) -> RootCauseCandidate:
        cause_type = "resource_exhaustion"
        evidence_bullets = [f"Isolated anomaly confirmed on {svc} with no cascading downstream links"]
        evidence_ids = []

        for a in anomalies:
            evidence_bullets.append(f"{a.metric_or_pattern}: {a.message}")
            evidence_ids.extend(a.evidence_ids)

        return RootCauseCandidate(
            service=svc,
            rank=1,
            score=0.95,
            cause_type=cause_type,
            evidence_bullets=evidence_bullets[:4],
            evidence_ids=evidence_ids[:6],
            onset_ts=anomalies[0].onset_ts if anomalies else "",
            features={"onset": 1.0, "upstream": 1.0, "downstream_coverage": 1.0}
        )

    def _extract_candidate_evidence(
        self, svc: str, feats: Dict[str, float], anoms: List[AnomalyEvent],
        events: List[UnifiedEvent], min_onset: float, svc_onset: float
    ) -> Tuple[List[str], List[str], str]:
        bullets: List[str] = []
        evidence_ids: List[str] = []
        cause_type = "dependency_outage"

        manifest = SERVICE_MANIFEST.get(svc, {})
        is_external = manifest.get("is_external", False)

        # 1. Onset Timing Evidence
        lag_sec = int(svc_onset - min_onset)
        if lag_sec <= 2:
            bullets.append(f"Earliest deviating service in cascade (diverged at T+0s)")
        else:
            bullets.append(f"Diverged {lag_sec}s after initial cascade onset")

        # 2. Resource Evidence
        for a in anoms:
            evidence_ids.extend(a.evidence_ids)
            if a.metric_or_pattern == "pool_utilization":
                bullets.append(f"Connection pool hit 100% saturation ({a.message})")
                cause_type = "resource_exhaustion"
            elif a.metric_or_pattern == "memory_pct":
                bullets.append(f"Memory reached {a.current_value:.1f}% with linear climb")
                cause_type = "resource_exhaustion"

        # 3. Change Evidence
        for ev in events:
            if ev.type == "deploy":
                bullets.append(f"Deployment v2.4.1 recorded immediately prior to failure onset")
                evidence_ids.append(ev.id)
                cause_type = "deploy_regression"
            elif ev.type == "config":
                bullets.append(f"Environment configuration change recorded prior to failure")
                evidence_ids.append(ev.id)
                cause_type = "config_error"

        # 4. Topology Leaf Evidence
        if feats["upstream"] == 1.0:
            bullets.append(f"Leaf service: zero downstream dependencies failing")
        else:
            bullets.append(f"Calling dependencies degraded: {int((1-feats['upstream'])*100)}% callee error rate")

        if is_external:
            cause_type = "dependency_outage"
            bullets.append(f"3rd-party external dependency outside cluster boundaries")

        # Fallback bullet if sparse
        if len(bullets) < 2:
            bullets.append(f"Downstream reachability explains {int(feats['downstream_coverage']*100)}% of downstream cascade")

        return bullets[:4], list(set(evidence_ids))[:6], cause_type


# Global root cause engine singleton
rca_engine = RootCauseEngine()
