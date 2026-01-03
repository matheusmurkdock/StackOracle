from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParsedLog:
    """
    Intermediate representation produced by format-specific parsers.

    This is intentionally minimal:
    - no normalization
    - no assumptions about semantics
    - best-effort extraction only
    """
    timestamp: datetime
    service: str
    level: str
    message: str


@dataclass(frozen=True)
class LogEvent:
    """
    Canonical log event consumed by the rest of the system.

    This is the ONLY structure downstream components rely on.
    """
    timestamp: datetime
    service: str
    level: str
    template: str
    raw: str

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParsedLog:
    """
    Intermediate representation produced by format-specific parsers.

    This is intentionally minimal:
    - no normalization
    - no assumptions about semantics
    - best-effort extraction only
    """
    timestamp: datetime
    service: str
    level: str
    message: str


@dataclass(frozen=True)
class LogEvent:
    """
    Canonical log event consumed by the rest of the system.

    This is the ONLY structure downstream components rely on.
    """
    timestamp: datetime
    service: str
    level: str
    template: str
    raw: str
