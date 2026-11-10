# Incident Copilot — Finish-First Build Roadmap

> **Framing (read this first, repeat it in interviews):**
> This is a **rigorously evaluated demonstration of agent engineering** — not a production incident tool.
> The commercial category is mature (Resolve AI, Cleric, Datadog Bits AI SRE, PagerDuty SRE Agent, incident.io).
> I'm not competing with them. I'm proving I can build, evaluate, secure, and ship an agentic system — with real, honest numbers.
> My moat is **rigor** (evals, distillation, security), not novelty. Ground truth is synthetic by design, and I say so.

**Owner goal:** Learn the skills hands-on + ship a public repo that stands out for an AI/ML engineer.
**Budget:** ₹0 (100% free). **Machine:** 8 GB RAM laptop. **Pace assumption:** 15–20 hrs/week → ~12–13 weeks.
**Golden rule:** *A finished 70%-scope project beats an abandoned 100%-scope one.* Reach the SHIPPABLE checkpoint (M3) before the heavy DevOps phases.

---

## The three non-negotiables (your actual differentiators)
1. **M3 — Eval harness** with a results table + confidence intervals + CI gate. *The #1 hiring signal. Do not cut.*
2. **M6 — LoRA distillation** (120B → 1.5B). *Moves you from "AI/prompt engineer" to "ML engineer." Do not cut.*
3. **M4 — Guardrails + security** (prompt-injection test, read/write separation). *Cheap, high interview value.*

Everything else can be thinned. These cannot.

---

## Resource checklist (all free)

**Accounts:** GitHub (public repo) · Groq · Google AI Studio (Gemini) · OpenRouter · Kaggle (phone-verify for GPU) · Hugging Face · Langfuse Cloud (Hobby) · Slack (free workspace).
**Local tools:** WSL2+Ubuntu · Docker Engine · k3d · kubectl · Helm · uv · Postgres+pgvector · Redis.
**Day-1 security habit:** `.env` in `.gitignore`, commit only `.env.example`. Pin LiteLLM to an exact version (never 1.82.7/1.82.8).
**Verify on day 1:** re-check Groq/Gemini/Kaggle free limits — they change; the whole eval budget depends on them.

---

## Milestones (finish-first order)

### M0 — Foundation  *(~1 week)*  [orig Phase 0]
- **Learn:** uv, pre-commit, WSL2 memory capping, supply-chain hygiene.
- **Build:** Public repo (MIT). `uv` project + ruff/mypy/pytest. `.wslconfig` (memory=5GB, swap=4GB). Folder skeleton. `config.py` (Pydantic Settings). Minimal GitHub Actions (lint+test). **20-line script that calls Groq/Gemini/OpenRouter via LiteLLM with a tool-calling test.**
- **Done:** Green CI badge; all 3 LLM keys verified working.
- **Proves:** clean engineering setup, security awareness.

### M1 — An observable system you can break  *(~2 weeks)*  [orig Phase 1, THINNED]
- **Thin it:** build **3 services first** (frontend, checkout, payment) + loadgen. Add catalog/cart later only if time.
- **Learn:** Docker, k3d, OpenTelemetry, Prometheus/Loki/Jaeger/Grafana, PromQL/LogQL.
- **Build:** `shop/common` (OTel + fault middleware + `/admin/faults`). Services (~150 lines each). docker-compose first, then k3d + Helm with memory limits. Observability stack (small resource settings). Alert rules (`promtool` tested). `faults/inject.py` with ground-truth logging. First **10 scenario YAMLs**.
- **Done:** `make cluster-up` works; `inject payment-errors-01` fires a real alert; live mode fits RAM budget (`docker stats`, `kubectl top`).
- **Proves:** backend + K8s + observability (the "I built the test environment too" story).

### M2 — Tools + first diagnosis  *(~2–2.5 weeks)*  [orig Phases 2+3]
- **Learn:** MCP, LangGraph state graphs, tool use, structured outputs, context engineering.
- **Build:** MCP server (start with ~6 tools: `service_health`, `query_metrics`, `search_logs`, `k8s_events`, `pod_logs`, `detect_anomalies`). **Token-cap every tool output.** **Record/replay fixture layer** (relative time ranges, fixture-miss reporting). Isolation Forest anomaly detector (precision/recall). LangGraph nodes: triage → plan → investigate → hypothesize → report. LiteLLM router with fallback + cache (off during evals).
- **Done:** CLI diagnoses **one** scenario end-to-end in **replay mode**. ← *first demo-able moment.*
- **Proves:** MCP, agent orchestration, classical-ML fundamentals.

### M3 — MEASURED  ⭐ **SHIPPABLE CHECKPOINT** *(~1.5 weeks)*  [orig Phase 4]
- **Learn:** eval design, Wilson confidence intervals, pass^k, LLM-judge calibration.
- **Build:** full **30 scenarios** (10 easy / 10 medium / 5 hard / 5 red-herring). `run_eval.py` (k runs, resume, scoring, CI table). Record all fixtures. Baseline v0. **CI smoke gate** (5 scenarios, fail on regression or any unsafe action). Calibrated LLM judge.
- **Done:** `make eval` → results table with **"X% top-3 (Wilson lo–hi)"**. CI blocks regressions.
- **⭐ START APPLYING TO JOBS HERE.** You now have the #1 differentiator.
- **Proves:** THE signal — data-driven engineering, regression testing, statistical honesty.

