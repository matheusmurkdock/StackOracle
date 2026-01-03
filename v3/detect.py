import re
from enum import Enum, auto


class LogFormat(Enum):
    """
    High-level log shapes.

    This is about structure, not meaning.
    """
    JSON = auto()
    TIMESTAMP_TEXT = auto()
    KEY_VALUE = auto()
    UNKNOWN = auto()


# Fast, cheap structural checks
ISO_TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T")


def detect_format(line: str) -> LogFormat:
    """
    Detect the structural format of a log line.

    This function must be:
    - deterministic
    - cheap (O(1))
    - conservative (UNKNOWN is fine)

    It should NEVER throw.
    """
    if not line:
        return LogFormat.UNKNOWN

    s = line.strip()
    if not s:
        return LogFormat.UNKNOWN

    # JSON logs (common in modern systems)
    if s.startswith("{") and s.endswith("}"):
        return LogFormat.JSON

    # ISO-8601 timestamp prefixed logs
    if ISO_TIMESTAMP_PREFIX.match(s):
        return LogFormat.TIMESTAMP_TEXT

    # key=value style logs (logfmt-ish)
    # example: level=ERROR service=user msg="timeout"
    if "=" in s and " " in s:
        return LogFormat.KEY_VALUE

    return LogFormat.UNKNOWN
