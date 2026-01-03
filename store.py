from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone
from typing import Dict, List, Tuple

from v3.ingest import LogEvent


PatternKey = Tuple[str, str, str]  # (service, level, template)


LEVEL_WEIGHTS = {
    "ERROR": 5.0,
    "WARN": 2.0,
    "INFO": 1.0,
    "DEBUG": 0.5,
}


@dataclass
class PatternStats:
    total_count: int
    first_seen: datetime
    last_seen: datetime


class PatternStoreV2:
    def __init__(self, window_size: timedelta, bucket_size: timedelta):
        self.window_size = window_size
        self.bucket_size = bucket_size

        # key -> deque[(bucket_start, count)]
        self._buckets: Dict[PatternKey, deque[Tuple[datetime, int]]] = defaultdict(deque)

        # key -> stats
        self._stats: Dict[PatternKey, PatternStats] = {}

    # ---------- Internal helpers ----------

    def _bucket_start(self, ts: datetime) -> datetime:
        seconds = int(ts.timestamp())
        bucket_seconds = int(self.bucket_size.total_seconds())
        return datetime.fromtimestamp(
            seconds - (seconds % bucket_seconds),
            tz=timezone.utc,
        )

    def _evict_old(self, key: PatternKey, now: datetime):
        cutoff = now - self.window_size
        buckets = self._buckets[key]
        while buckets and buckets[0][0] < cutoff:
            buckets.popleft()

    # ---------- Write API ----------

    def add(self, event: LogEvent):
        key: PatternKey = (event.service, event.level, event.template)
        bucket_ts = self._bucket_start(event.timestamp)

        buckets = self._buckets[key]
        if not buckets or buckets[-1][0] != bucket_ts:
            buckets.append((bucket_ts, 1))
        else:
            ts, count = buckets.pop()
            buckets.append((ts, count + 1))

        self._evict_old(key, event.timestamp)
        self._update_stats(key, event.timestamp)

    def _update_stats(self, key: PatternKey, ts: datetime):
        if key not in self._stats:
            self._stats[key] = PatternStats(
                total_count=1,
                first_seen=ts,
                last_seen=ts,
            )
        else:
            stats = self._stats[key]
            stats.total_count += 1
            stats.last_seen = ts

    # ---------- Read APIs (V2 FIX) ----------

    def get_patterns(self) -> List[PatternKey]:
        return list(self._buckets.keys())

    def get_buckets(self, key: PatternKey) -> List[Tuple[datetime, int]]:
        return list(self._buckets.get(key, []))

    def get_stats(self, key: PatternKey) -> PatternStats:
        return self._stats[key]

    def get_weighted_count(
        self,
        key: PatternKey,
        since: datetime,
    ) -> float:
        """
        Returns weighted count since given timestamp.
        Used by anomaly detector.
        """
        weight = LEVEL_WEIGHTS.get(key[1], 1.0)
        total = 0.0

        for ts, count in self._buckets.get(key, []):
            if ts >= since:
                total += count * weight

        return total

    def get_activity_window(
        self,
        since: datetime,
        until: datetime,
    ) -> Dict[PatternKey, int]:
        """
        Aggregate raw counts for all patterns in a time window.
        Used by context builder.
        """
        activity: Dict[PatternKey, int] = {}

        for key, buckets in self._buckets.items():
            total = 0
            for ts, count in buckets:
                if since <= ts <= until:
                    total += count
            if total > 0:
                activity[key] = total

        return activity
