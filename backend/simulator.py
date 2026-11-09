"""
J.A.R.V.I.S. Asynchronous Microservice Failure Simulator.
Emulates 6 microservices in a single lightweight async event loop with realistic
cascading failure propagation, telemetry generation (metrics & logs with trace IDs),
and interactive chaos injection / live healing.
"""

import asyncio
import random
import uuid
import datetime
from typing import Dict, Any, List, Optional
from .schema import UnifiedEvent
from .store import event_store
from .config import SERVICE_MANIFEST


class ServiceState:
    def __init__(self, name: str, manifest: Dict[str, Any]):
        self.name = name
        self.tier = manifest["tier"]
        self.host = manifest["host"]
        self.is_external = manifest["is_external"]
        self.dependencies = manifest["dependencies"]
        
        # Baselines
        self.baseline_p50 = 15.0 if self.tier != "database" else 8.0
        self.baseline_p95 = 35.0 if self.tier != "database" else 20.0
        self.baseline_cpu = 18.0
        self.baseline_memory = 32.0
        self.baseline_pool = 0.15
        
        # Dynamic telemetry
        self.p50_latency = self.baseline_p50
        self.p95_latency = self.baseline_p95
        self.error_rate = 0.001
        self.cpu_pct = self.baseline_cpu
        self.memory_pct = self.baseline_memory
        self.pool_utilization = self.baseline_pool
        self.queue_depth = 0
        
        # Injected faults
        self.active_fault: Optional[str] = None
        self.fault_params: Dict[str, Any] = {}
        self.fault_onset_ts: Optional[str] = None
        self.memory_leak_rate = 0.0


