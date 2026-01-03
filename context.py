from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone
from typing import Dict, List, Tuple, Optional

from detector import AnomalyV2
from store import PatternStoreV2, PatternKey


@dataclass(frozen=True)
class DeployEvent:
    service: str
    version: str
    timestamp: datetime


@dataclass(frozen=True)
class AnomalyContextV2:
    anomaly: AnomalyV2
    window_start: datetime
    window_end: datetime

    related_patterns: Dict[PatternKey, int]
    level_breakdown: Dict[str, int]

    deploy_event: Optional[DeployEvent]
    request_ids: List[str]


class ContextBuilderV2:
    def __init__(
        self,
        store: PatternStoreV2,
        context_window: timedelta = timedelta(minutes=5),
    ):
        self.store = store
        self.context_window = context_window

    def build(
        self,
        anomaly: AnomalyV2,
        deploy_events: List[DeployEvent] | None = None,
    ) -> AnomalyContextV2:
        window_end = anomaly.last_seen
        window_start = window_end - self.context_window

        # ---- Aggregate activity in window ----
        activity = self.store.get_activity_window(
            since=window_start,
            until=window_end,
        )

        # ---- Related patterns (same service, different template) ----
        related: Dict[PatternKey, int] = {}
        for key, count in activity.items():
            if key[0] == anomaly.key[0] and key != anomaly.key:
                related[key] = count

        # ---- Level breakdown ----
        level_breakdown: Dict[str, int] = {}
        for (svc, level, _), count in activity.items():
            level_breakdown[level] = level_breakdown.get(level, 0) + count

        # ---- Deploy correlation ----
        deploy_event = self._find_deploy(
            anomaly,
            deploy_events or [],
            window_start,
            window_end,
        )

        # ---- Request IDs (best-effort, placeholder) ----
        # NOTE: real request correlation comes later
        request_ids: List[str] = []

        return AnomalyContextV2(
            anomaly=anomaly,
            window_start=window_start,
            window_end=window_end,
            related_patterns=related,
            level_breakdown=level_breakdown,
            deploy_event=deploy_event,
            request_ids=request_ids,
        )

    def _find_deploy(
        self,
        anomaly: AnomalyV2,
        deploy_events: List[DeployEvent],
        start: datetime,
        end: datetime,
    ) -> Optional[DeployEvent]:
        for d in deploy_events:
            if (
                d.service == anomaly.key[0]
                and start <= d.timestamp <= end
            ):
                return d
        return None
