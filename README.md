# StackOracle  
---
[![StackOracle Demo](https://img.youtube.com/vi/ljWG0yz72O0/0.jpg)](https://www.youtube.com/watch?v=ljWG0yz72O0)
---
**An AI Production Debug Copilot**

> We don’t fix bugs.  
> We tell you **why an error matters** and **where to look**.

---

## Problem

Modern production systems generate **massive volumes of logs**.

- Errors are buried in noise
- Alerts fire without context
- On-call engineers waste time correlating symptoms manually
- Existing tools tell you *what happened*, not *why it matters*

Logs are data-rich but insight-poor.

---

## What StackOracle Does

StackOracle is a **CLI-first debugging copilot** that:

1. Ingests raw logs
2. Normalizes noisy patterns
3. Detects **behavioral anomalies** using deterministic logic
4. Correlates anomalies with recent deploys
5. Uses AI **only to explain**:
   - why this anomaly matters
   - where an engineer should look

No dashboards.  
No magic alerts.  
Just signal.

---

## Key Design Principles

- **Deterministic detection**  
  Anomalies are detected using explicit heuristics, not ML guessing.

- **AI for explanation, not detection**  
  AI never decides *what* is anomalous — only *how to explain it*.

- **Human-readable output**  
  Severity labels and signal strength replace raw numbers.

- **CLI-first**  
  Designed for engineers, terminals, and incident response.

---

## How It Works (High Level)

1. **Ingestion**
   - Logs are parsed into structured events
   - High-cardinality values (IDs, UUIDs, latencies) are normalized

2. **Pattern Store**
   - Events are bucketed over time
   - Patterns maintain rolling baseline and recent activity

3. **Anomaly Detection**
   - Compares recent behavior vs historical baseline
   - Flags:
     - new patterns
     - spikes
     - sustained increases

4. **Correlation**
   - Detects deploy events
   - Associates anomalies with nearby deployments

5. **Explanation**
   - AI generates:
     - summary
     - why it matters
     - where to look
   - No fixes suggested — only direction

---
### Architecture
```java
log_ingest_v3/        ← ingestion layer (V3)
  ├── detect.py
  ├── parsers.py
  ├── normalize.py
  └── ingest.py

core/                 ← analysis engine (stable)
  ├── store.py
  ├── detector.py
  ├── context.py
  └── details.py

cli.py                ← orchestration / policy
```
### Severity (human-readable)
- `CRITICAL` — immediate attention required
- `HIGH` — significant issue
- `MEDIUM` — noticeable degradation
- `LOW` — informational / suppressed

This avoids misleading “confidence scores” and reflects real observability practice.
---

## Usage

### Basic Run
```bash
python3 cli.py --log-file demo.log
```
## Example Output
```bash
#1 CRITICAL  user-service  ERROR
Pattern : timeout after <DURATION> user_id=<USER_ID>
Reason  : spike
Deploy  : user-service 1.4.2

Summary
• Timeouts spiked immediately after deployment

Why it matters
• User requests are failing under load

Where to look
• Request handling path
• Recent changes in user-service 1.4.2
```

## Project Status
This project was built as a hackathon prototype with production-grade design intent.
### Future Work (post-hackathon)
- More log formats
- Rule packs
- CI / incident integrations
