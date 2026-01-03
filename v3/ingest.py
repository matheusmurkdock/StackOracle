from typing import Optional

from .detect import detect_format, LogFormat
from .parsers import (
    parse_json,
    parse_timestamped,
    parse_kv,
)
from .normalize import normalize
from .types import LogEvent


def ingest_line(line: str) -> Optional[LogEvent]:
    """
    Ingest a single raw log line and convert it into a LogEvent.

    Pipeline:
      raw line
        → format detection
          → format-specific parser
            → message normalization
              → LogEvent

    This function must:
      - never throw
      - return None on failure
      - be deterministic
    """
    try:
        fmt = detect_format(line)

        parsed = None
        if fmt == LogFormat.JSON:
            parsed = parse_json(line)
        elif fmt == LogFormat.TIMESTAMP_TEXT:
            parsed = parse_timestamped(line)
        elif fmt == LogFormat.KEY_VALUE:
            parsed = parse_kv(line)
        else:
            return None

        if not parsed:
            return None

        template = normalize(parsed.message)

        return LogEvent(
            timestamp=parsed.timestamp,
            service=parsed.service,
            level=parsed.level,
            template=template,
            raw=line,
        )

    except Exception:
        # Ingestion must never crash the system
        return None
