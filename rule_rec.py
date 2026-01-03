import argparse
import re
from collections import defaultdict
from pathlib import Path

from v3.ingest import ingest_line
from openrouter import OpenRouterLLM


# ---------------- Config ----------------

MIN_FRAGMENTS = 2
SAMPLE_SIZE = 5


# ---------------- Helpers ----------------

def base_shape(template: str) -> str:
    shape = template

    shape = re.sub(r"<[^>]+>", "<VAR>", shape)

    shape = re.sub(r"\b\d+(ms|s|us|ns)\b", "<VAR>", shape)
    shape = re.sub(r"\b\d+\b", "<VAR>", shape)
    
    """
    Replace all normalization tokens with a generic placeholder.
    Used to detect fragmentation.
    """
    return shape


def sample(items, k):
    return items[:k]


def build_prompt(examples):
    lines = "\n".join(
        f"{i+1}. {ex}"
        for i, ex in enumerate(examples)
    )

    return f"""
You are helping improve a log normalization system.

These log messages are semantically the same but currently produce
fragmented templates.

Your task:
- Propose ONE regex-based normalization rule
- The rule MUST operate only on the log MESSAGE, not timestamps, levels, or service names
- Do NOT match the beginning of the line (^)
- Do NOT include timestamps, dates, or service names in the regex
- The goal is to remove variable values, not reinsert them
- The rule must be deterministic
- It must collapse these messages into ONE template
- Do NOT over-normalize
- Return ONLY a Python tuple: (regex, replacement)
- Return in plain text not like this ```python ...```

Log messages:
{lines}

Return format ONLY:
(re.compile(r"..."), "...")
""".strip()



def validate_rule(rule_text: str) -> bool:

    # must look like a regex tuple
    if "re.compile" not in rule_text:
        return False

    # must not anchor to line start
    if "^" in rule_text:
        return False

    # must not reference timestamps or dates
    forbidden = {
        r"\d{4}-\d{2}-\d{2}",
        "ERROR",
        "INFO",
        "WARN",
        "service",
    }
    
    if ".*" in rule_text:
        return False
    return True


# ---------------- Main ----------------

def main():
    parser = argparse.ArgumentParser(
        description="AI-assisted normalization rule recommender"
    )
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # ---- Ingest logs ----
    template_to_raw = defaultdict(list)

    with open(args.log_file) as f:
        for line in f:
            event = ingest_line(line)
            if not event:
                continue
            template_to_raw[event.template].append(event.raw)

    # ---- Detect fragmentation ----
    shape_groups = defaultdict(list)

    for template in template_to_raw:
        shape = base_shape(template)
        shape_groups[shape].append(template)

    fragmented = {
        shape: templates
        for shape, templates in shape_groups.items()
        if len(templates) >= MIN_FRAGMENTS
    }
    print("\nDEBUG: Shape groups")
    for shape, templates in shape_groups.items():
        print(f"{shape} -> {len(templates)} templates")

    if not fragmented:
        print("No fragmented templates detected.")
        return

    print(f"Detected {len(fragmented)} fragmented groups.\n")

    llm = OpenRouterLLM()

    suggestions = []

    for shape, templates in fragmented.items():
        print("=" * 60)
        print("FRAGMENTED SHAPE:")
        print(shape)
        print("\nTEMPLATES:")
        for t in templates:
            print(" ", t)

        # Collect raw examples
        raw_examples = []
        for t in templates:
            raw_examples.extend(template_to_raw[t])

        examples = sample(raw_examples, SAMPLE_SIZE)

        prompt = build_prompt(examples)

        print("\nQUERYING AI...\n")
        response = llm.complete(prompt)

        if not validate_rule(response):
            print("⚠️  Invalid rule suggestion, skipping.")
            continue

        print("SUGGESTED RULE:")
        print(response)

        choice = input("\nAccept this rule? [y/N] ").strip().lower()
        if choice == "y":
            suggestions.append(response)

    # ---- Output ----
    if not suggestions:
        print("\nNo rules accepted.")
        return

    out = Path("suggested_rules.txt")

    if args.dry_run:
        print("\nDry run mode. Suggested rules:")
        for r in suggestions:
            print(r)
        return

    with out.open("a") as f:
        for r in suggestions:
            f.write(r + "\n")

    print(f"\nSaved {len(suggestions)} rules to {out}")


if __name__ == "__main__":
    main()

