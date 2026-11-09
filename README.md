# J.A.R.V.I.S. — Autonomous Incident Intelligence
### Justified Analysis, Reasoning & Visualization of Incident Systems

🏆 **NITSHACKS 9.0 Official Hackathon Submission**  
👥 **Team Name**: `uppu`  
👨‍💻 **Team Members**: Kaustab Karmakar, Rajat Sharma  
🌐 **Live Cloud Command Center**: [https://frontend-three-alpha-90.vercel.app](https://frontend-three-alpha-90.vercel.app)  
📊 **Interactive Slide Deck**: [https://frontend-three-alpha-90.vercel.app/deck.html](https://frontend-three-alpha-90.vercel.app/deck.html)  
📄 **Official Submission PDF**: [`NITSHACKS_9_UPPU_JARVIS.pdf`](./NITSHACKS_9_UPPU_JARVIS.pdf)  

> *"Other tools tell you what is red. J.A.R.V.I.S. tells you why, shows the evidence, proves it by replaying the failure with the cause fixed, and admits when it is unsure."*

---

## 1. Executive Summary & Winning Thesis

When production goes down, on-call engineers face an overwhelming blizzard of cascading alarms. Most observability tools stop at grouping alerts into noisy buckets and asking an ungrounded LLM to guess the cause.

**J.A.R.V.I.S.** is built on four core pillars:
1. **Causal, Not Just Temporal**: Root cause is mathematically derived from the intersection of onset timing, dependency topology reachability, and node-level resource/change evidence.
2. **Counterfactual Proof**: J.A.R.V.I.S. validates its hypothesis by testing the counterfactual: click **Verify Fix**, heal the suspected service in the simulator, and observe downstream cascade alerts clear in real time.
3. **Honest Confidence & Calibrated Ambiguity**: When symptoms are split or evidence is inconclusive, J.A.R.V.I.S. rejects false certainty. It outputs an explicit **`Ambiguous`** state alongside the lowest-cost diagnostic query to disambiguate.
4. **Live Chaos Demo**: No pre-baked videos. Judges can pick any fault from the Chaos Panel or click **Surprise Me** for an unscripted live test.
5. **Zero LLM in the Causal Loop**: The LLM *never* diagnoses root cause. A deterministic 6-feature Python scoring engine produces the verdict and evidence IDs. The LLM acts solely as a natural-language interface strictly bound to cite verified event IDs.

---

## 2. Complete System Architecture

```
[Sources]                             [Pipeline]                               [Experience]
Simulator (6 svcs) ──┐
Log File Upload ─────┼──► Ingest API ──► Normalizer ──► Event Store ──► Detector 
Webhook / REST ──────┤    (FastAPI)      (Unified       (SQLite)        (Anomaly
                     │                    Schema)                        Scoring)
                     │
                     └──► Correlator ──► Root Cause Engine ──► Impact Analysis
                          (Clustering)   (6 Features +          (User Journeys +
                                          Ambiguity)             Revenue at Risk)
                                               │
WebSocket Push ◄── Counterfactual Proof ◄──────┘
               ◄── Playbook Recommendations
               │
React HUD Command Center:
  - Top HUD: Live Noise Counter (47 Alerts → 1 Incident in 1.8s)
  - Center: Interactive Canvas/SVG Dependency Topology Graph
  - Bottom: Scrubbable Incident Time Machine (T0 → Propagation → Resolution)
  - Right: Ranked Root Causes (#1, #2, #3) with Traceable Evidence Bullets
  - Drawers: Live Chaos Injection Panel, 20-Scenario Accuracy Scoreboard, Grounded AI War Room
```

---

## 3. Quickstart & Installation

### Requirements:
- Python 3.11+
- Modern Web Browser (Chrome / Edge / Firefox)

### Run with a single command:
```bash
python run_jarvis.py
```

Open your browser to:
- **Interactive HUD Command Center**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live Real-Time WebSockets**: `ws://localhost:8000/ws/live`

### Run Automated Test Suite:
```bash
python -m tests.run_tests
```
Verifies all 9 core subsystems: Schema Normalization, Drain3 Mining, SQLite Event Store, Topology Reachability, Debounced Anomaly Detection, Scenario 1 DB Cascade, Scenario 6 Incident Splitting, Scenario 17 Honest Ambiguity, War Room Citations, and the 20-Scenario Accuracy Benchmark.

---

## 4. Complete 20 Failure Scenarios Catalog

| # | Scenario Name | Injected Failure Dynamics | Expected Ground Truth & Behavior |
|---|---|---|---|
| **1** | **DB failure cascade** | `user-db` pool hits 100%, auth latency spikes, logins fail, payment verification fails | Blame `user-db`; 1 incident; show cascade through auth |
| **2** | **Third-party outage** | External `payment-gateway` responds with HTTP 503 | Blame external dependency; recommend provider failover |
| **3** | **Bad deploy** | Deploy event in `payment-api` followed immediately by 500 error spike | Identify code deployment as root cause; recommend rollback |
| **4** | **Slow burn memory leak** | Monotonic RAM climb on `auth-service` leading to OOM restarts | Detect early via EWMA; identify leaking service; estimate time-to-crash |
| **5** | **Retry storm amplification** | Downstream slow response triggers unthrottled retries from `web-gateway` | Recognize feedback loop; point to initial slowness; suggest circuit breaker |
| **6** | **Two independent incidents** | `redis-cache` corruption + unrelated `payment-gateway` failure simultaneously | Keep strictly as **2 separate incidents**; do not merge |
| **7** | **Red herring** | Unrelated noisy logging service throws loud errors 3s before real DB failure | Reject noisy service; correctly blame DB based on topology & downstream reach |
| **8** | **Traffic surge (not a fault)** | 5x traffic increase across all endpoints; no internal component broken | Classify as **traffic capacity surge**; recommend auto-scaling, no culprit service |
| **9** | **Network partition / latency** | Cross-node latency injects bidirectional timeouts between Node-1 and Node-2 | Identify host link partition; handle bidirectional error symptoms |
| **10** | **Config change error** | Bad environment variable change in `auth-service` causes auth failures | Detect config change event; cite config diff as root cause |
| **11** | **Certificate / Credential expiry**| Sudden 100% authorization failure on single internal edge | Step-change detection; classify as credential/cert expiration |
| **12** | **Cache stampede** | Redis cache flush causes massive sudden read wave on `orders-db` | Chain recognition: Identify Cache as **Trigger** and DB as **Bottleneck** |
| **13** | **Disk full** | Host disk hits 100% capacity on database node; write transactions abort | Prioritize disk resource saturation evidence |
| **14** | **Flapping service** | `payment-api` crashing and restarting every 15 seconds | Debounce algorithm holds single persistent flapping incident |
| **15** | **Silent failure** | Service ceases emitting logs/heartbeats without generating error lines | Heartbeat absence anomaly detector triggers silent death alert |
| **16** | **Partial / sparse data** | Only raw logs provided without metrics or trace IDs | Graceful degradation: flag inferred topology, lower confidence |
| **17** | **Ambiguous evidence** | Equal symptom evidence pointing to both `orders-db` and `payment-gateway` | Output **`Ambiguous`** state + cheapest disambiguation check |
| **18** | **False alarm** | 1-second transient metric spike that immediately self-resolves | Suppress incident creation or auto-close as transient noise |
| **19** | **Recovery** | Service fix applied; latencies and error rates return to normal | Auto-resolve incident, log Mean Time To Recover (MTTR) |
| **20** | **Recurrence** | Identical failure re-occurs 10 minutes post-recovery | Link to historical incident; flag as recurrent regression |

---

## 5. Judge Demonstration Script (6-Minute Walkthrough)

1. **Minute 0:00–0:45 (The Hook & Noise Reduction)**:
   - Start with raw alerts streaming. Show the noise counter.
   - Click **[Correlate (47 → 1)]**. The counter collapses: *"47 Alerts → 1 Unified Incident in 1.8s"*.
2. **Minute 0:45–1:45 (Explainable Root Cause)**:
   - Dependency graph highlights `user-db` pulsing crimson with blast radius shaded yellow.
   - Root Cause panel shows `user-db (91% confidence)` with exact evidence bullets citing timestamps and pool saturation.
3. **Minute 1:45–2:30 (Scrubbable Time Machine)**:
   - Drag the time scrubber from T0 to Now.
   - Graph animates the cascade propagating from `user-db` to `auth-service` to `web-gateway`.
4. **Minute 2:30–3:30 (Counterfactual Proof)**:
   - Click **[Verify Fix]**. The simulator heals `user-db`.
   - Live telemetry shows downstream error rates dropping to zero across all services with 100% cascade recovery verified.
5. **Minute 3:30–4:30 (Live Chaos Injection)**:
   - Hand control to a judge: *"Pick any failure on the Chaos Panel or click Surprise Me."*
   - Judge clicks **Bad Deploy** or **Stripe 503 Outage**. J.A.R.V.I.S. diagnoses it in under 2 seconds.
6. **Minute 4:30–5:15 (Grounded AI War Room)**:
   - Click suggested question: *"Why didn't you blame the payment gateway?"*
   - AI answers with clickable citation chips `[EVT-xxx]` referencing exact telemetry.
7. **Minute 5:15–5:45 (Honest Uncertainty)**:
   - Inject Scenario #17 (Ambiguous Evidence).
   - J.A.R.V.I.S. displays: **`Status: Ambiguous (52% vs 48%)`** and prompts the lowest-cost diagnostic check.
8. **Minute 5:45–6:00 (Post-Mortem & Scoreboard)**:
   - Click **[Report]** to show Executive vs Engineering 1-click post-mortem.
   - Open **Accuracy Scoreboard** showing benchmark accuracy across all 20 scenarios.
