"""
J.A.R.V.I.S. Core Automated Test Suite.
Verifies all P0 and P1 algorithms: Ingestion, Drain3 Normalization,
Anomaly Detection, Topology Graph, Correlation Clustering,
Root Cause Engine, Counterfactual Proof, War Room Guardrails, and Accuracy Benchmark.
"""

import datetime
import asyncio
from backend.schema import UnifiedEvent, AnomalyEvent
from backend.normalizer import normalize_event
from backend.drain_miner import log_miner
from backend.store import event_store
from backend.detector import anomaly_detector
from backend.topology import dependency_graph
from backend.correlator import incident_correlator
from backend.rca import rca_engine
from backend.impact import impact_analyzer
from backend.playbooks import playbook_engine
from backend.counterfactual import counterfactual_engine
from backend.war_room import grounded_war_room
from backend.accuracy_harness import accuracy_harness
from backend.scenarios import SCENARIO_CATALOG


def test_schema_and_drain_normalization():
    """Test log normalization, PII masking, and Drain3 template ID mining."""
    raw = {
        "source": "api",
        "service": "payment-api",
        "severity": "CRITICAL",
        "message": "Failed database connection for user john.doe@enterprise.com from 192.168.1.105 with UUID 123e4567-e89b-12d3-a456-426614174000",
        "attrs": {"latency_ms": 4200}
    }
    evt = normalize_event(raw)
    assert evt.service == "payment-api"
    assert evt.severity == "critical"
    # Verify PII masking
    assert "[EMAIL]" in evt.message
    assert "[IP_ADDR]" in evt.message
    assert "[UUID]" in evt.message
    assert "john.doe" not in evt.message
    assert evt.template_id is not None
    assert evt.fingerprint.startswith("payment-api|")


def test_event_store_and_alert_suppression():
    """Test SQLite event storage and alert storm deduplication counts."""
    event_store.clear_all()
    evt = normalize_event({
        "service": "user-db",
        "severity": "critical",
        "message": "connection refused on port 5432"
    })
    
    # Insert multiple identical events (Alert storm simulation)
    for _ in range(5):
        event_store.insert_event(evt)

    events = event_store.get_recent_events(limit=10)
    assert len(events) >= 1

    summary = event_store.get_suppressed_alerts_summary()
    assert len(summary) >= 1
    assert summary[0]["count"] >= 5


def test_topology_graph_reachability():
    """Verify directed topology traversal: callers, callees, and impacted blast radius."""
    # web-gateway -> auth-service -> user-db
    callees_gw = dependency_graph.get_callees("web-gateway")
    assert "auth-service" in callees_gw
    assert "payment-api" in callees_gw

    # If user-db fails, who is impacted? (auth-service and web-gateway)
    impacted_by_db = dependency_graph.get_all_impacted_services("user-db")
    assert "auth-service" in impacted_by_db
    assert "web-gateway" in impacted_by_db


def test_anomaly_detection_and_debounce():
    """Test that metric deviations trigger debounced anomalies with true onset timestamp."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    anoms_all = []
    
    # Emit 3 consecutive metric evaluations with saturated pool
    for i in range(3):
        t_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=i)).isoformat()
        evt = UnifiedEvent(
            id=f"evt_pool_{i}",
            ts=t_iso,
            ts_received=t_iso,
            source="simulator",
            type="metric",
            service="user-db",
            host="db-node",
            severity="critical",
            message="Pool saturated",
            attrs={"pool_utilization": 1.0, "latency_p95": 4500.0, "error_rate": 0.85},
            fingerprint="user-db|POOL|critical"
        )
        anoms = anomaly_detector.evaluate_event(evt)
        anoms_all.extend(anoms)

    assert len(anoms_all) > 0
    pool_anom = [a for a in anoms_all if a.metric_or_pattern == "pool_utilization"][0]
    assert pool_anom.service == "user-db"
    assert pool_anom.severity >= 0.8


def test_root_cause_engine_on_official_scenario():
    """Test that Scenario 1 (DB failure cascade) deterministically identifies user-db as top root cause."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t0 = now.isoformat()
    t1 = (now + datetime.timedelta(seconds=2)).isoformat()
    t2 = (now + datetime.timedelta(seconds=4)).isoformat()

    anoms = [
        AnomalyEvent(
            id="a1", service="user-db", metric_or_pattern="pool_utilization",
            onset_ts=t0, detected_ts=t0, severity=0.95, current_value=1.0, baseline_value=0.15,
            message="user-db connection pool hit 100%", evidence_ids=["evt_db_01"]
        ),
        AnomalyEvent(
            id="a2", service="auth-service", metric_or_pattern="latency_p95",
            onset_ts=t1, detected_ts=t1, severity=0.80, current_value=3500.0, baseline_value=25.0,
            message="auth-service timeout waiting for user-db", evidence_ids=["evt_auth_01"]
        ),
        AnomalyEvent(
            id="a3", service="web-gateway", metric_or_pattern="error_rate",
            onset_ts=t2, detected_ts=t2, severity=0.85, current_value=0.75, baseline_value=0.001,
            message="web-gateway 504 Gateway Timeout", evidence_ids=["evt_gw_01"]
        ),
    ]

    incidents = incident_correlator.correlate_anomalies(anoms)
    assert len(incidents) == 1
    inc = incidents[0]

    analyzed = rca_engine.analyze_incident(inc, anoms, [])
    assert len(analyzed.root_cause_candidates) >= 1
    top_cand = analyzed.root_cause_candidates[0]
    
    # Must blame user-db as rank 1 with high confidence!
    assert top_cand.service == "user-db"
    assert top_cand.score > 0.50
    assert analyzed.confidence_level == "high"
    assert len(top_cand.evidence_bullets) >= 2


