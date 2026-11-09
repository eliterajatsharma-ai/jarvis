"""
J.A.R.V.I.S. 20 Scenarios Failure Catalog and Test Profiles.
Implements all 20 scenarios from Section 8 of the execution plan as executable
fault injection profiles and downloadable/uploadable test log payloads.
"""

from typing import Dict, Any, List, Optional
import datetime
import uuid


SCENARIO_CATALOG: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "DB Failure Cascade (Official Scenario)",
        "description": "user-db connection pool saturates at 100%; auth-service times out, login fails, checkout payments fail.",
        "target_service": "user-db",
        "fault_type": "db_pool_exhaust",
        "expected_root_cause": "user-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"pool_utilization": 1.0}
    },
    2: {
        "id": 2,
        "name": "Third-Party Outage",
        "description": "External payment-gateway returns 503 Service Unavailable. Internal services are healthy.",
        "target_service": "payment-gateway",
        "fault_type": "payment_gw_503",
        "expected_root_cause": "payment-gateway",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"error_rate": 1.0}
    },
    3: {
        "id": 3,
        "name": "Bad Deploy Regression",
        "description": "Deployment v2.4.1 completed on payment-api, immediately followed by NullPointerException error spike.",
        "target_service": "payment-api",
        "fault_type": "bad_deploy",
        "expected_root_cause": "payment-api",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"error_rate": 0.85}
    },
    4: {
        "id": 4,
        "name": "Slow Burn Memory Leak",
        "description": "auth-service exhibits linear memory climb (+3%/sec) leading to OOM thrashing.",
        "target_service": "auth-service",
        "fault_type": "memory_leak",
        "expected_root_cause": "auth-service",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"initial_memory": 82.0}
    },
    5: {
        "id": 5,
        "name": "Retry Storm / Amplification",
        "description": "user-db latency triggers aggressive unthrottled retries from web-gateway, amplifying queue depth.",
        "target_service": "user-db",
        "fault_type": "retry_storm",
        "expected_root_cause": "user-db",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"retries_multiplier": 5}
    },
    6: {
        "id": 6,
        "name": "Two Independent Incidents at Once",
        "description": "Concurrent failure of redis-cache corruption AND payment-gateway 503 outage. Must NOT merge into 1 incident.",
        "target_service": "redis-cache",
        "fault_type": "dual_independent",
        "expected_root_cause": ["redis-cache", "payment-gateway"],
        "expected_incidents_count": 2,
        "expected_confidence": "high",
        "params": {"secondary_service": "payment-gateway"}
    },
    7: {
        "id": 7,
        "name": "Red Herring (Noisy Neighbor)",
        "description": "redis-cache throws benign noisy warnings at T-3s, but real cause is orders-db deadlock at T0.",
        "target_service": "orders-db",
        "fault_type": "red_herring",
        "expected_root_cause": "orders-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"noisy_service": "redis-cache"}
    },
    8: {
        "id": 8,
        "name": "Traffic Surge (Capacity Saturation)",
        "description": "Legitimate 5x traffic surge elevates latency across all microservices. No internal code fault.",
        "target_service": "web-gateway",
        "fault_type": "traffic_surge",
        "expected_root_cause": "web-gateway",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"traffic_multiplier": 5.0}
    },
    9: {
        "id": 9,
        "name": "Network Partition / Cross-Host Latency",
        "description": "Packet loss between compute-node-01 and compute-node-02 causes bidirectional timeouts.",
        "target_service": "payment-api",
        "fault_type": "network_partition",
        "expected_root_cause": "payment-api",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"latency_ms": 6000}
    },
    10: {
        "id": 10,
        "name": "Config Change Error",
        "description": "Admin updates AUTH_JWT_SECRET environment variable, causing signature verification failures.",
        "target_service": "auth-service",
        "fault_type": "config_error",
        "expected_root_cause": "auth-service",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"bad_key": "AUTH_JWT_SECRET"}
    },
    11: {
        "id": 11,
        "name": "Certificate / Credential Expiry",
        "description": "SSL certificate expired on internal orders-db endpoint, causing instant 100% TLS handshake failures.",
        "target_service": "orders-db",
        "fault_type": "credential_expiry",
        "expected_root_cause": "orders-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"tls_expired": True}
    },
    12: {
        "id": 12,
        "name": "Cache Stampede",
        "description": "redis-cache flush causes 100,000 queries to hit user-db simultaneously. Cache is trigger, DB is bottleneck.",
        "target_service": "redis-cache",
        "fault_type": "cache_stampede",
        "expected_root_cause": "redis-cache",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"secondary_bottleneck": "user-db"}
    },
    13: {
        "id": 13,
        "name": "Disk Full Outage",
        "description": "Database write journal fills partition to 100%, causing write transactions to fail.",
        "target_service": "user-db",
        "fault_type": "disk_full",
        "expected_root_cause": "user-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"disk_pct": 100.0}
    },
    14: {
        "id": 14,
        "name": "Flapping Service",
        "description": "payment-api crashes and restarts every 8 seconds. Debouncer must hold single persistent incident.",
        "target_service": "payment-api",
        "fault_type": "flapping",
        "expected_root_cause": "payment-api",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"period_sec": 8}
    },
    15: {
        "id": 15,
        "name": "Silent Failure (Heartbeat Drop)",
        "description": "auth-service worker thread deadlocks without logging error messages (heartbeat cessation).",
        "target_service": "auth-service",
        "fault_type": "silent_failure",
        "expected_root_cause": "auth-service",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"heartbeat_missing": True}
    },
    16: {
        "id": 16,
        "name": "Partial / Sparse Telemetry Data",
        "description": "Telemetry contains only raw text logs without metrics or distributed traces. Flags inferred topology.",
        "target_service": "payment-api",
        "fault_type": "sparse_data",
        "expected_root_cause": "payment-api",
        "expected_incidents_count": 1,
        "expected_confidence": "moderate",
        "params": {"traces_omitted": True}
    },
    17: {
        "id": 17,
        "name": "Ambiguous Evidence (Honest Uncertainty)",
        "description": "Equally plausible symptoms between orders-db and payment-gateway. System MUST declare Ambiguous state.",
        "target_service": "orders-db",
        "fault_type": "ambiguous_evidence",
        "expected_root_cause": "orders-db",
        "expected_incidents_count": 1,
        "expected_confidence": "ambiguous",
        "params": {"secondary_candidate": "payment-gateway"}
    },
    18: {
        "id": 18,
        "name": "False Alarm (Transient Noise Blip)",
        "description": "Single-second 300ms latency jitter that self-resolves on next tick. Must NOT open incident.",
        "target_service": "auth-service",
        "fault_type": "false_alarm",
        "expected_root_cause": None,
        "expected_incidents_count": 0,
        "expected_confidence": "none",
        "params": {"duration_sec": 1}
    },
    19: {
        "id": 19,
        "name": "Recovery Phase Verification",
        "description": "Remediation applied to user-db; latencies and error rates restore to baseline; incident marks resolved.",
        "target_service": "user-db",
        "fault_type": "recovery",
        "expected_root_cause": "user-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"auto_heal_after_sec": 5}
    },
    20: {
        "id": 20,
        "name": "Recurrence (Recurring Regression)",
        "description": "Same connection pool saturation returns 10 minutes later. Must link to historical incident.",
        "target_service": "user-db",
        "fault_type": "recurrence",
        "expected_root_cause": "user-db",
        "expected_incidents_count": 1,
        "expected_confidence": "high",
        "params": {"historical_incident_id": "inc_user_db_prev"}
    }
}


