"""
J.A.R.V.I.S. Layered Anomaly Detection Engine.
Combines Robust Median/MAD Z-Scores, EWMA Drift Filtering, Hard SLO Gates,
Drain3 Log Pattern Spike Detection, Debounce Tracking, and Onset Pinpointing.
"""

import math
import numpy as np
import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
from .schema import UnifiedEvent, AnomalyEvent
from .config import THRESHOLDS, SERVICE_MANIFEST
from .store import event_store


class ServiceMetricHistory:
    """Maintains rolling buffers and EWMA states for a service."""
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.history_len = 60
        self.p95_history = deque(maxlen=self.history_len)
        self.error_rate_history = deque(maxlen=self.history_len)
        self.cpu_history = deque(maxlen=self.history_len)
        self.pool_history = deque(maxlen=self.history_len)
        self.memory_history = deque(maxlen=self.history_len)
        
        # EWMA state for memory and latency
        self.ewma_memory = None
        self.ewma_latency = None
        
        # Debounce tracking: {metric_name: (consecutive_count, first_divergence_ts)}
        self.debounce_tracker: Dict[str, Tuple[int, str]] = {}
        
        # Log template frequency tracking: {template_id: deque of timestamps}
        self.template_timestamps: Dict[str, deque] = {}
        self.seen_templates: set = set()