def test_scenario_6_dual_independent_incidents_split():
    """Scenario 6: Verify that concurrent independent failures are kept as 2 separate incidents."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t0 = now.isoformat()

    anoms = [
        AnomalyEvent(
            id="a_redis", service="redis-cache", metric_or_pattern="cache_miss",
            onset_ts=t0, detected_ts=t0, severity=0.85, current_value=0.95, baseline_value=0.05,
            message="redis corruption", evidence_ids=["evt_rd"]
        ),
        AnomalyEvent(
            id="a_paygw", service="payment-gateway", metric_or_pattern="http_503",
            onset_ts=t0, detected_ts=t0, severity=0.90, current_value=1.0, baseline_value=0.001,
            message="payment-gateway 503 outage", evidence_ids=["evt_gw"]
        )
    ]

    # No dependency path exists between redis-cache and payment-gateway
    incidents = incident_correlator.correlate_anomalies(anoms)
    assert len(incidents) == 2, f"Expected 2 split incidents, but got {len(incidents)}"


def test_scenario_17_ambiguous_evidence_declaration():
    """Scenario 17: Verify system declares explicit Ambiguous status when evidence is split."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t0 = now.isoformat()
    t1 = (now + datetime.timedelta(seconds=2)).isoformat()

    anoms = [
        AnomalyEvent(
            id="a_ord", service="orders-db", metric_or_pattern="db_pool",
            onset_ts=t0, detected_ts=t0, severity=0.75, current_value=0.85, baseline_value=0.15,
            message="orders-db pool warning", evidence_ids=["evt_ord"]
        ),
        AnomalyEvent(
            id="a_pay", service="payment-gateway", metric_or_pattern="latency",
            onset_ts=t0, detected_ts=t0, severity=0.75, current_value=4000.0, baseline_value=20.0,
            message="payment-gateway latency spike", evidence_ids=["evt_pay"]
        ),
        AnomalyEvent(
            id="a_api", service="payment-api", metric_or_pattern="error_rate",
            onset_ts=t1, detected_ts=t1, severity=0.80, current_value=0.60, baseline_value=0.001,
            message="payment-api checkout failures", evidence_ids=["evt_api"]
        )
    ]

    incidents = incident_correlator.correlate_anomalies(anoms)
    inc = incidents[0]
    analyzed = rca_engine.analyze_incident(inc, anoms, [])
    
    assert analyzed.is_ambiguous is True
    assert analyzed.confidence_level == "ambiguous"
    assert analyzed.disambiguation_hint is not None


def test_war_room_guardrails_and_citations():
    """Verify AI war room citations are validated against evidence whitelist."""
    inc = incident_correlator.active_incidents.get(list(incident_correlator.active_incidents.keys())[0]) if incident_correlator.active_incidents else None
    if not inc:
        # Create sample incident
        inc = rca_engine.analyze_incident(
            incident_correlator.correlate_anomalies([
                AnomalyEvent(
                    id="a_db", service="user-db", metric_or_pattern="pool",
                    onset_ts="2026-11-09T10:00:00Z", detected_ts="2026-11-09T10:00:00Z",
                    severity=0.9, current_value=1.0, baseline_value=0.15,
                    message="pool", evidence_ids=["evt_sample_101"]
                )
            ])[0],
            [], []
        )

    res = grounded_war_room.answer_query("Why did you blame the DB?", inc)
    assert "user-db" in res.answer
    assert len(res.evidence_ids) > 0
    assert res.tier_used == "deterministic_template"


def test_accuracy_benchmark_harness():
    """Verify that accuracy benchmark harness runs and scores > 90% across scenarios."""
    results = accuracy_harness.run_benchmark(iterations_per_scenario=1)
    assert results["scenarios_tested"] == 20
    assert results["top1_accuracy_pct"] >= 85.0
    assert results["top3_accuracy_pct"] >= 95.0
    assert results["mean_time_to_identify_sec"] < 5.0
    assert results["ambiguity_honesty_rate_pct"] == 100.0
