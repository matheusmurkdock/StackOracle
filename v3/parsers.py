import json
import re
from datetime import datetime, timezone
from typing import Optional

from .types import ParsedLog


# -----------------------------
# JSON LOG PARSER
# -----------------------------

def parse_json(line: str) -> Optional[ParsedLog]:
    """
    Parse JSON logs.

    Expected (flexible) keys:
      - timestamp / time / ts
      - service / svc / app
      - level / severity
      - msg / message

    Missing fields fall back to 'unknown'.
    """
    try:
        data = json.loads(line)

        ts = (
            data.get("timestamp")
            or data.get("time")
            or data.get("ts")
        )
        if not ts:
            return None

        timestamp = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)

        service = (
            data.get("service")
            or data.get("svc")
            or data.get("app")
            or "unknown"
        )

        level = (
            data.get("level")
            or data.get("severity")
            or "UNKNOWN"
        ).upper()

        message = (
            data.get("msg")
            or data.get("message")
            or ""
        )

        return ParsedLog(
            timestamp=timestamp,
            service=service,
            level=level,
            message=message,
        )

    except Exception:
        return None


# -----------------------------
# TIMESTAMPED TEXT PARSER
# -----------------------------

TIMESTAMP_TEXT_RE = re.compile(
    r"""
    ^
    (?P<ts>\d{4}-\d{2}-\d{2}T[^\s]+)   # ISO timestamp
    \s+
    (?P<level>[A-Z]+)
    \s+
    (?P<service>[a-zA-Z0-9\-_]+)
    \s+
    (?P<msg>.+)
    $
    """,
    re.VERBOSE,
)


def parse_timestamped(line: str) -> Optional[ParsedLog]:
    """
    Parse logs like:
      2026-01-03T14:00:01 ERROR user-service timeout after 5000ms
    """
    m = TIMESTAMP_TEXT_RE.match(line.strip())
    if not m:
        return None

    try:
        timestamp = datetime.fromisoformat(m.group("ts")).replace(
            tzinfo=timezone.utc
        )

        return ParsedLog(
            timestamp=timestamp,
            service=m.group("service"),
            level=m.group("level").upper(),
            message=m.group("msg"),
        )

    except Exception:
        return None


# -----------------------------
# KEY=VALUE (LOGFMT-ISH) PARSER
# -----------------------------

KV_PAIR_RE = re.compile(r'(\w+)=(".*?"|\S+)')


def parse_kv(line: str) -> Optional[ParsedLog]:
    """
    Parse logs like:
      level=ERROR service=user-service msg="timeout after 5000ms"
    """
    try:
        fields = {
            k: v.strip('"')
            for k, v in KV_PAIR_RE.findall(line)
        }

        ts = (
            fields.get("timestamp")
            or fields.get("time")
            or fields.get("ts")
        )
        if not ts:
            return None

        timestamp = datetime.fromisoformat(ts).replace(
            tzinfo=timezone.utc
        )

        service = (
            fields.get("service")
            or fields.get("svc")
            or fields.get("app")
            or "unknown"
        )

        level = (
            fields.get("level")
            or fields.get("severity")
            or "UNKNOWN"
        ).upper()

        message = (
            fields.get("msg")
            or fields.get("message")
            or ""
        )

        return ParsedLog(
            timestamp=timestamp,
            service=service,
            level=level,
            message=message,
        )

    except Exception:
        return None
