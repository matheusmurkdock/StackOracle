import re
from dataclasses import dataclass
from typing import Dict, Optional, Iterable
from datetime import datetime


LOG_PATTERN = re.compile(
    r"""
    ^(?P<timestamp>\S+)\s+
    (?P<level>DEBUG|INFO|WARN|ERROR)\s+
    (?P<message>[\w\-]+)\s+
    (?P<service>.+)$
    """,
    re.VERBOSE,
)

NUMBER_PATTERN = re.compile(r"\b\d+\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    level: str
    service: str
    template: str
    variables: Dict[str, str]
    raw: str


def _normalize_message(message: str) -> tuple[str, Dict[str, str]]:
    """
    Replace variable components with placeholders.
    Returns (template, extracted_variables)
    """
    variables = {}

    def _replace_uuid(match):
        key = f"uuid_{len(variables)}"
        variables[key] = match.group(0)
        return "<UUID>"

    def _replace_number(match):
        key = f"num_{len(variables)}"
        variables[key] = match.group(0)
        return "<NUM>"

    message = UUID_PATTERN.sub(_replace_uuid, message)
    message = NUMBER_PATTERN.sub(_replace_number, message)

    return message, variables


def parse_log_line(line: str) -> Optional[LogEvent]:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    ts_raw = match.group("timestamp")
    try:
        timestamp = datetime.fromisoformat(ts_raw)
    except ValueError:
        return None

    message = match.group("message")
    template, variables = _normalize_message(message)

    return LogEvent(
        timestamp=timestamp,
        level=match.group("level"),
        service=match.group("service"),
        template=template,
        variables=variables,
        raw=line.strip(),
    )


def ingest(lines: Iterable[str]) -> Iterable[LogEvent]:
    for line in lines:
        event = parse_log_line(line)
        if event:
            yield event


if __name__ == "__main__":
    import sys

    for evt in ingest(sys.stdin):
        print(evt)