### M4 — Safe  *(~1 week)*  [orig Phase 5]
- **Learn:** OWASP LLM Top 10, prompt-injection defense, human-in-the-loop.
- **Build:** read-only RBAC for agent; separate executor (narrow write perms, approval-record required). Action allowlist + risk levels. Secret/PII scrubbing. **Slack approval (Socket Mode, no public URL).** Security tests: prompt-injection (malicious log line), permission, approval-bypass. OWASP mapping table in docs.
- **Done:** security tests pass; approval flow works; threat model documented.
- **Proves:** AI security + production safety thinking.

### M5 — Memory / RAG  *(~0.5 week)*  [orig Phase 6]
- **Learn:** embeddings, pgvector, hybrid retrieval.
- **Build:** 10–15 runbooks → fastembed (CPU, ONNX, no PyTorch) → pgvector. Past-incident summaries. Hybrid retrieval into the plan node. **Memory on/off eval comparison** (include a *misleading* past incident to show the agent still verifies live).
- **Done:** on/off comparison in eval results.
- **Proves:** RAG done with evaluation, not just vibes.

### M6 — ML depth  ⭐ **DIFFERENTIATOR** *(~2 weeks)*  [orig Phase 8 A+B]
- **Learn:** vLLM serving, AWQ quantization, LoRA/PEFT/TRL, distillation, data leakage.
- **Build (A):** Kaggle T4 notebook → vLLM serves Qwen2.5-7B-Instruct-AWQ → run replay eval against it. **Model comparison table** (gpt-oss-120b/20b, Gemini, Qwen-vLLM, hybrid) + estimated paid-cost column.
- **Build (B):** export (alert→triage) and (tool-output→summary) pairs from gpt-oss-120b traces (500–2,000). **Split by scenario, not example** (avoid leakage). Dataset card. LoRA-train Qwen2.5-1.5B on Kaggle (checkpoint often). Evaluate vs. base + gpt-oss-20b. Serve adapter with vLLM. **Publish adapter + dataset on Hugging Face.**
- **Done:** comparison table + published adapter + "what didn't work" write-up.
- **Proves:** the ML-engineer signal — serving, fine-tuning, cost/quality reasoning.

### M7 — Productionize  *(~2 weeks, LATE ON PURPOSE)*  [orig Phases 7+9]
- **Learn:** FastAPI service, Celery/Redis, multi-stage Docker, Helm, GitHub Actions CD, SBOM.
- **Build:** API (`/alerts`, `/slack/interactions`, `/incidents`). Alembic DB schema. Celery workers (concurrency 1, DLQ, idempotent). Multi-stage Dockerfiles → GHCR + SBOM (Syft). Full Helm chart. `live-eval.yml` on GitHub runner. Langfuse tracing on every run. One Grafana copilot dashboard.
- **Done:** one-command Helm deploy; full CI/CD; trace + dashboard screenshots.
- **Proves:** MLOps/LLMOps, DevOps. *Lowest AI/ML signal-per-hour → that's why it's last.*

### M8 — Launch  *(~1 week)*  [orig Phase 10]
- **Build:** README (results table + badges up top, "Built for ₹0" section, **Known Limitations** — draft below). Excalidraw architecture diagram. 3-min OBS demo video. Hashnode blog ("What broke when I built an on-call AI agent for ₹0"). Update resume + LinkedIn.
- **Done:** repo pinned; video embedded; blog shared.
- **Bonus high-value add:** one merged PR to Langfuse / vLLM / LangGraph / Promptfoo — cited as a strong hiring signal.

---

## Draft: README "Known Limitations" section (own the gaps — this reads as senior)

```markdown
## Known limitations (honest by design)
- **Synthetic ground truth.** Faults are injected, so the correct root cause is known at eval time.
  Real production RCA is harder: unknown faults, noisy/incomplete signals, interacting failures.
  The reported accuracy measures the controlled case and does not claim real-world parity.
- **Toy topology.** 3–5 services on a single k3d cluster — not a service-mesh / multi-region estate.
- **No alert-correlation/noise-reduction layer** (the core value of commercial AIOps) — out of scope.
- **Free-model ceiling.** Hardest scenarios are bounded by free-tier model quality; numbers reported honestly.
- **Not a product.** This is an engineering + evaluation demonstration, not a Resolve AI / Cleric competitor.
```

---

## Timeline at a glance

| Weeks | Milestone | Checkpoint |
|---|---|---|
| 1 | M0 Foundation | Green CI, keys verified |
| 2–3 | M1 Observable system | Real alert from injected fault |
| 4–6 | M2 Tools + first diagnosis | One scenario diagnosed (replay) |
| 6–7 | **M3 MEASURED** | ⭐ Results table → **start applying** |
| 8 | M4 Safe | Security tests pass |
| 8–9 | M5 Memory | on/off comparison |
| 9–11 | **M6 ML depth** | ⭐ Published adapter + comparison |
| 11–12 | M7 Productionize | One-command deploy |
| 13 | M8 Launch | Repo + video + blog |

*Pace flexes with your weekly hours and K8s comfort. If K8s is new, add 3–4 days of fundamentals before M1.*

---

## Guardrails against the two ways this fails
1. **Quitting at 60%** (the common death) → M3 is a complete, shippable project on its own. Hit it first.
2. **Being undifferentiated** (another generic agent demo) → the three non-negotiables are the only moat. Never skip them to save time; skip M5/M7 scope instead.
```
