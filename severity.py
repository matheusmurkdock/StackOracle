from enum import Enum


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def severity_label(score: float) -> Severity:
    if score >= 20:
        return Severity.CRITICAL
    if score >= 10:
        return Severity.HIGH
    if score >= 5:
        return Severity.MEDIUM
    return Severity.LOW
