from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class PersistenceRecord:
    timestamp: float
    event: str
    payload: Dict[str, Any]


class PersistentLogger:
    """Writes telemetry records to a JSON Lines file for later analysis."""

    def __init__(self, path: str = "logs/scalper_metrics.jsonl") -> None:
        self._path = path
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def write(self, event: str, payload: Dict[str, Any]) -> None:
        record = PersistenceRecord(timestamp=time.time(), event=event, payload=payload)
        try:
            with open(self._path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record)) + "\n")
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to persist telemetry %s: %s", event, exc)
