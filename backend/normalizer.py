"""
J.A.R.V.I.S. Event Normalizer.
Standardizes heterogeneous telemetry from Simulator, Files, and Webhooks into UnifiedEvent schema.
"""

import uuid
import datetime
from typing import Dict, Any, Union
from dateutil import parser as date_parser
from .schema import UnifiedEvent
from .drain_miner import log_miner


def parse_timestamp_to_utc_iso(ts_val: Any) -> str:
    """Safely converts arbitrary timestamp representation to UTC ISO-8601 string."""
    if not ts_val:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
    if isinstance(ts_val, (int, float)):
        # Handle Unix epoch seconds or ms
        if ts_val > 1e11:  # Milliseconds
            ts_val = ts_val / 1000.0
        return datetime.datetime.fromtimestamp(ts_val, tz=datetime.timezone.utc).isoformat()
    if isinstance(ts_val, str):
        try:
            dt = date_parser.parse(ts_val)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc).isoformat()
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def normalize_event(raw: Union[Dict[str, Any], UnifiedEvent]) -> UnifiedEvent:
    """Converts a raw dictionary into a strictly validated UnifiedEvent."""
    if isinstance(raw, UnifiedEvent):
        return raw

    evt_id = raw.get("id") or f"evt_{uuid.uuid4().hex[:8]}"
    ts = parse_timestamp_to_utc_iso(raw.get("ts"))
    ts_received = parse_timestamp_to_utc_iso(raw.get("ts_received"))

    service = str(raw.get("service") or "unknown-service").strip().lower()
    host = str(raw.get("host") or "node-default").strip()
    source = str(raw.get("source") or "api").strip()
    event_type = str(raw.get("type") or "log").strip().lower()

    # Normalize severity
    raw_sev = str(raw.get("severity") or "info").lower().strip()
    if raw_sev in ("crit", "critical", "fatal", "emerg"):
        severity = "critical"
    elif raw_sev in ("err", "error", "failed", "failure"):
        severity = "error"
    elif raw_sev in ("warn", "warning"):
        severity = "warn"
    else:
        severity = "info"

    raw_msg = str(raw.get("message") or "")
    template_id, cleaned_msg = log_miner.process_message(raw_msg)
    override_template = raw.get("template_id")
    if override_template:
        template_id = override_template

    attrs = raw.get("attrs") or {}
    if not isinstance(attrs, dict):
        attrs = {"raw_attrs": str(attrs)}

    # Mask any PII in string attributes
    for k, v in list(attrs.items()):
        if isinstance(v, str):
            attrs[k] = log_miner.mask_pii(v)

    fingerprint = raw.get("fingerprint") or f"{service}|{template_id}|{severity}"

    return UnifiedEvent(
        id=evt_id,
        ts=ts,
        ts_received=ts_received,
        source=source,
        type=event_type,
        service=service,
        host=host,
        severity=severity,
        message=cleaned_msg,
        template_id=template_id,
        attrs=attrs,
        fingerprint=fingerprint
    )
