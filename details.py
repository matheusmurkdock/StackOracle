from dataclasses import dataclass
from typing import Protocol

from context import AnomalyContextV2


# ---------- Output Model ----------

@dataclass(frozen=True)
class ExplanationV2:
    summary: str
    why_it_matters: str
    where_to_look: str
    confidence: float


# ---------- LLM Interface ----------

class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


# ---------- Explainer ----------

class ExplainerV2:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def explain(self, ctx: AnomalyContextV2) -> ExplanationV2:
        prompt = self._build_prompt(ctx)
        raw = self.llm.complete(prompt)
        return self._parse_response(raw)

    # ---------- Prompt ----------

    def _build_prompt(self, ctx: AnomalyContextV2) -> str:
        a = ctx.anomaly
        svc, level, template = a.key

        deploy_info = (
            f"Yes – version {ctx.deploy_event.version} at {ctx.deploy_event.timestamp}"
            if ctx.deploy_event
            else "No deploy detected in this window"
        )

        return f"""
You are a senior production engineer assisting during an active incident.

You MUST follow the rules exactly.

Facts:
- Service: {svc}
- Log level: {level}
- Pattern: "{template}"
- Reason flagged: {a.reason}
- Severity score: {a.severity:.2f}
- First seen: {a.first_seen}
- Last seen: {a.last_seen}
- Recent weighted count: {a.recent_weighted}
- Baseline weighted avg: {a.baseline_weighted}

Context window:
- From: {ctx.window_start}
- To: {ctx.window_end}

Level breakdown in window:
{ctx.level_breakdown}

Related patterns (same service):
{ctx.related_patterns}

Deploy correlation:
{deploy_info}

Rules:
- Do NOT mention security issues unless explicitly stated in the logs
- Do NOT use words like "breach", "attack", or "unauthorized"
- Do NOT propose fixes
- Do NOT speculate beyond the facts
- Do NOT claim causation
- Explain impact and investigation direction only

Return output in EXACTLY this format:

SUMMARY:
<1 short paragraph>

WHY IT MATTERS:
<1 short paragraph>

WHERE TO LOOK:
- <bullet>
- <bullet>

CONFIDENCE:
<number between 0 and 1>
"""

    # ---------- Parsing ----------

    def _parse_response(self, text: str) -> ExplanationV2:
        sections = {}
        current = None

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.endswith(":"):
                current = line[:-1]
                sections[current] = []
            elif current:
                sections[current].append(line)

        try:
            confidence = float(sections["CONFIDENCE"][0])
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence out of range")

            return ExplanationV2(
                summary=" ".join(sections["SUMMARY"]),
                why_it_matters=" ".join(sections["WHY IT MATTERS"]),
                where_to_look="\n".join(sections["WHERE TO LOOK"]),
                confidence=confidence,
            )
        except Exception as e:
            raise ValueError(
                f"Malformed LLM response:\n{text}"
            ) from e
