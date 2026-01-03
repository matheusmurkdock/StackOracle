import re
from typing import List, Tuple


# Ordered normalization rules.
# Order matters: more specific patterns must come first.
NORMALIZATION_RULES: List[Tuple[re.Pattern, str]] = [
    # UUIDs (canonical)
    (
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
        "<UUID>",
    ),

    # IPv4 addresses
    (
        re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
        "<IP>",
    ),

    # Durations like 5000ms, 120ms
    (
        re.compile(r"\b\d+ms\b"),
        "<TIMEOUT>ms",
    ),

    # Floating point numbers
    (
        re.compile(r"\b\d+\.\d+\b"),
        "<FLOAT>",
    ),

    # Plain integers (IDs, counts, etc.)
    (
        re.compile(r"\b\d+\b"),
        "<NUM>",
    ),

    #Python with IDs
    (
        re.compile(r"/(users|orders|payments|sessions)/\d+"),
        r"/\1/<ID>",
    ),

    #HTTP status code
    (
        re.compile(r"\b[1-5]\d{2}\b"),
        "<HTTP_STATUS>",
    ),

    #Methods
    (
        re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\b"),
        "<HTTP_METHOD>",
    ),


    #SQL ERROR Codes
    (
        re.compile(r"\bSQL error code \d+\b", re.IGNORECASE),
        "SQL error code <SQL_CODE>",
    ),

    #Query Durations
    (
        re.compile(r"violates constraint \".+?\"", re.IGNORECASE),
        "query took <DURATION>ms",
    ),

    #Postgres violates
    (
        re.compile(r"violates constraint \".+?\"", re.IGNORECASE),
        'violates constraint "<CONSTRAINT>"',
    ),

    # TIMEOUTS and Latency
    (
        re.compile(r"timeout after \d+ms", re.IGNORECASE),
        "timeout after <DURATION>ms",
    ),

    (
        re.compile(r"slow response time=\d+ms", re.IGNORECASE),
        "slow response time=<DURATION>ms",
    ),

    # AUTHS adn Security

    #USER_ID
    (
        re.compile(r"user_id=\d+", re.IGNORECASE),
        "user_id=<USER_ID>",
    ),

    #AUTH faliure
    (
        re.compile(r"(invalid|expired) token", re.IGNORECASE),
        "<AUTH_ERROR>",
    ),

    #Messaging / queues

    #kaffka offset
    (
        re.compile(r"offset \d+", re.IGNORECASE),
        "offset <OFFSET>",
    ),

    #Partition ID's
    (
        re.compile(r"partition \d+", re.IGNORECASE),
        "partition <PARTITION>",
    ),

    #JVM/ python runtime errors

    #java
    (
        re.compile(r"java\.lang\.[A-Za-z]+Exception"),
        "java.lang.<EXCEPTION>",
    ),

    #python trace IDs
    (
        re.compile(r"Traceback \(most recent call last\):"),
        "<PYTHON_TRACEBACK>",
    ),

    #Devlopment / Infra Signals
    (
        re.compile(r"version=\d+\.\d+\.\d+"),
         "version=<VERSION>",
    ),
    
    (
        re.compile(r"pod-[a-z0-9\-]+"),
        "pod-<POD_ID>",
    ),
]


def normalize(message: str) -> str:
    """
    Normalize a log message into a stable template.

    This function must be:
    - deterministic
    - order-dependent
    - side-effect free

    It should NEVER throw.
    """
    if not message:
        return ""

    normalized = message

    for pattern, token in NORMALIZATION_RULES:
        normalized = pattern.sub(token, normalized)

    return normalized
