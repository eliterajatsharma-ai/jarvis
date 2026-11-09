"""
J.A.R.V.I.S. Drain3 Log Template Miner.
Mines recurring templates from unstructured log messages and masks variable tokens.
"""

import re
from typing import Tuple, Optional
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

# Fallback regex maskers
RE_IP = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
RE_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{16,}\b")
RE_NUM = re.compile(r"\b\d+\b")
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class LogMiner:
    """Extracts pattern templates and masks PII/dynamic tokens."""

    def __init__(self):
        config = TemplateMinerConfig()
        config.drain_sim_th = 0.5
        config.drain_depth = 4
        self.miner = TemplateMiner(config=config)
        self.template_cache = {}

    def mask_pii(self, message: str) -> str:
        """Regex-masks PII (emails, tokens, IPs) prior to storage or LLM processing."""
        m = RE_EMAIL.sub("[EMAIL]", message)
        m = RE_IP.sub("[IP_ADDR]", m)
        m = RE_UUID.sub("[UUID]", m)
        return m

    def process_message(self, message: str) -> Tuple[str, str]:
        """
        Processes a raw log string.
        Returns:
            (template_id, cleaned_template_str)
        """
        masked = self.mask_pii(message)
        try:
            result = self.miner.add_log_message(masked)
            cluster_id = result.get("cluster_id") if isinstance(result, dict) else getattr(result, "cluster_id", 1)
            template_str = result.get("template_mined") if isinstance(result, dict) else getattr(result, "template_mined", masked)
            template_id = f"T{cluster_id:02d}"
            return template_id, template_str
        except Exception:
            # Fallback regex extraction
            fallback_pattern = RE_NUM.sub("<*>", masked)
            cluster_id = abs(hash(fallback_pattern)) % 1000
            template_id = f"T{cluster_id:02d}"
            return template_id, fallback_pattern


# Global singleton instance
log_miner = LogMiner()
