# cli.py
import argparse
import sys
from datetime import datetime, timedelta

from input import ingest
from store import PatternStore
from detector import AnomalyDetector
from context import ContextBuilder
from details import Explainer


class StdoutLLM:
    """
    Placeholder LLM.
    Replace with real client later.
    """

    def complete(self, prompt: str) -> str:
        return """
SUMMARY:
An abnormal log pattern was detected.

WHY IT MATTERS:
The frequency deviates significantly from historical behavior.

WHERE TO LOOK:
- Recent deployments
- Upstream dependencies
- Service configuration

CONFIDENCE:
0.50
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Log-Whisperer – Production Debug Copilot"
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (defaults to stdin)",
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=10,
        help="Total lookback window in minutes",
    )
    parser.add_argument(
        "--recent-minutes",
        type=int,
        default=2,
        help="Recent window for spike detection",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    window = timedelta(minutes=args.window_minutes)
    recent = timedelta(minutes=args.recent_minutes)

    store = PatternStore(
        window_size=window,
        bucket_size=timedelta(minutes=1),
    )

    detector = AnomalyDetector(
        store=store,
        recent_window=recent,
    )

    context_builder = ContextBuilder(store)
    explainer = Explainer(StdoutLLM())

    if args.log_file:
        source = open(args.log_file)
    else:
        source = sys.stdin

    for event in ingest(source):
        store.add(event)

    now = datetime.utcnow()
    anomalies = detector.detect(now)

    if not anomalies:
        print("No anomalies detected.")
        return

    print(f"\nDetected {len(anomalies)} anomalies:\n")

    for idx, anomaly in enumerate(anomalies, 1):
        ctx = context_builder.build(anomaly)
        explanation = explainer.explain(ctx)

        print("=" * 60)
        print(f"Anomaly #{idx}")
        print(f"Service   : {anomaly.service}")
        print(f"Pattern   : {anomaly.template}")
        print(f"Reason    : {anomaly.reason}")
        print(f"Severity  : {anomaly.severity:.2f}")
        print()
        print("Summary:")
        print(explanation.summary)
        print()
        print("Why it matters:")
        print(explanation.why_it_matters)
        print()
        print("Where to look:")
        print(explanation.where_to_look)
        print()
        print(f"Confidence: {explanation.confidence:.2f}")
        print("=" * 60)


if __name__ == "__main__":
    main()

