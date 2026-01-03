import json
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Dict, Iterable, Optional, Tuple


# ---------- Data Models ----------

@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    level: str
    service: str
    template: str
    variables: Dict[str, str]
    raw: str
    request_id: Optional[str]


@dataclass
class ParseFailure:
    raw: str
    reason: str


# ---------- Metrics ----------

class IngestMetrics:
    def __init__(self):
        self.parsed = 0
        self.failed = 0
        self.failures_by_reason: Dict[str, int] = {}

    def record_success(self):
        self.parsed += 1

    def record_failure(self, reason: str):
        self.failed += 1
        self.failures_by_reason[reason] = (
            self.failures_by_reason.get(reason, 0) + 1
        )


# ---------- Regex (text logs) ----------

TEXT_LOG_PATTERN = re.compile(
    r"""
    ^(?P<timestamp>\S+)\s+
    (?P<level>DEBUG|INFO|WARN|ERROR)\s+
    (?P<service>[\w\-]+)\s+
    (?P<message>.+)$
    """,
    re.VERBOSE,
)

NUMBER_PATTERN = re.compile(r"\b\d+\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)


# ---------- Normalization ----------
TIMEOUT_PATTERN = re.compile(r"timeout after \d+ms")
SLOW_RESPONSE_PATTERN = re.compile(r"slow response time=\d+ms")

def normalize_message(message: str) -> Tuple[str, Dict[str, str]]:
    message = TIMEOUT_PATTERN.sub("timeout after <TIMEOUT>ms", message)
    message = SLOW_RESPONSE_PATTERN.sub(
        "slow response time=<LATENCY>ms", message
    )
    variables: Dict[str, str] = {}

    def repl_uuid(match):
        key = f"uuid_{len(variables)}"
        variables[key] = match.group(0)
        return "<UUID>"

    def repl_num(match):
        key = f"num_{len(variables)}"
        variables[key] = match.group(0)
        return "<NUM>"

    message = UUID_PATTERN.sub(repl_uuid, message)
    message = NUMBER_PATTERN.sub(repl_num, message)

    return message, variables


# ---------- Parsers ----------

def parse_text_log(line: str) -> Optional[LogEvent]:
    match = TEXT_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    try:
        timestamp = datetime.fromisoformat(match.group("timestamp")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    template, variables = normalize_message(match.group("message"))

    return LogEvent(
        timestamp=timestamp,
        level=match.group("level"),
        service=match.group("service"),
        template=template,
        variables=variables,
        raw=line.strip(),
        request_id=None,
    )


def parse_json_log(line: str) -> Optional[LogEvent]:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None

    required = {"timestamp", "level", "service", "message"}
    if not required.issubset(data):
        return None

    try:
        timestamp = datetime.fromisoformat(match.group("timestamp")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    template, variables = normalize_message(data["message"])

    return LogEvent(
        timestamp=timestamp,
        level=data["level"],
        service=data["service"],
        template=template,
        variables=variables,
        raw=line.strip(),
        request_id=data.get("request_id"),
    )


# ---------- Ingest Pipeline ----------

class LogIngestor:
    def __init__(self):
        self.metrics = IngestMetrics()

    def ingest(self, lines: Iterable[str]) -> Iterable[LogEvent]:
        for line in lines:
            event = self._parse_line(line)
            if event:
                self.metrics.record_success()
                yield event
            else:
                self.metrics.record_failure("unrecognized_format")

    def _parse_line(self, line: str) -> Optional[LogEvent]:
        # Order matters: JSON first, then text
        return (
            parse_json_log(line)
            or parse_text_log(line)
        )
