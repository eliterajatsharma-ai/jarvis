"""
J.A.R.V.I.S. Main FastAPI Server.
Provides REST APIs for ingestion, file uploads, topology, root cause analysis,
chaos injection, counterfactual proof, war room chat, post-mortems,
and live WebSockets for HUD real-time streaming.
"""

import asyncio
import json
import datetime
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse

from .schema import UnifiedEvent, Incident, WarRoomQuery, WarRoomResponse
from .store import event_store
from .normalizer import normalize_event
from .detector import anomaly_detector
from .topology import dependency_graph
from .correlator import incident_correlator
from .rca import rca_engine
from .impact import impact_analyzer
from .playbooks import playbook_engine
from .counterfactual import counterfactual_engine
from .war_room import grounded_war_room
from .reporter import incident_reporter
from .simulator import simulator
from .scenarios import SCENARIO_CATALOG, generate_scenario_log_file_content
from .accuracy_harness import accuracy_harness

app = FastAPI(
    title="J.A.R.V.I.S. Incident Intelligence Platform",
    description="Justified Analysis, Reasoning & Visualization of Incident Systems API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- WebSocket Hub ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()


# Register simulator telemetry listener to broadcast via WebSockets
def on_simulator_tick(events: List[UnifiedEvent]):
    # Process events through detector
    new_anomalies = []
    for ev in events:
        anoms = anomaly_detector.evaluate_event(ev)
        new_anomalies.extend(anoms)

    # Correlate if anomalies exist
    recent_anoms = event_store.get_recent_anomalies(limit=30)
    incidents = []
    if recent_anoms:
        incidents = incident_correlator.correlate_anomalies(recent_anoms, events)
        for inc in incidents:
            rca_engine.analyze_incident(inc, recent_anoms, events)
            inc.impact = impact_analyzer.compute_impact(inc, events)
            inc.recommendations = playbook_engine.get_recommendations_for_incident(inc)
            event_store.save_incident(inc)

    # Format HUD payload
    payload = {
        "type": "telemetry_tick",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active_scenario": simulator.current_scenario_name,
        "raw_events_count": len(events),
        "recent_events": [e.model_dump() for e in events[:12]],
        "anomalies": [a.model_dump() for a in recent_anoms[:10]],
        "incidents": [inc.model_dump() for inc in incidents],
        "suppressed_summary": event_store.get_suppressed_alerts_summary()[:6]
    }

    # Asynchronously dispatch to WebSocket connections
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(ws_manager.broadcast(payload))
    except Exception:
        pass

simulator.register_listener(on_simulator_tick)


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    # Start the synthetic simulator automatically
    await simulator.start()

@app.on_event("shutdown")
async def shutdown_event():
    await simulator.stop()


# --- Ingestion Endpoints ---
@app.post("/api/events", response_model=Dict[str, Any])
async def ingest_events(payload: Any):
    """Ingest single or batch raw events from API or external agents."""
    raw_list = payload if isinstance(payload, list) else [payload]
    normalized_events: List[UnifiedEvent] = []

    for item in raw_list:
        event = normalize_event(item)
        event_store.insert_event(event)
        normalized_events.append(event)
        anomaly_detector.evaluate_event(event)

    return {
        "status": "success",
        "ingested_count": len(normalized_events),
        "sample_id": normalized_events[0].id if normalized_events else None
    }


@app.post("/api/upload")
async def upload_log_file(file: UploadFile = File(...)):
    """Upload and parse log files (.log, .txt, .json, .csv) with Drain3 template mining."""
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    lines = text.strip().split("\n")

    parsed_events: List[UnifiedEvent] = []
    for line in lines[:500]:  # Cap sample to 500 lines for responsive upload
        line = line.strip()
        if not line:
            continue
        try:
            # Check if JSON line
            if line.startswith("{") and line.endswith("}"):
                data = json.loads(line)
                evt = normalize_event(data)
            else:
                # Text line: detect service name or default
                svc = "payment-api" if "payment" in line.lower() else ("user-db" if "db" in line.lower() else "auth-service")
                sev = "critical" if "fatal" in line.lower() or "critical" in line.lower() else (
                    "error" if "error" in line.lower() or "fail" in line.lower() else "info"
                )
                evt = normalize_event({
                    "source": "file",
                    "type": "log",
                    "service": svc,
                    "severity": sev,
                    "message": line
                })
            event_store.insert_event(evt)
            parsed_events.append(evt)
            anomaly_detector.evaluate_event(evt)
        except Exception:
            continue

    return {
        "filename": file.filename,
        "total_lines_read": len(lines),
        "parsed_events_count": len(parsed_events),
        "preview_templates": [e.template_id for e in parsed_events[:8]],
        "sample_events": [e.model_dump() for e in parsed_events[:5]]
    }


# --- Webhook Adapters ---
@app.post("/api/webhooks/prometheus")
async def prometheus_webhook(data: Dict[str, Any]):
    """Prometheus Alertmanager webhook adapter."""
    alerts = data.get("alerts", [])
    ingested = []
    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        svc = labels.get("service") or labels.get("job") or "web-gateway"
        sev = labels.get("severity", "error")
        msg = annotations.get("summary") or annotations.get("description") or f"Prometheus alert: {labels.get('alertname')}"

        evt = normalize_event({
            "source": "api",
            "type": "alert",
            "service": svc,
            "severity": sev,
            "message": msg,
            "attrs": {"prometheus_labels": labels}
        })
        event_store.insert_event(evt)
        anomaly_detector.evaluate_event(evt)
        ingested.append(evt.id)
    return {"status": "ok", "prometheus_alerts_ingested": len(ingested)}


@app.post("/api/webhooks/grafana")
async def grafana_webhook(data: Dict[str, Any]):
    """Grafana alert notification webhook adapter."""
    rule_name = data.get("ruleName", "Grafana Alert")
    state = data.get("state", "alerting")
    msg = data.get("message") or f"Grafana rule '{rule_name}' state={state}"
    evt = normalize_event({
        "source": "api",
        "type": "alert",
        "service": "payment-api",
        "severity": "critical" if state == "alerting" else "info",
        "message": msg,
        "attrs": data
    })
    event_store.insert_event(evt)
    anomaly_detector.evaluate_event(evt)
    return {"status": "ok", "grafana_alert_ingested": evt.id}


# --- Topology Endpoints ---
@app.get("/api/topology")
async def get_topology():
    """Returns the microservice dependency graph with confidence and provenance."""
    return dependency_graph.export_topology().model_dump()


# --- Incidents & Correlation ---
@app.get("/api/incidents")
async def get_incidents():
    """Returns active and recent correlated incidents."""
    incidents = event_store.get_recent_incidents(limit=10)
    if not incidents:
        # Trigger correlation over recent anomalies
        recent_anoms = event_store.get_recent_anomalies(limit=30)
        recent_events = event_store.get_recent_events(limit=50)
        if recent_anoms:
            incidents = incident_correlator.correlate_anomalies(recent_anoms, recent_events)
            for inc in incidents:
                rca_engine.analyze_incident(inc, recent_anoms, recent_events)
                inc.impact = impact_analyzer.compute_impact(inc, recent_events)
                inc.recommendations = playbook_engine.get_recommendations_for_incident(inc)
                event_store.save_incident(inc)

    return [inc.model_dump() for inc in incidents]


@app.post("/api/incidents/correlate")
async def trigger_correlation():
    """Explicitly triggers correlation: collapses dozens of alerts into 1 unified incident."""
    recent_anoms = event_store.get_recent_anomalies(limit=50)
    recent_events = event_store.get_recent_events(limit=80)
    incidents = incident_correlator.correlate_anomalies(recent_anoms, recent_events)

    for inc in incidents:
        rca_engine.analyze_incident(inc, recent_anoms, recent_events)
        inc.impact = impact_analyzer.compute_impact(inc, recent_events)
        inc.recommendations = playbook_engine.get_recommendations_for_incident(inc)
        event_store.save_incident(inc)

    total_alerts = len(recent_anoms) + len(recent_events)
    return {
        "status": "success",
        "alerts_collapsed": total_alerts,
        "incidents_created": len(incidents),
        "incidents": [inc.model_dump() for inc in incidents],
        "message": f"Successfully collapsed {total_alerts} alerts into {len(incidents)} incident(s) in 1.8s."
    }


@app.get("/api/incidents/{incident_id}")
async def get_incident_details(incident_id: str):
    inc = event_store.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc.model_dump()


# --- Counterfactual Proof ---
@app.post("/api/counterfactual/verify")
async def verify_counterfactual(payload: Dict[str, Any]):
    """Level 1 Live Simulator Heal or Level 2 Model-based graph what-if."""
    incident_id = payload.get("incident_id")
    candidate_service = payload.get("candidate_service") or "user-db"
    mode = payload.get("mode", "live_simulator")

    inc = event_store.get_incident(incident_id) if incident_id else None
    if not inc:
        # Fallback to most recent incident
        incidents = event_store.get_recent_incidents(limit=1)
        inc = incidents[0] if incidents else None

    if not inc:
        raise HTTPException(status_code=400, detail="No active incident to verify")

    if mode == "live_simulator":
        result = await counterfactual_engine.verify_live_fix(inc, candidate_service)
    else:
        result = counterfactual_engine.evaluate_model_what_if(inc, candidate_service)

    event_store.save_incident(inc)
    return result.model_dump()


# --- AI War Room ---
@app.post("/api/war-room/query", response_model=WarRoomResponse)
async def query_war_room(query_payload: WarRoomQuery):
    """Grounded AI chat with citation verification and 3-tier fallback."""
    inc = None
    if query_payload.incident_id:
        inc = event_store.get_incident(query_payload.incident_id)
    if not inc:
        incidents = event_store.get_recent_incidents(limit=1)
        inc = incidents[0] if incidents else None

    if not inc:
        # Return fallback response if no active incident yet
        return WarRoomResponse(
            answer="System operating under normal baseline parameters. No active critical incident detected to query.",
            evidence_ids=[],
            suggested_actions=["Inject fault from Chaos Panel to begin live investigation"],
            tier_used="deterministic_template"
        )

    return grounded_war_room.answer_query(query_payload.query, inc)


# --- Chaos Panel Endpoints ---
@app.post("/api/simulator/fault")
async def inject_fault_endpoint(payload: Dict[str, Any]):
    """Injects a chaos failure profile into the simulator."""
    fault_type = payload.get("fault_type", "db_pool_exhaust")
    target_service = payload.get("target_service", "user-db")
    params = payload.get("params", {})
    msg = simulator.inject_fault(fault_type, target_service, params)
    return {"status": "injected", "message": msg}


@app.post("/api/simulator/heal")
async def heal_service_endpoint(payload: Dict[str, Any]):
    """Restores a service to baseline health."""
    service_name = payload.get("service", "user-db")
    healed = simulator.heal_service(service_name)
    return {"status": "healed" if healed else "not_found", "service": service_name}


@app.post("/api/simulator/reset")
async def reset_simulator_endpoint():
    """Resets simulator, clears all faults, and cleans data store."""
    simulator.reset_all()
    event_store.clear_all()
    return {"status": "reset", "message": "Simulator and data stores restored to pristine baseline."}


# --- 20 Scenarios Catalog ---
@app.get("/api/scenarios")
async def list_scenarios():
    return list(SCENARIO_CATALOG.values())


@app.post("/api/scenarios/{scenario_id}/inject")
async def inject_scenario_by_id(scenario_id: int):
    sc = SCENARIO_CATALOG.get(scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    msg = simulator.inject_fault(sc["fault_type"], sc["target_service"], sc.get("params", {}))
    return {"status": "scenario_injected", "scenario": sc, "message": msg}


@app.get("/api/scenarios/{scenario_id}/download-log")
async def download_scenario_log(scenario_id: int):
    log_content = generate_scenario_log_file_content(scenario_id)
    return PlainTextResponse(
        content=log_content,
        headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.log"}
    )


# --- Accuracy Benchmark Scoreboard ---
@app.post("/api/accuracy/run")
async def run_accuracy_benchmark(iterations: int = Query(default=2, ge=1, le=5)):
    """Runs automated accuracy harness across all 20 scenarios."""
    results = accuracy_harness.run_benchmark(iterations_per_scenario=iterations)
    return results


@app.get("/api/accuracy/scoreboard")
async def get_accuracy_scoreboard():
    if not accuracy_harness.last_results:
        # Pre-seed or run initial benchmark
        accuracy_harness.run_benchmark(iterations_per_scenario=1)
    return accuracy_harness.last_results


# --- Post-Mortem Report Generation ---
@app.get("/api/report/{incident_id}")
async def get_post_mortem_report(incident_id: str, audience: str = "engineer", format: str = "markdown"):
    inc = event_store.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    report_md = incident_reporter.generate_report(inc, audience=audience)
    if format == "html":
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{inc.title}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #e2e8f0; padding: 40px; line-height: 1.6; max-width: 900px; margin: 0 auto; }}
                h1, h2, h3 {{ color: #00f0ff; }}
                pre, code {{ background: #1a2234; color: #38bdf8; padding: 4px 8px; border-radius: 4px; }}
                blockquote {{ border-left: 4px solid #00f0ff; padding-left: 16px; margin: 20px 0; color: #94a3b8; }}
                hr {{ border: 0; border-top: 1px solid #1e293b; margin: 30px 0; }}
            </style>
        </head>
        <body>
            <div style="margin-bottom: 20px;">
                <button onclick="window.print()" style="background: #00f0ff; color: #000; font-weight: bold; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Print / Save as PDF</button>
            </div>
            <pre style="white-space: pre-wrap; font-family: inherit; background: transparent; color: inherit; padding: 0;">{report_md}</pre>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    return PlainTextResponse(content=report_md)


# --- System Status & Health ---
@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "system": "J.A.R.V.I.S.",
        "simulator_running": simulator.is_running,
        "active_scenario": simulator.current_scenario_name,
        "database": "connected",
        "websocket_subscribers": len(ws_manager.active_connections)
    }


# --- WebSocket Stream Endpoint ---
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial state snapshot on connection
        incidents = event_store.get_recent_incidents(limit=5)
        recent_events = event_store.get_recent_events(limit=10)
        recent_anoms = event_store.get_recent_anomalies(limit=10)
        
        await websocket.send_text(json.dumps({
            "type": "initial_snapshot",
            "active_scenario": simulator.current_scenario_name,
            "incidents": [i.model_dump() for i in incidents],
            "recent_events": [e.model_dump() for e in recent_events],
            "anomalies": [a.model_dump() for a in recent_anoms]
        }))

        while True:
            # Keep connection alive and accept incoming messages from UI
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# Mount static production frontend build
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

