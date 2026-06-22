"""
Canonical schema for enriched requirements — single source of truth.

Used by: RequirementAgent, ValidationSkill, ProcurementAgent,
         LeadWriterAgent, Jinja2 templates.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ProjectInfo(TypedDict):
    title: str
    organization: str
    reference_code: NotRequired[str]
    description: NotRequired[str]


class ScopeInfo(TypedDict):
    objectives: list[str]
    in_scope: NotRequired[list[str]]
    out_of_scope: NotRequired[list[str]]


class FunctionalReq(TypedDict):
    id: str
    title: str
    description: str
    priority: str  # MUST | SHOULD | COULD


class TechnicalReq(TypedDict):
    id: str
    category: str
    description: str
    constraint: NotRequired[str]


class SLAInfo(TypedDict):
    availability: str
    rto: NotRequired[str]
    rpo: NotRequired[str]
    response_time: NotRequired[str]
    custom_kpis: NotRequired[list[str]]


class SecurityInfo(TypedDict):
    standards: list[str]
    requirements: NotRequired[list[str]]
    data_classification: NotRequired[str]


class TimelineInfo(TypedDict):
    project_start: NotRequired[str]
    go_live: str
    milestones: NotRequired[list[str]]


class EnrichedRequirements(TypedDict):
    """Schema canonico — single source of truth per tutti i componenti."""

    project: ProjectInfo
    scope: ScopeInfo
    functional_requirements: list[FunctionalReq]
    technical_requirements: list[TechnicalReq]
    sla: SLAInfo
    security_compliance: SecurityInfo
    timeline: TimelineInfo
    integrations: NotRequired[list[dict]]
    stakeholders: NotRequired[list[dict]]
    constraints: NotRequired[list[str]]
    regulatory_references: NotRequired[list[dict]]
    evaluation_criteria: NotRequired[list[dict]]
    budget: NotRequired[dict]
