from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

from store import PatternStore


@dataclass(frozen=True)
class Anomaly:
    service: str
    template: str
    reason: str
    severity: float
    first_seen: datetime
    last_seen: datetime
    recent_count: int
    baseline_count: float


class AnomalyDetector:
    def __init__(
        self,
        store: PatternStore,
        recent_window: timedelta,
        spike_threshold: float = 5.0,
        min_baseline: int = 5,
    ):
        """
        spike_threshold: multiplier over baseline to flag anomaly
        min_baseline: minimum historical count before trusting baseline
        """
        self.store = store
        self.recent_window = recent_window
        self.spike_threshold = spike_threshold
        self.min_baseline = min_baseline

    def detect(self, now: datetime) -> List[Anomaly]:
        anomalies: List[Anomaly] = []

        for (service, template), buckets in self.store._buckets.items():
            if not buckets:
                continue

            recent, baseline = self._split_counts(buckets, now)

            if self._is_spike(recent, baseline):
                stats = self.store.get_stats(service, template)
                anomalies.append(
                    Anomaly(
                        service=service,
                        template=template,
                        reason="spike",
                        severity=recent / max(baseline, 1),
                        first_seen=stats.first_seen,
                        last_seen=stats.last_seen,
                        recent_count=recent,
                        baseline_count=baseline,
                    )
                )

            elif self._is_new_pattern(baseline):
                stats = self.store.get_stats(service, template)
                anomalies.append(
                    Anomaly(
                        service=service,
                        template=template,
                        reason="new_pattern",
                        severity=10.0,
                        first_seen=stats.first_seen,
                        last_seen=stats.last_seen,
                        recent_count=recent,
                        baseline_count=baseline,
                    )
                )

        return sorted(anomalies, key=lambda a: a.severity, reverse=True)

    def _split_counts(
        self,
        buckets: List[Tuple[datetime, int]],
        now: datetime,
    ) -> Tuple[int, float]:
        recent_cutoff = now - self.recent_window

        recent_count = 0
        baseline_count = 0
        baseline_buckets = 0

        for ts, count in buckets:
            if ts >= recent_cutoff:
                recent_count += count
            else:
                baseline_count += count
                baseline_buckets += 1

        baseline_avg = (
            baseline_count / baseline_buckets
            if baseline_buckets > 0
            else 0.0
        )

        return recent_count, baseline_avg

    def _is_spike(self, recent: int, baseline: float) -> bool:
        if baseline < self.min_baseline:
            return False
        return recent >= baseline * self.spike_threshold

    def _is_new_pattern(self, baseline: float) -> bool:
        return baseline == 0.0