class AnomalyDetector:
    def __init__(self):
        self.service_histories: Dict[str, ServiceMetricHistory] = {
            svc: ServiceMetricHistory(svc) for svc in SERVICE_MANIFEST
        }

    def _get_history(self, service: str) -> ServiceMetricHistory:
        if service not in self.service_histories:
            self.service_histories[service] = ServiceMetricHistory(service)
        return self.service_histories[service]

    @staticmethod
    def _calc_robust_z(val: float, history: deque) -> Tuple[float, float]:
        """Calculates Robust Z-score using Median and Median Absolute Deviation (MAD)."""
        if len(history) < 5:
            return 0.0, float(np.mean(list(history))) if history else val
        arr = np.array(list(history))
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med)))
        if mad < 1e-4:
            # If MAD is near zero, use standard deviation or simple diff
            std = float(np.std(arr))
            if std < 1e-4:
                return (val - med) / 1.0, med
            return (val - med) / std, med
        z = 0.6745 * (val - med) / mad
        return z, med

    def evaluate_event(self, event: UnifiedEvent) -> List[AnomalyEvent]:
        """Evaluates an incoming event against detection layers and returns any triggered anomalies."""
        anomalies: List[AnomalyEvent] = []
        hist = self._get_history(event.service)
        now_iso = event.ts
        attrs = event.attrs or {}
        criticality = SERVICE_MANIFEST.get(event.service, {}).get("criticality", 0.8)

        # 1. Metric Telemetry Evaluation
        if event.type == "metric":
            # Extract metrics
            p95 = float(attrs.get("latency_p95", 0.0))
            err_rate = float(attrs.get("error_rate", 0.0))
            pool = float(attrs.get("pool_utilization", 0.0))
            mem = float(attrs.get("memory_pct", 0.0))
            cpu = float(attrs.get("cpu_pct", 0.0))

            # Update EWMA for memory drift (Slow burn Scenario #4)
            alpha = THRESHOLDS["ewma_alpha"]
            if hist.ewma_memory is None:
                hist.ewma_memory = mem
            else:
                hist.ewma_memory = alpha * mem + (1 - alpha) * hist.ewma_memory

            # A. Robust Z-score check on p95 latency
            z_p95, med_p95 = self._calc_robust_z(p95, hist.p95_history)
            p95_diverged = z_p95 > THRESHOLDS["z_score_cutoff"] or (p95 > med_p95 * THRESHOLDS["hard_p95_multiplier"] and p95 > 250.0)
            self._handle_debounce(hist, "p95_latency", p95_diverged, now_iso)
            
            if self._is_debounced_active(hist, "p95_latency"):
                onset_ts = hist.debounce_tracker["p95_latency"][1]
                sev = min(1.0, (0.4 + (p95 / 5000.0) * 0.4) * criticality)
                anom = AnomalyEvent(
                    id=f"anom_{event.service}_p95_{onset_ts[-8:].replace(':', '')}",
                    service=event.service,
                    metric_or_pattern="latency_p95",
                    onset_ts=onset_ts,
                    detected_ts=now_iso,
                    severity=round(sev, 2),
                    z_score=round(z_p95, 2),
                    current_value=p95,
                    baseline_value=round(med_p95, 1),
                    message=f"{event.service} p95 latency degraded to {p95:.1f}ms (baseline: {med_p95:.1f}ms, z={z_p95:.1f})",
                    evidence_ids=[event.id]
                )
                anomalies.append(anom)
                event_store.insert_anomaly(anom)

            # B. Hard SLO check on Error Rate
            err_diverged = err_rate > THRESHOLDS["hard_error_rate"]
            self._handle_debounce(hist, "error_rate", err_diverged, now_iso)
            if self._is_debounced_active(hist, "error_rate"):
                onset_ts = hist.debounce_tracker["error_rate"][1]
                sev = min(1.0, (0.5 + err_rate * 0.5) * criticality)
                anom = AnomalyEvent(
                    id=f"anom_{event.service}_err_{onset_ts[-8:].replace(':', '')}",
                    service=event.service,
                    metric_or_pattern="error_rate",
                    onset_ts=onset_ts,
                    detected_ts=now_iso,
                    severity=round(sev, 2),
                    z_score=None,
                    current_value=err_rate,
                    baseline_value=0.001,
                    message=f"{event.service} error rate breached SLO threshold: {err_rate*100:.1f}% errors",
                    evidence_ids=[event.id]
                )
                anomalies.append(anom)
                event_store.insert_anomaly(anom)

            # C. Connection Pool Saturation
            pool_diverged = pool >= THRESHOLDS["pool_saturation_cutoff"]
            self._handle_debounce(hist, "pool_utilization", pool_diverged, now_iso)
            if self._is_debounced_active(hist, "pool_utilization"):
                onset_ts = hist.debounce_tracker["pool_utilization"][1]
                sev = 0.95 * criticality
                anom = AnomalyEvent(
                    id=f"anom_{event.service}_pool_{onset_ts[-8:].replace(':', '')}",
                    service=event.service,
                    metric_or_pattern="pool_utilization",
                    onset_ts=onset_ts,
                    detected_ts=now_iso,
                    severity=round(sev, 2),
                    z_score=None,
                    current_value=pool,
                    baseline_value=0.15,
                    message=f"{event.service} connection pool saturated at {pool*100:.0f}% capacity",
                    evidence_ids=[event.id]
                )
                anomalies.append(anom)
                event_store.insert_anomaly(anom)

            # D. Memory Leak Trend (EWMA climb)
            mem_diverged = mem > THRESHOLDS["memory_pct_cutoff"] or (hist.ewma_memory and hist.ewma_memory > 85.0)
            self._handle_debounce(hist, "memory_pct", mem_diverged, now_iso)
            if self._is_debounced_active(hist, "memory_pct"):
                onset_ts = hist.debounce_tracker["memory_pct"][1]
                anom = AnomalyEvent(
                    id=f"anom_{event.service}_mem_{onset_ts[-8:].replace(':', '')}",
                    service=event.service,
                    metric_or_pattern="memory_pct",
                    onset_ts=onset_ts,
                    detected_ts=now_iso,
                    severity=round(0.85 * criticality, 2),
                    z_score=None,
                    current_value=mem,
                    baseline_value=32.0,
                    message=f"{event.service} memory critical: {mem:.1f}% used (EWMA trend indicates slow-burn leak)",
                    evidence_ids=[event.id]
                )
                anomalies.append(anom)
                event_store.insert_anomaly(anom)

            # Update rolling baselines
            hist.p95_history.append(p95)
            hist.error_rate_history.append(err_rate)
            hist.cpu_history.append(cpu)
            hist.pool_history.append(pool)
            hist.memory_history.append(mem)

        # 2. Log Template Anomaly Evaluation
        elif event.type == "log" and event.severity in ("error", "critical"):
            tpl_id = event.template_id or "UNKNOWN"
            is_new = tpl_id not in hist.seen_templates
            hist.seen_templates.add(tpl_id)

            if tpl_id not in hist.template_timestamps:
                hist.template_timestamps[tpl_id] = deque(maxlen=30)
            hist.template_timestamps[tpl_id].append(now_iso)

            # Frequency spike: > 4 errors of this template in window
            spike = len(hist.template_timestamps[tpl_id]) >= 4
            if is_new or spike:
                sev = 0.90 if event.severity == "critical" else 0.75
                anom = AnomalyEvent(
                    id=f"anom_{event.service}_{tpl_id}_{now_iso[-8:].replace(':', '')}",
                    service=event.service,
                    metric_or_pattern=f"log_template_{tpl_id}",
                    onset_ts=now_iso,
                    detected_ts=now_iso,
                    severity=round(sev * criticality, 2),
                    z_score=None,
                    current_value=len(hist.template_timestamps[tpl_id]),
                    baseline_value=0.0,
                    message=f"{event.service} logged abnormal error spike pattern [{tpl_id}]: {event.message[:80]}",
                    evidence_ids=[event.id]
                )
                anomalies.append(anom)
                event_store.insert_anomaly(anom)

        return anomalies

    def _handle_debounce(self, hist: ServiceMetricHistory, metric: str, is_diverged: bool, ts: str):
        """Maintains debounce counter and true onset timestamp."""
        if is_diverged:
            if metric not in hist.debounce_tracker:
                # First time signal left baseline: save onset_ts!
                hist.debounce_tracker[metric] = (1, ts)
            else:
                count, onset = hist.debounce_tracker[metric]
                hist.debounce_tracker[metric] = (count + 1, onset)
        else:
            # Signal back to normal, clear debounce
            if metric in hist.debounce_tracker:
                del hist.debounce_tracker[metric]

    def _is_debounced_active(self, hist: ServiceMetricHistory, metric: str) -> bool:
        if metric in hist.debounce_tracker:
            count, _ = hist.debounce_tracker[metric]
            return count >= THRESHOLDS["debounce_windows"]
        return False


# Global detector instance
anomaly_detector = AnomalyDetector()
