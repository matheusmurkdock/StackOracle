from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from store import PatternStoreV2, PatternKey


@dataclass(frozen=True)
class AnomalyV2:
    key: PatternKey
    reason: str  # spike | new_pattern
    severity: float
    recent_weighted: float
    baseline_weighted: float
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True)
class NearMiss:
    key: PatternKey
    recent_weighted: float
    baseline_weighted: float
    threshold: float


class AnomalyDetectorV2:
    def __init__(
        self,
        store: PatternStoreV2,
        recent_window: timedelta,
        spike_multiplier: float = 5.0,
        min_baseline: float = 5.0,
        track_near_miss: bool = True,
    ):
        self.store = store
        self.recent_window = recent_window
        self.spike_multiplier = spike_multiplier
        self.min_baseline = min_baseline
        self.track_near_miss = track_near_miss

    def detect(
        self,
        now: datetime,
    ) -> tuple[List[AnomalyV2], List[NearMiss]]:
        anomalies: List[AnomalyV2] = []
        near_misses: List[NearMiss] = []

        recent_cutoff = now - self.recent_window

        for key in self.store.get_patterns():
            buckets = self.store.get_buckets(key)
            if not buckets:
                continue

            recent = self.store.get_weighted_count(key, recent_cutoff)

            # baseline = everything before recent window
            baseline_total = 0.0
            baseline_buckets = 0

            for ts, count in buckets:
                if ts < recent_cutoff:
                    baseline_total += count
                    baseline_buckets += 1

            baseline_avg = (
                baseline_total / baseline_buckets
                if baseline_buckets > 0
                else 0.0
            )

            stats = self.store.get_stats(key)

            # ---- New pattern ----
            if baseline_avg == 0.0 and recent > 0:
                anomalies.append(
                    AnomalyV2(
                        key=key,
                        reason="new_pattern",
                        severity=recent,
                        recent_weighted=recent,
                        baseline_weighted=0.0,
                        first_seen=stats.first_seen,
                        last_seen=stats.last_seen,
                    )
                )
                continue

            # ---- Spike detection ----
            if baseline_avg >= self.min_baseline:
                threshold = baseline_avg * self.spike_multiplier
                if recent >= threshold:
                    anomalies.append(
                        AnomalyV2(
                            key=key,
                            reason="spike",
                            severity=recent / baseline_avg,
                            recent_weighted=recent,
                            baseline_weighted=baseline_avg,
                            first_seen=stats.first_seen,
                            last_seen=stats.last_seen,
                        )
                    )
                elif self.track_near_miss and recent >= threshold * 0.7:
                    near_misses.append(
                        NearMiss(
                            key=key,
                            recent_weighted=recent,
                            baseline_weighted=baseline_avg,
                            threshold=threshold,
                        )
                    )

        anomalies.sort(key=lambda a: a.severity, reverse=True)
        return anomalies, near_misses
