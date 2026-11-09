"""
J.A.R.V.I.S. Unified Event Schema and Data Models.
Defines canonical representations for Events, Anomalies, Topology,
Incidents, Root Causes, Impact, and Recommendations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import datetime


class UnifiedEvent(BaseModel):
    """Canonical event format ingested across all sources."""
    id: str = Field(..., description="Unique event identifier (e.g. evt_8f21)")
    ts: str = Field(..., description="Original event timestamp in ISO 8601 UTC")
    ts_received: str = Field(..., description="Time event reached ingestion pipeline (clock skew handling)")
    source: str = Field(..., description="simulator | file | api | otel")
    type: str = Field(..., description="log | metric | alert | trace | deploy | config")
    service: str = Field(..., description="Microservice name (e.g. payment-api)")
    host: str = Field(default="node-1", description="Host or container ID")
    severity: str = Field(..., description="info | warn | error | critical")
    message: str = Field(..., description="Human-readable event message")
    template_id: Optional[str] = Field(default=None, description="Drain3 mined pattern ID (e.g. T42)")
    attrs: Dict[str, Any] = Field(default_factory=dict, description="Metadata: trace_id, user_id, latency_ms, etc.")
    fingerprint: str = Field(..., description="Deduplication key: service|template_id|severity")


class AnomalyEvent(BaseModel):
    """An anomalous metric deviation or abnormal log pattern spike."""
    id: str
    service: str
    metric_or_pattern: str
    onset_ts: str
    detected_ts: str
    severity: float = Field(..., ge=0.0, le=1.0, description="Severity score 0 to 1")
    z_score: Optional[float] = None
    current_value: float
    baseline_value: float
    message: str
    evidence_ids: List[str] = Field(default_factory=list)


class TopologyNode(BaseModel):
    id: str
    name: str
    tier: str  # gateway, service, database, cache, external
    host: str
    is_external: bool = False


class TopologyEdge(BaseModel):
    source: str
    target: str
    provenance: str  # trace, manifest, log, inferred
    confidence: float  # 0.0 to 1.0
    latency_baseline_ms: float = 20.0


class TopologyGraph(BaseModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]


class RootCauseCandidate(BaseModel):
    service: str
    rank: int
    score: float = Field(..., description="Normalized probability (0 to 1)")
    cause_type: str = Field(..., description="resource_exhaustion | dependency_outage | deploy_regression | network_degradation | traffic_surge | config_error | credential_expiry")
    evidence_bullets: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    onset_ts: str
    features: Dict[str, float] = Field(default_factory=dict)


class JourneyStatus(BaseModel):
    name: str
    status: str  # healthy, degraded, failing
    failure_rate_pct: float
    impact_description: str


class ImpactSummary(BaseModel):
    blast_radius_nodes: List[str]
    blast_radius_hop_counts: Dict[str, int]
    user_journeys: Dict[str, JourneyStatus]
    affected_users_count: int
    failed_transactions_count: int
    revenue_at_risk: float
    time_since_incident_start_sec: float
    customer_severity: str  # P1, P2, P3


class Recommendation(BaseModel):
    id: str
    title: str
    action_type: str
    expected_effect: str
    time_to_execute: str
    risk_level: str  # Low, Medium, High
    reversibility: bool
    ranking: str
    do_not_do_warning: Optional[str] = None
    owner: str
    service: str
    script_command: Optional[str] = None


class CounterfactualResult(BaseModel):
    mode: str  # live_simulator | model_based_what_if
    tested_candidate: str
    verified: bool
    recovery_rate_pct: float
    unexplained_symptoms_remaining: int
    message: str
    timestamp: str


class Incident(BaseModel):
    """Unified correlated incident containing causal analysis and evidence."""
    id: str
    title: str
    status: str = "investigating"  # active, investigating, verified, resolved, ambiguous
    severity: str = "P1"  # P1, P2, P3
    created_at: str
    updated_at: str
    root_cause_candidates: List[RootCauseCandidate] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_level: str = "moderate"  # high, moderate, ambiguous
    is_ambiguous: bool = False
    disambiguation_hint: Optional[str] = None
    explained_symptoms_ratio: float = 0.0
    services_involved: List[str] = Field(default_factory=list)
    event_ids: List[str] = Field(default_factory=list)
    alert_count: int = 0
    suppressed_count: int = 0
    impact: Optional[ImpactSummary] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
    counterfactual_result: Optional[CounterfactualResult] = None
    historical_link: Optional[str] = None  # Scenario 20 recurrence link


class WarRoomQuery(BaseModel):
    query: str
    incident_id: Optional[str] = None


class WarRoomResponse(BaseModel):
    answer: str
    evidence_ids: List[str]
    suggested_actions: List[str] = Field(default_factory=list)
    tier_used: str  # hosted_api | local_model | deterministic_template
