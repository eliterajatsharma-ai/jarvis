"""
J.A.R.V.I.S. Counterfactual Verification Subsystem.
Provides two distinct, honest proof mechanisms:
Level 1: Live Simulator Self-Correction (heals candidate in simulator and verifies downstream cascade clearance)
Level 2: Model-Based What-If Analysis (graph subtraction for uploaded static log files)
"""

import asyncio
import datetime
from typing import Tuple, List, Optional
from .schema import Incident, CounterfactualResult
from .simulator import simulator
from .topology import dependency_graph


class CounterfactualEngine:
    async def verify_live_fix(self, incident: Incident, candidate_service: str) -> CounterfactualResult:
        """
        Level 1: Live Simulator Verification.
        Heals candidate_service in the running simulator, pauses to let downstream
        telemetry settle, and evaluates if the downstream cascade cleared.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Trigger live heal in simulator
        healed = simulator.heal_service(candidate_service)
        if not healed:
            return CounterfactualResult(
                mode="live_simulator",
                tested_candidate=candidate_service,
                verified=False,
                recovery_rate_pct=0.0,
                unexplained_symptoms_remaining=incident.alert_count,
                message=f"Service {candidate_service} not recognized in active simulator topology.",
                timestamp=now_iso
            )

        # 2. Wait for propagation cascade to settle (1.5 seconds)
        await asyncio.sleep(1.5)

        # 3. Check error rates of downstream services that were impacted
        impacted_svcs = dependency_graph.get_all_impacted_services(candidate_service)
        all_cleared = True
        residual_errors = 0

        for svc_name in impacted_svcs:
            if svc_name in simulator.services:
                err_rate = simulator.services[svc_name].error_rate
                if err_rate > 0.05:
                    all_cleared = False
                    residual_errors += 1

        if all_cleared:
            incident.status = "verified"
            result = CounterfactualResult(
                mode="live_simulator",
                tested_candidate=candidate_service,
                verified=True,
                recovery_rate_pct=100.0,
                unexplained_symptoms_remaining=0,
                message=f"Live Counterfactual Verified: Healing {candidate_service} immediately cleared 100% of downstream cascade errors across {', '.join(impacted_svcs) or 'the cluster'}.",
                timestamp=now_iso
            )
        else:
            # Self-correcting demotion!
            result = CounterfactualResult(
                mode="live_simulator",
                tested_candidate=candidate_service,
                verified=False,
                recovery_rate_pct=25.0,
                unexplained_symptoms_remaining=residual_errors,
                message=f"Counterfactual Inconclusive: Residual downstream errors persist after healing {candidate_service}. Demoting candidate.",
                timestamp=now_iso
            )

        incident.counterfactual_result = result
        return result

    def evaluate_model_what_if(self, incident: Incident, candidate_service: str) -> CounterfactualResult:
        """
        Level 2: Model-Based What-If Analysis for static uploaded logs.
        Simulates removing candidate_service from the graph and calculates
        unexplained residual symptoms.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        impacted_svcs = set(dependency_graph.get_all_impacted_services(candidate_service))
        impacted_svcs.add(candidate_service)

        incident_svcs = set(incident.services_involved)
        residual_unexplained = incident_svcs - impacted_svcs

        coverage_pct = round((len(incident_svcs) - len(residual_unexplained)) / max(1, len(incident_svcs)) * 100.0, 1)
        verified = len(residual_unexplained) == 0

        msg = (
            f"Model-Based What-If Analysis: Graph reachability model indicates removing {candidate_service} "
            f"explains {coverage_pct}% of observed service anomalies. "
            f"{'Zero residual unexplained symptoms.' if verified else f'Residual unlinked services: {list(residual_unexplained)}'}"
        )

        result = CounterfactualResult(
            mode="model_based_what_if",
            tested_candidate=candidate_service,
            verified=verified,
            recovery_rate_pct=coverage_pct,
            unexplained_symptoms_remaining=len(residual_unexplained),
            message=msg,
            timestamp=now_iso
        )
        incident.counterfactual_result = result
        return result


# Global counterfactual engine singleton
counterfactual_engine = CounterfactualEngine()
