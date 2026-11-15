"""Structured agent output — validated so malformed reports are caught, not passed on."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "application_error",
    "resource_exhaustion",
    "bad_deploy",
    "config_error",
    "dependency_failure",
    "network",
    "capacity",
    "no_incident",
    "unknown",
]
Risk = Literal["low", "medium", "high"]


class Hypothesis(BaseModel):
    rank: int
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    root_cause_service: str
    root_cause_category: Category


class IncidentReport(BaseModel):
    summary: str
    root_cause_service: str
    root_cause_category: Category
    hypotheses: list[Hypothesis]
    recommended_action: str
    action_risk: Risk
    confidence: float = Field(ge=0.0, le=1.0)
