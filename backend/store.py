"""
J.A.R.V.I.S. SQLite Event Store.
Provides persistent zero-setup storage with indexed querying,
fingerprint deduplication, and anomaly tracking.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from .config import SQLITE_DB_PATH
from .schema import UnifiedEvent, AnomalyEvent, Incident


class EventStore:
    def __init__(self, db_path: str = str(SQLITE_DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Unified Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    ts_received TEXT NOT NULL,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    service TEXT NOT NULL,
                    host TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    template_id TEXT,
                    attrs TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_service ON events(service)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_fingerprint ON events(fingerprint)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity)")

            # Anomalies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    metric_or_pattern TEXT NOT NULL,
                    onset_ts TEXT NOT NULL,
                    detected_ts TEXT NOT NULL,
                    severity REAL NOT NULL,
                    z_score REAL,
                    current_value REAL NOT NULL,
                    baseline_value REAL NOT NULL,
                    message TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_ts ON anomalies(onset_ts)")

            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    confidence_level TEXT NOT NULL,
                    is_ambiguous INTEGER NOT NULL,
                    data TEXT NOT NULL
                )
            """)

            # Fingerprint Aggregation table (Alert Storm Suppression)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fingerprint_counts (
                    fingerprint TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    template_id TEXT,
                    sample_message TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
            """)
            conn.commit()

    def insert_event(self, event: UnifiedEvent) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO events
                (id, ts, ts_received, source, type, service, host, severity, message, template_id, attrs, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.ts, event.ts_received, event.source, event.type,
                event.service, event.host, event.severity, event.message,
                event.template_id, json.dumps(event.attrs), event.fingerprint
            ))

            # Update alert storm suppression table
            cursor.execute("""
                INSERT INTO fingerprint_counts (fingerprint, service, severity, template_id, sample_message, count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    count = count + 1,
                    last_seen = excluded.last_seen
            """, (
                event.fingerprint, event.service, event.severity, event.template_id,
                event.message, event.ts, event.ts
            ))
            conn.commit()

    def insert_events_batch(self, events: List[UnifiedEvent]) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            for event in events:
                cursor.execute("""
                    INSERT OR REPLACE INTO events
                    (id, ts, ts_received, source, type, service, host, severity, message, template_id, attrs, fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id, event.ts, event.ts_received, event.source, event.type,
                    event.service, event.host, event.severity, event.message,
                    event.template_id, json.dumps(event.attrs), event.fingerprint
                ))
                cursor.execute("""
                    INSERT INTO fingerprint_counts (fingerprint, service, severity, template_id, sample_message, count, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(fingerprint) DO UPDATE SET
                        count = count + 1,
                        last_seen = excluded.last_seen
                """, (
                    event.fingerprint, event.service, event.severity, event.template_id,
                    event.message, event.ts, event.ts
                ))
            conn.commit()

    def get_recent_events(self, limit: int = 100, service: Optional[str] = None, min_severity: Optional[str] = None) -> List[UnifiedEvent]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            if service:
                query += " AND service = ?"
                params.append(service)
            if min_severity == "error":
                query += " AND severity IN ('error', 'critical')"
            elif min_severity == "warn":
                query += " AND severity IN ('warn', 'error', 'critical')"

            query += " ORDER BY ts DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            events = []
            for r in rows:
                events.append(UnifiedEvent(
                    id=r["id"],
                    ts=r["ts"],
                    ts_received=r["ts_received"],
                    source=r["source"],
                    type=r["type"],
                    service=r["service"],
                    host=r["host"],
                    severity=r["severity"],
                    message=r["message"],
                    template_id=r["template_id"],
                    attrs=json.loads(r["attrs"]),
                    fingerprint=r["fingerprint"]
                ))
            return events

    def get_events_by_ids(self, event_ids: List[str]) -> List[UnifiedEvent]:
        if not event_ids:
            return []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(event_ids))
            cursor.execute(f"SELECT * FROM events WHERE id IN ({placeholders})", event_ids)
            rows = cursor.fetchall()
            events = []
            for r in rows:
                events.append(UnifiedEvent(
                    id=r["id"],
                    ts=r["ts"],
                    ts_received=r["ts_received"],
                    source=r["source"],
                    type=r["type"],
                    service=r["service"],
                    host=r["host"],
                    severity=r["severity"],
                    message=r["message"],
                    template_id=r["template_id"],
                    attrs=json.loads(r["attrs"]),
                    fingerprint=r["fingerprint"]
                ))
            return events

    def insert_anomaly(self, anomaly: AnomalyEvent) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO anomalies
                (id, service, metric_or_pattern, onset_ts, detected_ts, severity, z_score, current_value, baseline_value, message, evidence_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anomaly.id, anomaly.service, anomaly.metric_or_pattern, anomaly.onset_ts,
                anomaly.detected_ts, anomaly.severity, anomaly.z_score, anomaly.current_value,
                anomaly.baseline_value, anomaly.message, json.dumps(anomaly.evidence_ids)
            ))
            conn.commit()

    def get_recent_anomalies(self, limit: int = 50) -> List[AnomalyEvent]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM anomalies ORDER BY onset_ts DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            anomalies = []
            for r in rows:
                anomalies.append(AnomalyEvent(
                    id=r["id"],
                    service=r["service"],
                    metric_or_pattern=r["metric_or_pattern"],
                    onset_ts=r["onset_ts"],
                    detected_ts=r["detected_ts"],
                    severity=r["severity"],
                    z_score=r["z_score"],
                    current_value=r["current_value"],
                    baseline_value=r["baseline_value"],
                    message=r["message"],
                    evidence_ids=json.loads(r["evidence_ids"])
                ))
            return anomalies

    def save_incident(self, incident: Incident) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO incidents
                (id, title, status, severity, created_at, updated_at, confidence_score, confidence_level, is_ambiguous, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident.id, incident.title, incident.status, incident.severity,
                incident.created_at, incident.updated_at, incident.confidence_score,
                incident.confidence_level, 1 if incident.is_ambiguous else 0,
                json.dumps(incident.model_dump())
            ))
            conn.commit()

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM incidents WHERE id = ?", (incident_id,))
            row = cursor.fetchone()
            if row:
                return Incident.model_validate_json(row["data"])
            return None

    def get_recent_incidents(self, limit: int = 10) -> List[Incident]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [Incident.model_validate_json(r["data"]) for r in rows]

    def get_suppressed_alerts_summary(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fingerprint_counts ORDER BY count DESC LIMIT 20")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def clear_all(self) -> None:
        """Reset data store for clean chaos runs and demo reset."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM anomalies")
            cursor.execute("DELETE FROM incidents")
            cursor.execute("DELETE FROM fingerprint_counts")
            conn.commit()


# Global singleton store
event_store = EventStore()