def generate_scenario_log_file_content(scenario_id: int) -> str:
    """Generates synthetic formatted log file content for upload testing of this scenario."""
    sc = SCENARIO_CATALOG.get(scenario_id, SCENARIO_CATALOG[1])
    target = sc["target_service"]
    now = datetime.datetime.now(datetime.timezone.utc)
    lines = []

    # Emit normal precursor logs
    for i in range(5, 0, -1):
        ts = (now - datetime.timedelta(seconds=i*3)).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{ts} [INFO] [web-gateway] [tr_{uuid.uuid4().hex[:8]}] GET /api/v1/health HTTP/1.1 200 4ms")
        lines.append(f"{ts} [INFO] [auth-service] [tr_{uuid.uuid4().hex[:8]}] Token validation succeeded for user usr_{1000+i}")

    # Emit failure logs
    fail_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    if target == "user-db":
        lines.append(f"{fail_ts} [CRITICAL] [user-db] FATAL: connection pool exhausted active=50/50 queue=142")
        lines.append(f"{fail_ts} [ERROR] [auth-service] User session query failed: connection timeout after 5000ms to user-db:5432")
        lines.append(f"{fail_ts} [ERROR] [web-gateway] Upstream timeout on POST /api/auth/login: 504 Gateway Timeout")
    elif target == "payment-gateway":
        lines.append(f"{fail_ts} [ERROR] [payment-api] HTTP POST https://api.stripe-external.com/v1/charges returned HTTP 503")
        lines.append(f"{fail_ts} [ERROR] [web-gateway] Checkout failed: upstream payment provider unavailable (502)")
    elif target == "payment-api":
        lines.append(f"{fail_ts} [WARN] [payment-api] Deployment v2.4.1 initialized by devops-ci")
        lines.append(f"{fail_ts} [CRITICAL] [payment-api] NullPointerException: PaymentController.java line 142 at runtime")
        lines.append(f"{fail_ts} [ERROR] [web-gateway] POST /api/checkout returned 500 Internal Server Error")
    else:
        lines.append(f"{fail_ts} [CRITICAL] [{target}] Unhandled fatal failure in component: {sc['description']}")
        lines.append(f"{fail_ts} [ERROR] [web-gateway] Downstream service error from {target}: connection dropped")

    return "\n".join(lines)
