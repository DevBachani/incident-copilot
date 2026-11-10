# Incident Copilot

> An on-call triage agent for Kubernetes — a **rigorously evaluated** agentic AI project.
> It receives an alert, investigates on its own (metrics, logs, traces, K8s events) through a
> custom MCP tool server, ranks root-cause hypotheses with evidence, and proposes a fix that
> runs only after a human approves.

[![CI](https://github.com/DevBachani/incident-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/DevBachani/incident-copilot/actions/workflows/ci.yml)

**This is an engineering + evaluation demonstration, not a production incident tool.** The
commercial category is mature (Resolve AI, Cleric, Datadog Bits AI SRE, PagerDuty SRE Agent).
The goal here is to prove agent engineering done well — with real, honest numbers — not to
compete with those products. Ground truth is synthetic by design (faults are injected), and the
reported accuracy measures that controlled case. See the roadmap for the full plan.

Built for ₹0 on an 8 GB laptop. See [ROADMAP.md](ROADMAP.md).

## Status
🚧 Early build — Milestone M0 (foundation).

## Quick start (dev)
```bash
uv sync                           # install deps into .venv
cp .env.example .env              # then paste your free API keys
uv run python scripts/verify_llm.py   # confirm all providers + tool calling work
uv run pytest                     # run tests
```

## License
MIT
