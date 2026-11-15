"""Record/replay: capture tool outputs live, then replay them with the cluster off.

Same interface for both, so the agent cannot tell live from replay. Replay is
deterministic, free (no LLM-independent cluster calls) and RAM-light — it's how
most agent iteration and all CI evals run.
"""
