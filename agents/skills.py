"""Skill definitions for A2A agent cards."""

from __future__ import annotations

from a2a.types import AgentSkill


def deep_intel_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="deep_intel_report",
            name="Deep Intel Report",
            description="Run AWS research and business intelligence, then synthesize a full report.",
            tags=["research", "orchestration", "aws", "intelligence"],
            examples=["Analyze atscale.com for AWS opportunities"],
        )
    ]


def aws_research_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="aws_research",
            name="AWS Research",
            description="Search for AWS opportunities, case studies, and cloud adoption signals.",
            tags=["aws", "research", "case-study"],
            examples=["Find AWS case studies for fintech companies"],
        )
    ]


def business_intel_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="business_intel",
            name="Business Intelligence",
            description="Profile a company, its market position, and competitive landscape.",
            tags=["business", "market", "competitive"],
            examples=["Summarize company profile for atscale.com"],
        )
    ]
