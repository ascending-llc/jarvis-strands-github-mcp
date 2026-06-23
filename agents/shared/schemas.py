"""Typed contracts for agent inputs and outputs.

These Pydantic models replace the giant JSON-schema-as-prose blocks that used to
live in the agent system prompts. Workers produce these via Strands structured
output and serialize them across A2A as JSON; the orchestrator validates them
back into these models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- AWS Research worker output ------------------------------------------------


class CaseStudy(BaseModel):
    company: str = Field(description="Company featured in the AWS case study")
    industry: str | None = Field(default=None, description="Industry of the featured company")
    challenge: str | None = Field(default=None, description="Business challenge addressed")
    aws_services: list[str] = Field(default_factory=list, description="AWS services used")
    business_outcome: str | None = Field(
        default=None, description="Quantified outcome (cost, revenue, scale, efficiency)"
    )
    url: str | None = Field(default=None, description="Source URL for the case study")
    relevance: str | None = Field(default=None, description="Why this is relevant to the target")


class AwsOpportunity(BaseModel):
    title: str = Field(description="Short name of the opportunity")
    description: str = Field(description="What the opportunity is")
    aws_services: list[str] = Field(default_factory=list)
    potential_impact: str | None = Field(default=None, description="Expected business impact")
    priority: str | None = Field(default=None, description="High | Medium | Low")


class AwsFindings(BaseModel):
    """Output contract for the AWS Research worker."""

    industry: str | None = Field(default=None, description="Target company's industry vertical")
    business_challenges: list[str] = Field(default_factory=list)
    case_studies: list[CaseStudy] = Field(default_factory=list)
    opportunities: list[AwsOpportunity] = Field(default_factory=list)
    adoption_insights: list[str] = Field(
        default_factory=list, description="Industry AWS adoption trends and patterns"
    )
    confidence: str = Field(default="MEDIUM", description="HIGH | MEDIUM | LOW")
    sources: list[str] = Field(default_factory=list, description="Source URLs used")


# --- Business Intel worker output ----------------------------------------------


class CompanyIdentity(BaseModel):
    official_name: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    description: str | None = Field(default=None)
    headquarters: str | None = Field(default=None)
    founded_year: str | None = Field(default=None)


class CompanyProfile(BaseModel):
    """Output contract for the Business Intel worker."""

    identity: CompanyIdentity = Field(default_factory=CompanyIdentity)
    industry_vertical: str | None = Field(default=None)
    business_model: str | None = Field(default=None)
    employee_count: str | None = Field(default=None)
    funding_summary: str | None = Field(default=None)
    market_position: str | None = Field(default=None)
    competitors: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    cloud_provider: str | None = Field(default=None, description="AWS | Azure | GCP | Unknown")
    leadership: list[str] = Field(default_factory=list, description="Key decision makers, name + title")
    recent_developments: list[str] = Field(default_factory=list)
    potential_challenges: list[str] = Field(default_factory=list)
    confidence: str = Field(default="MEDIUM", description="HIGH | MEDIUM | LOW")
    sources: list[str] = Field(default_factory=list)


# --- Worker request envelope ---------------------------------------------------


class ResearchRequest(BaseModel):
    """What the orchestrator sends to a worker over A2A."""

    user_input: str = Field(description="Original user prompt")
    company: str | None = Field(default=None, description="Resolved official company name, if known")
    domain: str | None = Field(default=None, description="Target domain, if known")
