from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Tuple

from input import LogEvent


@dataclass
class PatternStats:
    total_count: int
    first_seen: datetime
    last_seen: datetime


class PatternStore:
    def __init__(self, window_size: timedelta, bucket_size: timedelta):
        """
        window_size: total lookback duration (e.g. 10 minutes)
        bucket_size: granularity (e.g. 1 minute)
        """
        self.window_size = window_size
        self.bucket_size = bucket_size

        # (service, template) -> deque[(bucket_start, count)]
        self._buckets: Dict[
            Tuple[str, str],
            deque[Tuple[datetime, int]]
        ] = defaultdict(deque)

        # (service, template) -> PatternStats
        self._stats: Dict[Tuple[str, str], PatternStats] = {}

    def _bucket_start(self, ts: datetime) -> datetime:
        seconds = int(ts.timestamp())
        bucket_seconds = int(self.bucket_size.total_seconds())
        return datetime.fromtimestamp(
            seconds - (seconds % bucket_seconds)
        )

    def add(self, event: LogEvent) -> None:
        key = (event.service, event.template)
        now_bucket = self._bucket_start(event.timestamp)

        buckets = self._buckets[key]

        if not buckets or buckets[-1][0] != now_bucket:
            buckets.append((now_bucket, 1))
        else:
            ts, count = buckets.pop()
            buckets.append((ts, count + 1))

        self._evict_old_buckets(key, event.timestamp)
        self._update_stats(key, event.timestamp)

    def _evict_old_buckets(self, key, now: datetime) -> None:
        cutoff = now - self.window_size
        buckets = self._buckets[key]

        while buckets and buckets[0][0] < cutoff:
            buckets.popleft()

    def _update_stats(self, key, ts: datetime) -> None:
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

    def get_buckets(self, service: str, template: str):
        return list(self._buckets.get((service, template), []))

    def get_stats(self, service: str, template: str):
        return self._stats.get((service, template))

