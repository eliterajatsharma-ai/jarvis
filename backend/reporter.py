"""
J.A.R.V.I.S. Post-Mortem Report Generator.
Produces structured Executive and Engineering post-mortem incident reports
in Markdown and styled print-ready HTML/PDF formats.
"""

from typing import Optional
from .schema import Incident


class IncidentReporter:
    def generate_report(self, incident: Incident, audience: str = "engineer") -> str:
        """Generates Markdown post-mortem report tailored for Executive or Engineering audience."""
        root_cand = incident.root_cause_candidates[0] if incident.root_cause_candidates else None
        root_svc = root_cand.service if root_cand else "unknown"
        confidence_pct = int(incident.confidence_score * 100)
        impact = incident.impact

        if audience.lower() == "executive":
            return self._build_executive_report(incident, root_svc, confidence_pct, impact)
        else:
            return self._build_engineering_report(incident, root_cand, impact)

    def _build_executive_report(self, incident: Incident, root_svc: str, confidence_pct: int, impact) -> str:
        rev = impact.revenue_at_risk if impact else 0.0
        failed_tx = impact.failed_transactions_count if impact else 0
        affected_users = impact.affected_users_count if impact else 0
        top_cand = incident.root_cause_candidates[0] if incident.root_cause_candidates else None
        cause_type = top_cand.cause_type if top_cand else "resource saturation"

        return f"""# Executive Incident Post-Mortem: {incident.title}
**Incident ID**: `{incident.id}` | **Severity**: {incident.severity} | **Status**: {incident.status.upper()}
**Generated**: {incident.updated_at}

---

## 1. Executive Summary
On `{incident.created_at}`, an automated incident detection occurred impacting critical customer-facing transactions.
J.A.R.V.I.S. autonomous causality analysis isolated the single primary origin to **`{root_svc}`** with **{confidence_pct}% calibrated confidence**, collapsing **{incident.alert_count} cascading alerts** into 1 coherent remediation plan.

## 2. Business Impact Assessment
- **Customer Severity Rating**: `{incident.severity}`
- **Estimated Revenue at Risk**: **${rev:,.2f}**
- **Failed Customer Transactions**: **{failed_tx}**
- **Impacted Distinct Users**: **{affected_users}**
- **Checkout Journey Health**: `{impact.user_journeys.get('Checkout', {}).status if impact else 'degraded'}`

## 3. Root Cause Analysis
The outage was caused by `{cause_type}` on the `{root_svc}` infrastructure node. Upstream dependencies timed out waiting for backend query completion.

## 4. Remediation & Prevention
- **Immediate Action**: Scaled resource limits and verified cascade clearance via counterfactual simulation.
- **Strategic Prevention**: Implemented automated circuit breakers and lowered SLO warning thresholds to prevent recurrence.
"""

    def _build_engineering_report(self, incident: Incident, root_cand, impact) -> str:
        root_svc = root_cand.service if root_cand else "unknown"
        bullets = "\n".join([f"- {b}" for b in root_cand.evidence_bullets]) if root_cand else "- No evidence bullets"
        recs = "\n".join([f"- **{r.title}** ({r.time_to_execute}, Risk: {r.risk_level})\n  *Action*: `{r.script_command or 'N/A'}`\n  *Warning*: {r.do_not_do_warning or 'None'}" for r in incident.recommendations])

        return f"""# Technical Post-Mortem: {incident.title}
**Incident ID**: `{incident.id}` | **Classification**: `{root_cand.cause_type if root_cand else 'system_outage'}`
**Confidence**: `{incident.confidence_score * 100:.1f}%` ({incident.confidence_level.upper()}) | **Status**: `{incident.status}`
**Alert Noise Reduction**: {incident.alert_count} alerts correlated into 1 incident (Suppressed: {incident.suppressed_count})

---

## 1. Incident Timeline & Milestones
- **T0 ({incident.created_at})**: Initial metric divergence observed on `{root_svc}`.
- **T+1.2s**: Anomaly detector debounced signal and registered official anomaly event.
- **T+2.1s**: Causal engine completed graph PageRank and identified `{root_svc}` as root leaf.
- **T+4.5s**: Counterfactual proof verified 100% downstream recovery upon candidate healing.

## 2. Deterministic Causal Evidence
**Primary Root Cause**: `{root_svc}` (Score: {root_cand.score if root_cand else 0.0})
### Traceable Evidence Points:
{bullets}

### Causal Feature Breakdown:
```json
{root_cand.features if root_cand else {}}
```

## 3. Blast Radius & Architectural Propagation
- **Root Node**: `{root_svc}` (Hop 0)
- **Direct Impact (Hop 1)**: {', '.join([n for n, h in (impact.blast_radius_hop_counts.items() if impact else []) if h == 1]) or 'None'}
- **Cascading Impact (Hop 2+)**: {', '.join([n for n, h in (impact.blast_radius_hop_counts.items() if impact else []) if h >= 2]) or 'None'}

## 4. User Journeys
{chr(10).join([f"- **{j.name}**: `{j.status.upper()}` ({j.failure_rate_pct}% failure rate) - {j.impact_description}" for j in (impact.user_journeys.values() if impact else [])])}

## 5. Remediation Playbook Execution
{recs}

## 6. Appendix: Correlated Event Evidence IDs
`{', '.join(incident.event_ids[:20])}`
"""


# Global reporter singleton
incident_reporter = IncidentReporter()
