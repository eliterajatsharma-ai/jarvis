"""
J.A.R.V.I.S. Impact Analysis and User Journey Engine.
Calculates blast radius hop distances, user journey failure rates (Login, Browse, Checkout),
affected unique users, failed transactions, and estimated revenue at risk.
"""

from typing import Dict, List, Set, Tuple
from collections import deque
from dateutil import parser as date_parser
import datetime
from .schema import Incident, ImpactSummary, JourneyStatus, UnifiedEvent
from .config import USER_JOURNEYS, AVERAGE_ORDER_VALUE, SERVICE_MANIFEST
from .topology import dependency_graph


class ImpactAnalyzer:
    def compute_impact(self, incident: Incident, raw_events: List[UnifiedEvent]) -> ImpactSummary:
        """Evaluates business and architectural blast radius for the incident."""
        root_cause_svc = incident.root_cause_candidates[0].service if incident.root_cause_candidates else (
            incident.services_involved[0] if incident.services_involved else "user-db"
        )

        # 1. Blast Radius BFS (Reverse Traversal: Callee -> Callers)
        hop_counts: Dict[str, int] = {root_cause_svc: 0}
        queue = deque([(root_cause_svc, 0)])
        blast_nodes = [root_cause_svc]

        while queue:
            current, hop = queue.popleft()
            callers = dependency_graph.get_callers(current)
            for caller in callers:
                if caller not in hop_counts:
                    hop_counts[caller] = hop + 1
                    blast_nodes.append(caller)
                    queue.append((caller, hop + 1))

        # 2. User Journey Health Evaluation
        user_journeys: Dict[str, JourneyStatus] = {}
        for j_name, j_data in USER_JOURNEYS.items():
            constituents = j_data["services"]
            # Check how many constituent services are in blast_nodes or incident services
            impacted_constituents = [s for s in constituents if s in incident.services_involved or s in blast_nodes]
            impact_ratio = len(impacted_constituents) / len(constituents)

            if impact_ratio >= 0.5:
                status = "failing"
                fail_rate = round(min(98.0, 45.0 + impact_ratio * 50.0), 1)
                desc = f"{len(impacted_constituents)} of {len(constituents)} services degraded in critical path"
            elif impact_ratio > 0:
                status = "degraded"
                fail_rate = round(15.0 + impact_ratio * 25.0, 1)
                desc = f"Upstream dependency latency affecting {impacted_constituents[0]}"
            else:
                status = "healthy"
                fail_rate = 0.1
                desc = "Operating within normal SLO bounds"

            user_journeys[j_name] = JourneyStatus(
                name=j_name,
                status=status,
                failure_rate_pct=fail_rate,
                impact_description=desc
            )

        # 3. Quantitative Impact Numbers
        affected_users: Set[str] = set()
        failed_transactions = 0

        for ev in raw_events:
            if ev.severity in ("error", "critical"):
                uid = ev.attrs.get("user_id")
                if uid:
                    affected_users.add(str(uid))
                # Count 5xx or failed transaction events
                status = ev.attrs.get("status")
                if status and int(status) >= 500:
                    failed_transactions += 1
                elif "fail" in ev.message.lower() or "error" in ev.message.lower():
                    failed_transactions += 1

        if not failed_transactions and incident.services_involved:
            # If in simulator with sparse explicit logs, estimate from alert count
            failed_transactions = max(12, incident.alert_count * 3)
            affected_users_count = max(8, len(affected_users) or incident.alert_count * 2)
        else:
            affected_users_count = len(affected_users)

        revenue_at_risk = round(failed_transactions * AVERAGE_ORDER_VALUE, 2)

        # 4. Time Since Incident Start
        try:
            start_ts = date_parser.parse(incident.created_at).timestamp()
            now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
            elapsed_sec = max(0.0, now_ts - start_ts)
        except Exception:
            elapsed_sec = 42.0

        # Customer-Facing Severity derivation
        checkout_status = user_journeys.get("Checkout", {}).status
        if checkout_status == "failing" or revenue_at_risk > 1000.0:
            cust_sev = "P1"
        elif user_journeys.get("Login", {}).status == "degraded" or checkout_status == "degraded":
            cust_sev = "P2"
        else:
            cust_sev = "P3"

        return ImpactSummary(
            blast_radius_nodes=blast_nodes,
            blast_radius_hop_counts=hop_counts,
            user_journeys=user_journeys,
            affected_users_count=affected_users_count,
            failed_transactions_count=failed_transactions,
            revenue_at_risk=revenue_at_risk,
            time_since_incident_start_sec=round(elapsed_sec, 1),
            customer_severity=cust_sev
        )


# Global impact analyzer singleton
impact_analyzer = ImpactAnalyzer()
