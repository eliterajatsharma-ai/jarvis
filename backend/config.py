"""
J.A.R.V.I.S. System Configuration and Service Catalog.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "jarvis.db"

# Service Catalog Manifest
SERVICE_MANIFEST = {
    "web-gateway": {
        "tier": "gateway",
        "host": "ingress-node-01",
        "is_external": False,
        "criticality": 1.0,
        "owner": "team-gateway-oncall",
        "dependencies": ["auth-service", "payment-api"],
    },
    "auth-service": {
        "tier": "service",
        "host": "compute-node-01",
        "is_external": False,
        "criticality": 0.9,
        "owner": "team-security-auth",
        "dependencies": ["user-db", "redis-cache"],
    },
    "user-db": {
        "tier": "database",
        "host": "db-cluster-01",
        "is_external": False,
        "criticality": 0.95,
        "owner": "team-dba-core",
        "dependencies": [],
    },
    "payment-api": {
        "tier": "service",
        "host": "compute-node-02",
        "is_external": False,
        "criticality": 0.95,
        "owner": "team-payments-app",
        "dependencies": ["payment-gateway", "orders-db"],
    },
    "payment-gateway": {
        "tier": "external",
        "host": "api.stripe-external.com",
        "is_external": True,
        "criticality": 0.9,
        "owner": "vendor-payments-sla",
        "dependencies": [],
    },
    "orders-db": {
        "tier": "database",
        "host": "db-cluster-02",
        "is_external": False,
        "criticality": 0.95,
        "owner": "team-dba-core",
        "dependencies": [],
    },
    "redis-cache": {
        "tier": "cache",
        "host": "cache-node-01",
        "is_external": False,
        "criticality": 0.7,
        "owner": "team-platform-cache",
        "dependencies": [],
    },
}

# User Journey Definitions
USER_JOURNEYS = {
    "Login": {
        "criticality": 0.9,
        "services": ["web-gateway", "auth-service", "user-db", "redis-cache"],
        "description": "User authentication, token verification, session setup"
    },
    "Checkout": {
        "criticality": 1.0,
        "services": ["web-gateway", "payment-api", "payment-gateway", "orders-db"],
        "description": "Cart payment processing, transaction commit, order confirmation"
    },
    "Browse": {
        "criticality": 0.6,
        "services": ["web-gateway", "auth-service", "redis-cache"],
        "description": "Product catalog queries and cached recommendations"
    }
}

# Average Order Value for Revenue At Risk calculations
AVERAGE_ORDER_VALUE = 84.50

# Anomaly Thresholds
THRESHOLDS = {
    "z_score_cutoff": 2.8,
    "ewma_alpha": 0.2,
    "hard_error_rate": 0.05,       # 5% error rate triggers SLO breach
    "hard_p95_multiplier": 2.5,   # 2.5x baseline p95
    "pool_saturation_cutoff": 0.85, # 85% pool utilization (0.0 to 1.0 scale)
    "memory_pct_cutoff": 88.0,     # 88% memory utilization (0 to 100 scale)
    "cpu_pct_cutoff": 90.0,        # 90% CPU utilization (0 to 100 scale)
    "debounce_windows": 2,         # Consecutive evaluations required
}

# Causal Weights for Root Cause Scoring (Section 6.5)
RCA_WEIGHTS = {
    "onset": 0.28,
    "upstream": 0.25,
    "downstream_coverage": 0.20,
    "random_walk": 0.15,
    "resource_evidence": 0.08,
    "change_evidence": 0.04
}
