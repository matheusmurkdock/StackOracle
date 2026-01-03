from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from detector import Anomaly
from store import PatternStore


@dataclass(frozen=True)
class AnomalyContext:
    anomaly: Anomaly
    level_breakdown: Dict[str, int]
    related_patterns: List[Tuple[str, str]]
    window_start: datetime
    window_end: datetime


class ContextBuilder:
    def __init__(
        self,
        store: PatternStore,
        context_window: timedelta = timedelta(minutes=5),
        max_related: int = 5,
    ):
        self.store = store
        self.context_window = context_window
        self.max_related = max_related

    def build(self, anomaly: Anomaly) -> AnomalyContext:
        window_start = anomaly.last_seen - self.context_window
        window_end = anomaly.last_seen

        level_counts: Dict[str, int] = {}
        related: List[Tuple[str, str]] = []

        for (service, template), buckets in self.store._buckets.items():
            for ts, count in buckets:
                if window_start <= ts <= window_end:
                    # Level inference via template key (temporary, honest hack)
                    key_level = self._infer_level(template)
                    level_counts[key_level] = (
                        level_counts.get(key_level, 0) + count
                    )

                    if service == anomaly.service and template != anomaly.template:
                        related.append((service, template))

        related = related[: self.max_related]

        return AnomalyContext(
            anomaly=anomaly,
            level_breakdown=level_counts,
            related_patterns=related,
            window_start=window_start,
            window_end=window_end,
        )

    def _infer_level(self, template: str) -> str:
        """
        Temporary heuristic.
        Will be replaced once level becomes part of the key.
        """
        if "ERROR" in template:
            return "ERROR"
        if "WARN" in template:
            return "WARN"
        return "INFO"

