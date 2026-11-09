"""
J.A.R.V.I.S. Operational Playbooks and Recommendation Engine.
Contains knowledge base of remediation actions keyed by cause type, with risk badges,
execution times, reversibility flags, safety warnings, and on-call routing.
"""

from typing import List, Dict, Any, Optional
from .schema import Recommendation, Incident
from .config import SERVICE_MANIFEST


PLAYBOOK_KNOWLEDGE_BASE: Dict[str, List[Dict[str, Any]]] = {
    "resource_exhaustion": [
        {
            "id": "rec_pool_scale",
            "title": "Increase Database Connection Pool Size",
            "action_type": "scale_pool",
            "expected_effect": "Instantly eliminates connection acquisition timeouts by raising pool max from 50 to 150 slots",
            "time_to_execute": "15 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "Fastest safe action first",
            "do_not_do_warning": "Do not restart database master under load; restarting drops in-flight client transactions",
            "script_command": "kubectl patch configmap db-pool-config -p '{\"data\":{\"max_connections\":\"150\"}}'"
        },
        {
            "id": "rec_restart_worker",
            "title": "Graceful Rolling Restart of Service Pods",
            "action_type": "restart_service",
            "expected_effect": "Flushes leaked memory heap and resets stalled worker threads",
            "time_to_execute": "45 seconds",
            "risk_level": "Medium",
            "reversibility": False,
            "ranking": "Secondary remediation",
            "do_not_do_warning": "Ensure minAvailable=50% to prevent dropping below quorum",
            "script_command": "kubectl rollout restart deployment/{service}"
        }
    ],
    "deploy_regression": [
        {
            "id": "rec_rollback_deploy",
            "title": "Immediate Deployment Rollback to Previous Stable Release",
            "action_type": "rollback_deploy",
            "expected_effect": "Reverts regression commit and restores known stable binary (v2.4.0)",
            "time_to_execute": "30 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "Immediate priority fix",
            "do_not_do_warning": "Do not execute hotfix patches directly in production without running test harness",
            "script_command": "kubectl rollout undo deployment/{service}"
        }
    ],
    "dependency_outage": [
        {
            "id": "rec_circuit_breaker",
            "title": "Enable Circuit Breaker with Fallback Degraded Mode",
            "action_type": "enable_circuit_breaker",
            "expected_effect": "Fast-fails failing downstream calls, isolating blast radius and freeing upstream worker threads",
            "time_to_execute": "10 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "Immediate blast radius containment",
            "do_not_do_warning": "Do not retry failed 503 requests aggressively; triggers downstream retry storms",
            "script_command": "consul-kv put services/{service}/circuit_breaker_enabled true"
        },
        {
            "id": "rec_failover_provider",
            "title": "Switch Payment Provider Route to Secondary Gateway (Adyen)",
            "action_type": "switch_provider",
            "expected_effect": "Redirects 100% of checkout authorizations away from degraded Stripe gateway",
            "time_to_execute": "20 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "High confidence failover",
            "do_not_do_warning": "Verify secondary provider credentials before routing live traffic",
            "script_command": "aws route53 change-resource-record-sets --hosted-zone-id Z123 --change-batch ..."
        }
    ],
    "network_degradation": [
        {
            "id": "rec_reroute_mesh",
            "title": "Reroute Service Mesh Traffic Around Congested Link",
            "action_type": "reroute_mesh",
            "expected_effect": "Bypasses packet loss on node-us-east-02 by steering traffic through node-01",
            "time_to_execute": "25 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "Fastest network mitigation",
            "script_command": "istioctl routing apply -f bypass-degraded-link.yaml"
        }
    ],
    "config_error": [
        {
            "id": "rec_restore_config",
            "title": "Restore Secret & Environment Variable from Vault",
            "action_type": "restore_config",
            "expected_effect": "Replaces corrupted JWT secret with active valid credential token",
            "time_to_execute": "15 seconds",
            "risk_level": "Low",
            "reversibility": True,
            "ranking": "Zero risk config revert",
            "script_command": "vault kv get -field=secret secret/auth-service | kubectl apply ..."
        }
    ]
}


class PlaybookEngine:
    def get_recommendations_for_incident(self, incident: Incident) -> List[Recommendation]:
        """Maps incident root causes to ordered, actionable playbook items."""
        if not incident.root_cause_candidates:
            return []

        top_cand = incident.root_cause_candidates[0]
        cause_type = top_cand.cause_type
        target_svc = top_cand.service

        owner = SERVICE_MANIFEST.get(target_svc, {}).get("owner", "team-oncall-core")
        templates = PLAYBOOK_KNOWLEDGE_BASE.get(cause_type, PLAYBOOK_KNOWLEDGE_BASE["resource_exhaustion"])

        recommendations: List[Recommendation] = []
        for tpl in templates:
            cmd = tpl.get("script_command")
            if cmd:
                cmd = cmd.replace("{service}", target_svc)

            recommendations.append(Recommendation(
                id=tpl["id"],
                title=tpl["title"].replace("{service}", target_svc),
                action_type=tpl["action_type"],
                expected_effect=tpl["expected_effect"],
                time_to_execute=tpl["time_to_execute"],
                risk_level=tpl["risk_level"],
                reversibility=tpl["reversibility"],
                ranking=tpl["ranking"],
                do_not_do_warning=tpl.get("do_not_do_warning"),
                owner=owner,
                service=target_svc,
                script_command=cmd
            ))

        return recommendations


# Global playbook engine singleton
playbook_engine = PlaybookEngine()
