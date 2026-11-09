"""
Direct Python Test Runner for J.A.R.V.I.S. Test Suite.
Runs all core tests without requiring third-party test runners.
"""

import sys
import traceback
from tests.test_core import (
    test_schema_and_drain_normalization,
    test_event_store_and_alert_suppression,
    test_topology_graph_reachability,
    test_anomaly_detection_and_debounce,
    test_root_cause_engine_on_official_scenario,
    test_scenario_6_dual_independent_incidents_split,
    test_scenario_17_ambiguous_evidence_declaration,
    test_war_room_guardrails_and_citations,
    test_accuracy_benchmark_harness
)

TESTS = [
    ("Schema Normalization & Drain3 Mining", test_schema_and_drain_normalization),
    ("Event Store & Alert Storm Suppression", test_event_store_and_alert_suppression),
    ("Topology Graph Reachability & Blast Radius", test_topology_graph_reachability),
    ("Anomaly Detection & Debounce Onset", test_anomaly_detection_and_debounce),
    ("RCA Engine: Scenario 1 (DB Cascade)", test_root_cause_engine_on_official_scenario),
    ("Scenario 6: Dual Independent Incidents Split", test_scenario_6_dual_independent_incidents_split),
    ("Scenario 17: Honest Ambiguous Evidence", test_scenario_17_ambiguous_evidence_declaration),
    ("War Room Guardrails & Citation Whitelist", test_war_room_guardrails_and_citations),
    ("20-Scenario Accuracy Benchmark Scoreboard", test_accuracy_benchmark_harness)
]

def main():
    passed = 0
    failed = 0
    print("=" * 60)
    print("J.A.R.V.I.S. Automated Engineering Test Suite")
    print("=" * 60)

    for name, test_fn in TESTS:
        sys.stdout.write(f"Testing {name:.<48}")
        sys.stdout.flush()
        try:
            test_fn()
            print(" [PASS]")
            passed += 1
        except Exception as e:
            print(" [FAIL]")
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
