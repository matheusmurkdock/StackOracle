import argparse
from datetime import datetime, timedelta, timezone

from severity import severity_label

from v3.ingest import ingest_line
from store import PatternStoreV2
from detector import AnomalyDetectorV2
from context import ContextBuilderV2, DeployEvent
from details import ExplainerV2
from openrouter import OpenRouterLLM


# ---------------- CLI ----------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Log-Whisperer — Production Debug Copilot"
    )
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--window-minutes", type=int, default=10)
    parser.add_argument("--recent-minutes", type=int, default=2)
    parser.add_argument("--context-minutes", type=int, default=5)
    parser.add_argument("--max-anomalies", type=int, default=5)

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Relax thresholds for small log samples (demo only)",
    )

    return parser.parse_args()


# ---------------- Helpers ----------------

def extract_deploy_events(events):
    deploys = []

    for e in events:
        if e.service == "deploy-service" and "deployment completed" in e.template:
            parts = e.raw.split()
            service = None
            version = None

            for p in parts:
                if p.startswith("service="):
                    service = p.split("=", 1)[1]
                elif p.startswith("version="):
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

def main():
    args = parse_args()

    ingest_stats = {
        "parsed": 0,
        "failed": 0,
        "unrecognized_format": 0,
    }

    all_events = []

    window = timedelta(minutes=args.window_minutes)
    recent = timedelta(minutes=args.recent_minutes)
    context_window = timedelta(minutes=args.context_minutes)

    store = PatternStoreV2(
        window_size=window,
        bucket_size=timedelta(minutes=1),
    )

    # 👇 THIS IS THE KEY LINE
    min_baseline = 0.1 if args.demo else 1.0

    detector = AnomalyDetectorV2(
        store=store,
        recent_window=recent,
        min_baseline=min_baseline,
    )

    context_builder = ContextBuilderV2(
        store=store,
        context_window=context_window,
    )

    explainer = ExplainerV2(OpenRouterLLM())

    # ---- Ingest ----
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

    # ---- Ingest summary ----
    print("\nIngestion summary")
    print(f"  Parsed logs : {ingest_stats['parsed']}")
    print(f"  Failed logs : {ingest_stats['failed']}")

    if ingest_stats["failed"]:
        print("  Failure reasons:")
        print(f"    unrecognized_format: {ingest_stats['unrecognized_format']}")

    # ---- Detect anomalies ----
    now = datetime.now(timezone.utc)
    anomalies, near_misses = detector.detect(now)

    if not anomalies:
        print("\nNo anomalies detected.")

        if near_misses:
            print(
                f"{len(near_misses)} near-miss patterns observed "
                "(activity increase below alert threshold)."
            )
        else:
            print(
                "Not enough historical baseline to determine anomalies."
            )

        if args.demo:
            print(
                "NOTE: Demo mode is ON — try increasing window size "
                "or adding more baseline logs."
            )

        return

    print(f"\nDetected {len(anomalies)} anomalies.")

    # ---- Deploy correlation ----
    deploy_events = extract_deploy_events(all_events)

    # ---- Report ----
    print("\n=== ANOMALY REPORT ===")

    error_services = {
        a.key[0] for a in anomalies if a.key[1] == "ERROR"
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

        sev = severity_label(anomaly.severity)

        print("\n" + "─" * 60)
        print(f"#{idx} {sev}  {svc}  {level}")
        print(f"Pattern : {template}")
        print(f"Reason  : {anomaly.reason}")

        if ctx.deploy_event:
            print(
                f"Deploy  : {ctx.deploy_event.service} "
                f"{ctx.deploy_event.version}"
            )

        print("\nSummary")
        print(explanation.summary)

        print("\nWhy it matters")
        print(explanation.why_it_matters)

        print("\nWhere to look")
        print(explanation.where_to_look)

        print("─" * 60)

    print("\nDone.")


if __name__ == "__main__":
    main()
