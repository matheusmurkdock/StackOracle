from datetime import datetime, timedelta

from input import LogEvent
from store import PatternStoreV2
from detector import AnomalyDetectorV2
from context import ContextBuilderV2, DeployEvent

store = PatternStoreV2(
    window_size=timedelta(minutes=10),
    bucket_size=timedelta(minutes=1),
)

now = datetime.now(timezone.utc)

# baseline
for _ in range(5):
    store.add(
        LogEvent(
            timestamp=now - timedelta(minutes=5),
            level="ERROR",
            service="user-service",
            template="timeout after <NUM>ms",
            variables={},
            raw="",
            request_id=None,
        )
    )

# spike
for _ in range(25):
    store.add(
        LogEvent(
            timestamp=now,
            level="ERROR",
            service="user-service",
            template="timeout after <NUM>ms",
            variables={},
            raw="",
            request_id=None,
        )
    )
detector = AnomalyDetectorV2(
    store=store,
    recent_window=timedelta(minutes=1),
)

anomalies, _ = detector.detect(now)
assert anomalies, "Expected at least one anomaly"
builder = ContextBuilderV2(store)

deploys = [
    DeployEvent(
        service="user-service",
        version="1.4.2",
        timestamp=now - timedelta(minutes=2),
    )
]

ctx = builder.build(anomalies[0], deploy_events=deploys)
print(ctx)

