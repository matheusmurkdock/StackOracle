from dataclasses import dataclass
from typing import Optional

from context import AnomalyContext


@dataclass(frozen=True)
class Explanation:
    summary: str
    why_it_matters: str
    where_to_look: str
    confidence: float


class Explainer:
    def __init__(self, llm_client):
        """
        llm_client must expose:
        - complete(prompt: str) -> str
        """
        self.llm = llm_client

    def explain(self, ctx: AnomalyContext) -> Explanation:
        prompt = self._build_prompt(ctx)
        response = self.llm.complete(prompt)

        return self._parse_response(response)

    def _build_prompt(self, ctx: AnomalyContext) -> str:
        a = ctx.anomaly

        return f"""
You are a senior production engineer assisting during an incident.

Facts:
- Service: {a.service}
- Log pattern: "{a.template}"
- Reason flagged: {a.reason}
- Severity score: {a.severity:.2f}
- First seen: {a.first_seen}
- Last seen: {a.last_seen}
- Recent count: {a.recent_count}
- Baseline avg count: {a.baseline_count:.2f}

Context window: {ctx.window_start} to {ctx.window_end}

Log level distribution in window:
{ctx.level_breakdown}

Related patterns in same service:
{ctx.related_patterns}

Instructions:
- Do NOT propose fixes
- Do NOT speculate beyond the facts
- Explain why this anomaly matters
- Suggest which area of the system to investigate
- Be concise and precise

Return the response in this exact format:

SUMMARY:
<one paragraph>

WHY IT MATTERS:
<one paragraph>

WHERE TO LOOK:
<bullet points>

CONFIDENCE:
<number between 0 and 1>
"""

    def _parse_response(self, text: str) -> Explanation:
        """
        Extremely strict parsing.
        If the model deviates, we fail fast.
        """
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
            return Explanation(
                summary=" ".join(sections["SUMMARY"]),
                why_it_matters=" ".join(sections["WHY IT MATTERS"]),
                where_to_look="\n".join(sections["WHERE TO LOOK"]),
                confidence=float(sections["CONFIDENCE"][0]),
            )
        except Exception as e:
            raise ValueError(
                f"LLM response malformed: {text}"
            ) from e

