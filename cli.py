import argparse
import sys
from datetime import datetime, timedelta
from datetime import timezone

from v3.ingest import ingest_line
from store import PatternStoreV2
from detector import AnomalyDetectorV2
from context import ContextBuilderV2, DeployEvent
from details import ExplainerV2
from openrouter import OpenRouterLLM


# ---------------- CLI ----------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Log-Whisperer V2 — Production Debug Copilot"
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
        help="Recent window for anomaly detection",
    )
    parser.add_argument(
        "--context-minutes",
        type=int,
        default=5,
        help="Context window for correlation",
    )
    parser.add_argument(
        "--max-anomalies",
        type=int,
        default=5,
        help="Max anomalies to explain (LLM budget guard)",
    )
    return parser.parse_args()


# ---------------- Helpers ----------------

def extract_deploy_events(events):
    """
    VERY simple heuristic:
    looks for logs like:
    deploy-service deployment completed service=X version=Y
    """
    deploys = []

    for e in events:
        if (
            e.service == "deploy-service"
            and "deployment completed" in e.template
        ):
            # extremely naive parsing, intentional for hackathon
            parts = e.raw.split()
            service = None
            version = None
            for p in parts:
                if p.startswith("service="):
                    service = p.split("=", 1)[1]
                if p.startswith("version="):
                    version = p.split("=", 1)[1]

            if service and version:
                deploys.append(
                    DeployEvent(
                        service=service,
                        version=version,
                        timestamp=e.timestamp,
                    )
                )

    return deploys


# ---------------- Main ----------------
ingest_stats = {
    "parsed": 0,
    "failed": 0,
    "unrecognized_format": 0,
}

all_events = []


def main():
    args = parse_args()

    # ---- Windows ----
    window = timedelta(minutes=args.window_minutes)
    recent = timedelta(minutes=args.recent_minutes)
    context_window = timedelta(minutes=args.context_minutes)

    # ---- Core components ----
    

    store = PatternStoreV2(
        window_size=window,
        bucket_size=timedelta(minutes=1),
    )

    detector = AnomalyDetectorV2(
        store=store,
        recent_window=recent,
        min_baseline=1.0,
    )

    context_builder = ContextBuilderV2(
        store=store,
        context_window=context_window,
    )

    explainer = ExplainerV2(OpenRouterLLM())

    # ---- Input ----
    with open(args.log_file) as f:
        for line in f:
            event = ingest_line(line)
            if not event:
                ingest_stats["failed"] += 1
                ingest_stats["unrecognized_format"] += 1
                continue
            
            ingest_stats["parsed"] += 1
            all_events.append(event)
            store.add(event)

    # ---- Ingest metrics ----
    print("\nIngestion summary:")
    print(f"  Parsed logs : {ingest_stats['parsed']}")
    print(f"  Failed logs : {ingest_stats['failed']}")
    if ingest_stats["failed"]:
        print("  Failure reasons:")
        print(
            f"  unrecognized_format: "
            f"{ingest_stats['unrecognized_format']}"
        )

    # ---- Detect anomalies ----
    now = datetime.now(timezone.utc)
    anomalies, near_misses = detector.detect(now)

    if not anomalies:
        print("\nNo anomalies detected.")
        return

    print(f"\nDetected {len(anomalies)} anomalies.")
    if near_misses:
        print(f"Near misses: {len(near_misses)} (not alerted)")

    # ---- Deploy correlation ----
    deploy_events = extract_deploy_events(all_events)

    # ---- Explain anomalies (budget guarded) ----
    print("\n=== ANOMALY REPORT ===")

    error_services = {
        anomaly.key[0]
        for anomaly in anomalies
        if anomaly.key[1] == "ERROR"
    }
    
    for idx, anomaly in enumerate(anomalies[: args.max_anomalies], 1):
        
        svc, level, template = anomaly.key

        if level == "WARN" and svc in error_services:
            continue
        
        ctx = context_builder.build(
            anomaly,
            deploy_events=deploy_events,
        )


        try:
            explanation = explainer.explain(ctx)
        except Exception as e:
            print("\n[LLM ERROR]")
            print(str(e))
            continue



        print("\n" + "=" * 70)
        print(f"Anomaly #{idx}")
        print(f"Service   : {svc}")
        print(f"Level     : {level}")
        print(f"Pattern   : {template}")
        print(f"Reason    : {anomaly.reason}")
        print(f"Severity  : {anomaly.severity:.2f}")

        if ctx.deploy_event:
            print(
                f"Deploy    : {ctx.deploy_event.service} "
                f"{ctx.deploy_event.version}"
            )

        print("\nSummary:")
        print(explanation.summary)

        print("\nWhy it matters:")
        print(explanation.why_it_matters)

        print("\nWhere to look:")
        print(explanation.where_to_look)

        print(f"\nConfidence: {explanation.confidence:.2f}")
        print("=" * 70)

    print("\nDone.")


if __name__ == "__main__":
    main()