class Simulator:
    def __init__(self):
        self.services: Dict[str, ServiceState] = {
            name: ServiceState(name, cfg) for name, cfg in SERVICE_MANIFEST.items()
        }
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.global_traffic_multiplier = 1.0
        self.listeners: List[Any] = []
        self.current_scenario_name = "Normal Baseline"

    def register_listener(self, callback):
        self.listeners.append(callback)

    def unregister_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._simulation_loop())

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def inject_fault(self, fault_type: str, target_service: str = "user-db", params: Optional[Dict[str, Any]] = None) -> str:
        """Injects a specific chaos fault profile into the simulator."""
        params = params or {}
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if target_service not in self.services:
            target_service = "user-db"

        svc = self.services[target_service]
        svc.active_fault = fault_type
        svc.fault_params = params
        svc.fault_onset_ts = now_iso
        self.current_scenario_name = f"{fault_type} on {target_service}"

        # Emit an audit event for config / deploy faults if applicable
        if fault_type == "bad_deploy":
            deploy_event = UnifiedEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                ts=now_iso,
                ts_received=now_iso,
                source="api",
                type="deploy",
                service=target_service,
                host=svc.host,
                severity="warn",
                message=f"Deployment v2.4.1 completed on {target_service} (Commit #8f9b1c)",
                template_id="T01_DEPLOY_COMMIT",
                attrs={"version": "v2.4.1", "commit": "8f9b1c", "author": "devops-ci"},
                fingerprint=f"{target_service}|T01_DEPLOY_COMMIT|warn"
            )
            event_store.insert_event(deploy_event)

        elif fault_type == "config_error":
            cfg_event = UnifiedEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                ts=now_iso,
                ts_received=now_iso,
                source="api",
                type="config",
                service=target_service,
                host=svc.host,
                severity="warn",
                message=f"Environment variable AUTH_JWT_SECRET updated by admin",
                template_id="T02_CONFIG_UPDATE",
                attrs={"key": "AUTH_JWT_SECRET", "updated_by": "secops"},
                fingerprint=f"{target_service}|T02_CONFIG_UPDATE|warn"
            )
            event_store.insert_event(cfg_event)

        return f"Injected {fault_type} into {target_service} at {now_iso}"

    def heal_service(self, service_name: str) -> bool:
        """Removes active faults from a service and resets its baselines."""
        if service_name not in self.services:
            return False
        svc = self.services[service_name]
        svc.active_fault = None
        svc.fault_params = {}
        svc.fault_onset_ts = None
        svc.memory_leak_rate = 0.0
        
        # Reset telemetry
        svc.p50_latency = svc.baseline_p50
        svc.p95_latency = svc.baseline_p95
        svc.error_rate = 0.001
        svc.cpu_pct = svc.baseline_cpu
        svc.memory_pct = svc.baseline_memory
        svc.pool_utilization = svc.baseline_pool
        svc.queue_depth = 0
        return True

    def reset_all(self):
        """Clears all faults, resets all services to baseline health."""
        for name in self.services:
            self.heal_service(name)
        self.global_traffic_multiplier = 1.0
        self.current_scenario_name = "Normal Baseline"

    async def _simulation_loop(self):
        """Main 1-second cadence telemetry generation loop."""
        while self.is_running:
            try:
                events_to_emit = self._tick()
                if events_to_emit:
                    event_store.insert_events_batch(events_to_emit)
                    # Notify WebSocket subscribers
                    for listener in self.listeners:
                        try:
                            listener(events_to_emit)
                        except Exception:
                            pass
                await asyncio.sleep(1.0)
            except Exception as e:
                await asyncio.sleep(1.0)

    def _tick(self) -> List[UnifiedEvent]:
        """Calculates 1-second state step and creates telemetry events."""
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now_dt.isoformat()
        emitted_events: List[UnifiedEvent] = []

        # 1. Update internal state based on active faults
        for name, svc in self.services.items():
            fault = svc.active_fault
            
            # Normal baseline jitter
            jitter = random.uniform(-0.08, 0.08)
            svc.cpu_pct = max(5.0, min(95.0, svc.baseline_cpu * (1 + jitter) * self.global_traffic_multiplier))
            svc.p50_latency = max(2.0, svc.baseline_p50 * (1 + jitter) * self.global_traffic_multiplier)
            svc.p95_latency = max(5.0, svc.baseline_p95 * (1 + jitter) * self.global_traffic_multiplier)
            svc.pool_utilization = max(0.05, min(0.95, svc.baseline_pool * (1 + jitter) * self.global_traffic_multiplier))
            svc.error_rate = 0.001

            # Apply specific fault logic
            if fault in ("db_failure", "db_pool_exhaust", "pool_exhaust"):
                svc.pool_utilization = 1.0
                svc.queue_depth = random.randint(80, 200)
                svc.p95_latency = random.uniform(3500.0, 5200.0)
                svc.error_rate = random.uniform(0.65, 0.95)
                svc.cpu_pct = random.uniform(85.0, 98.0)

            elif fault == "db_slowdown":
                svc.p95_latency = random.uniform(2200.0, 3800.0)
                svc.pool_utilization = 0.82
                svc.error_rate = random.uniform(0.15, 0.35)

            elif fault == "payment_gw_503":
                svc.error_rate = 1.0
                svc.p95_latency = random.uniform(4000.0, 6000.0)

            elif fault == "bad_deploy":
                svc.error_rate = random.uniform(0.70, 0.90)
                svc.p95_latency = random.uniform(800.0, 1500.0)

            elif fault == "memory_leak":
                svc.memory_pct = min(99.5, svc.memory_pct + random.uniform(1.5, 3.5))
                if svc.memory_pct > 92.0:
                    svc.error_rate = random.uniform(0.40, 0.80)
                    svc.p95_latency = random.uniform(1200.0, 3000.0)

            elif fault == "retry_storm":
                svc.p95_latency = random.uniform(1500.0, 3200.0)
                svc.queue_depth = random.randint(150, 400)
                svc.error_rate = random.uniform(0.30, 0.60)

            elif fault == "disk_full":
                svc.error_rate = 0.98
                svc.p95_latency = random.uniform(2000.0, 4500.0)

            elif fault == "network_partition":
                svc.p95_latency = random.uniform(5000.0, 8000.0)
                svc.error_rate = 0.85

            elif fault == "credential_expiry":
                svc.error_rate = 1.0

            elif fault == "cache_stampede":
                svc.error_rate = 0.45
                svc.p95_latency = random.uniform(1800.0, 3400.0)

        # 2. Propagate cascade downstream along dependencies
        # auth-service depends on user-db and redis-cache
        auth_svc = self.services["auth-service"]
        user_db = self.services["user-db"]
        if user_db.error_rate > 0.10 and not auth_svc.active_fault:
            auth_svc.p95_latency = user_db.p95_latency * 0.9 + random.uniform(50, 150)
            auth_svc.error_rate = min(0.95, user_db.error_rate * 0.85)

        # payment-api depends on payment-gateway and orders-db
        pay_svc = self.services["payment-api"]
        pay_gw = self.services["payment-gateway"]
        orders_db = self.services["orders-db"]
        if pay_gw.error_rate > 0.10 and not pay_svc.active_fault:
            pay_svc.p95_latency = pay_gw.p95_latency * 0.85 + random.uniform(30, 100)
            pay_svc.error_rate = min(0.98, pay_gw.error_rate * 0.90)
        elif orders_db.error_rate > 0.10 and not pay_svc.active_fault:
            pay_svc.p95_latency = orders_db.p95_latency * 0.85
            pay_svc.error_rate = min(0.95, orders_db.error_rate * 0.80)

        # web-gateway depends on auth-service and payment-api
        web_svc = self.services["web-gateway"]
        max_downstream_err = max(auth_svc.error_rate, pay_svc.error_rate)
        if max_downstream_err > 0.10 and not web_svc.active_fault:
            web_svc.error_rate = min(0.92, max_downstream_err * 0.80)
            web_svc.p95_latency = max(auth_svc.p95_latency, pay_svc.p95_latency) + random.uniform(20, 80)

        # 3. Generate Metric & Log telemetry events for each service
        for name, svc in self.services.items():
            trace_id = f"tr_{uuid.uuid4().hex[:10]}"
            user_id = f"usr_{random.randint(10000, 99999)}"

            # Metric event
            metric_sev = "critical" if svc.error_rate > 0.20 or svc.pool_utilization > 0.90 else (
                "error" if svc.error_rate > 0.05 else ("warn" if svc.p95_latency > 200 else "info")
            )
            emitted_events.append(UnifiedEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                ts=now_iso,
                ts_received=now_iso,
                source="simulator",
                type="metric",
                service=name,
                host=svc.host,
                severity=metric_sev,
                message=f"{name} metrics: p95={svc.p95_latency:.1f}ms, err={svc.error_rate*100:.1f}%, cpu={svc.cpu_pct:.1f}%, pool={svc.pool_utilization*100:.0f}%",
                template_id=f"T_METRIC_{name.upper()}",
                attrs={
                    "trace_id": trace_id,
                    "user_id": user_id,
                    "latency_p50": round(svc.p50_latency, 2),
                    "latency_p95": round(svc.p95_latency, 2),
                    "error_rate": round(svc.error_rate, 4),
                    "cpu_pct": round(svc.cpu_pct, 2),
                    "memory_pct": round(svc.memory_pct, 2),
                    "pool_utilization": round(svc.pool_utilization, 3),
                    "queue_depth": svc.queue_depth
                },
                fingerprint=f"{name}|METRIC_REPORT|{metric_sev}"
            ))

            # Log events when errors / warnings occur
            if svc.error_rate > 0.03 or svc.active_fault:
                log_sev = "critical" if svc.error_rate > 0.30 else "error"
                status_code = 500 if svc.tier != "gateway" else 502

                # Context-specific realistic log messages
                if name == "user-db" and (svc.active_fault in ("db_failure", "db_pool_exhaust") or svc.pool_utilization > 0.85):
                    log_msg = f"FATAL: remaining connection slots are reserved for non-replication superuser connections (active={int(svc.pool_utilization*50)}/50)"
                    tpl = "T42_CONN_POOL_EXHAUST"
                elif name == "auth-service" and user_db.error_rate > 0.10:
                    log_msg = f"User session verification failed: database connection timeout after 5000ms"
                    tpl = "T19_DB_TIMEOUT"
                elif name == "payment-gateway":
                    log_msg = f"HTTP 503 Service Unavailable: upstream provider experiencing degraded network connectivity"
                    tpl = "T88_EXT_GW_503"
                    status_code = 503
                elif name == "payment-api" and pay_gw.error_rate > 0.10:
                    log_msg = f"Payment capture failed for user {user_id}: payment-gateway returned HTTP 503"
                    tpl = "T34_PAY_CAPTURE_FAILED"
                elif name == "payment-api" and svc.active_fault == "bad_deploy":
                    log_msg = f"NullPointerException in PaymentController.processTransaction() line 142 (v2.4.1 regression)"
                    tpl = "T55_NPE_REGRESSION"
                elif name == "web-gateway":
                    log_msg = f"Gateway upstream timeout: 504 Gateway Timeout on POST /api/checkout"
                    tpl = "T91_GATEWAY_TIMEOUT"
                    status_code = 504
                else:
                    log_msg = f"Unhandled exception processing request: connection refused on host {svc.host}"
                    tpl = "T10_CONN_REFUSED"

                emitted_events.append(UnifiedEvent(
                    id=f"evt_{uuid.uuid4().hex[:8]}",
                    ts=now_iso,
                    ts_received=now_iso,
                    source="simulator",
                    type="log",
                    service=name,
                    host=svc.host,
                    severity=log_sev,
                    message=log_msg,
                    template_id=tpl,
                    attrs={
                        "trace_id": trace_id,
                        "user_id": user_id,
                        "status": status_code,
                        "latency_ms": round(svc.p95_latency, 1)
                    },
                    fingerprint=f"{name}|{tpl}|{log_sev}"
                ))

        return emitted_events


# Global simulator instance
simulator = Simulator()
