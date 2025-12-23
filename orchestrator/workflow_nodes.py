"""Workflow node implementations for the graph orchestration."""

import json
from typing import Any, Dict

from orchestrator.agents.perplexity_agent import run_perplexity_agent
from orchestrator.agents.tavily_agent import run_tavily_agent
from orchestrator.config import load_config
from orchestrator.context import WorkflowContext
from orchestrator.report import render_html_report
from orchestrator.schemas import MasterInput, validate_required_keys
from orchestrator.tools.tavily import tavily_extract, tavily_search
from orchestrator.utils import ensure_dir, utc_timestamp


def input_validation_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    payload = json.loads(task) if isinstance(task, str) else task
    validated = MasterInput(**payload)
    context.set("input", validated.model_dump())
    return {"validated_input": validated.model_dump()}


def domain_verification_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    config = load_config()
    validated_input = context.get("input", {})
    target_domain = validated_input.get("target_domain")

    url = target_domain
    if not url.startswith("http"):
        url = f"https://{target_domain}"

    extract_result = tavily_extract(config=config, url=url)

    record = {
        "target_domain": target_domain,
        "domain_accessible": bool(extract_result.get("ok")),
        "official_company_name": validated_input.get("company_name_hint") or "Unknown",
        "business_description": "Unknown",
        "headquarters": "Unknown",
        "industry_preliminary": "Unknown",
        "disambiguation_required": False,
        "similar_companies": [],
        "exclusion_list": [],
        "validation_confidence": "LOW" if not extract_result.get("ok") else "MEDIUM",
        "validation_timestamp": utc_timestamp(),
        "raw_extract": extract_result,
    }

    scope = {
        "company_stage": "Unknown",
        "business_model": "Unknown",
        "industry_focus": "Unknown",
        "research_complexity": "Standard",
        "special_considerations": [],
        "estimated_research_time": "3-4 hours",
    }

    context.set("domain_verification", record)
    context.set("research_scope", scope)
    return {"domain_verification": record, "research_scope": scope}


def perplexity_handoff_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    domain_verification = context.get("domain_verification", {})
    handoff = {
        "agent": "Perplexity Sonar",
        "task": "General Business Intelligence Research",
        "target_domain": domain_verification.get("target_domain"),
        "validated_company_name": domain_verification.get("official_company_name"),
        "disambiguation_context": {
            "disambiguation_required": domain_verification.get("disambiguation_required"),
            "exclusion_list": domain_verification.get("exclusion_list"),
            "similar_companies": domain_verification.get("similar_companies"),
        },
        "research_focus": [
            "Company profile and business model",
            "Market position and competitive analysis",
            "Technology stack and infrastructure",
            "Leadership and organizational structure",
            "Financial indicators and growth signals",
            "Recent developments and strategic initiatives",
        ],
        "constraints": [
            "Domain-first validation required",
            "No AWS case study research (handled by Tavily)",
            "Focus on business intelligence, not technical architecture",
        ],
    }

    result = run_perplexity_agent(handoff)
    context.set("perplexity_report", result)
    return {"perplexity_report": result}


def tavily_handoff_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    domain_verification = context.get("domain_verification", {})
    handoff = {
        "agent": "Tavily",
        "task": "AWS Case Study & Technical Intelligence Research",
        "target_domain": domain_verification.get("target_domain"),
        "validated_company_name": domain_verification.get("official_company_name"),
        "preliminary_industry": domain_verification.get("industry_preliminary"),
        "disambiguation_context": {
            "disambiguation_required": domain_verification.get("disambiguation_required"),
            "exclusion_list": domain_verification.get("exclusion_list"),
        },
        "research_focus": [
            "AWS case studies relevant to industry and business challenges",
            "Industry-specific AWS solutions and adoption patterns",
            "Technical architecture patterns and cloud opportunities",
            "Competitive AWS usage intelligence",
            "Business value mapping and ROI examples",
        ],
        "constraints": [
            "Focus on AWS case studies and cloud solutions",
            "Business outcomes over technical details",
            "No general business intelligence (handled by Perplexity)",
        ],
    }

    result = run_tavily_agent(handoff)
    context.set("tavily_report", result)
    return {"tavily_report": result}


def integration_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    perplexity_report = context.get("perplexity_report", {})
    tavily_report = context.get("tavily_report", {})

    perplexity_validation = validate_required_keys(
        perplexity_report, ["research_metadata", "company_identity", "business_model"]
    )
    tavily_validation = validate_required_keys(
        tavily_report, ["research_metadata", "aws_case_studies", "industry_classification"]
    )

    completeness = {
        "business_intelligence": "Complete" if perplexity_validation.valid else "Partial",
        "aws_case_studies": "Complete" if tavily_validation.valid else "Partial",
        "industry_analysis": "Partial",
        "technical_intelligence": "Partial",
        "overall_confidence": "MEDIUM",
    }

    context.set("completeness", completeness)
    return {
        "perplexity_validation": perplexity_validation.model_dump(),
        "tavily_validation": tavily_validation.model_dump(),
        "completeness": completeness,
    }


def gap_fill_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    config = load_config()
    completeness = context.get("completeness", {})
    notes = []

    if completeness.get("aws_case_studies") != "Complete":
        query = "AWS case study industry trends"
        result = tavily_search(config=config, query=query, max_results=5)
        notes.append({"gap": "aws_case_studies", "supplement": result})

    context.set("gap_fill_notes", notes)
    return {"gap_fill_notes": notes}


def synthesis_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    domain_verification = context.get("domain_verification", {})
    perplexity_report = context.get("perplexity_report", {})
    tavily_report = context.get("tavily_report", {})
    completeness = context.get("completeness", {})

    report_model = {
        "report_metadata": {
            "target_domain": domain_verification.get("target_domain"),
            "validated_company_name": domain_verification.get("official_company_name"),
            "report_date": utc_timestamp().split(" ")[0],
            "overall_confidence": completeness.get("overall_confidence", "MEDIUM"),
            "data_completeness": completeness.get("business_intelligence", "Partial"),
        },
        "domain_verification": domain_verification,
        "perplexity_summary": perplexity_report,
        "tavily_summary": tavily_report,
        "conflict_log": [],
        "report_sections": {
            "executive_summary": "Synthesis pending. Review business intelligence and AWS opportunities.",
            "company_profile": {
                "description": perplexity_report.get("company_identity", {}).get("description", ""),
            },
            "business_challenges_and_aws_opportunities": tavily_report.get("business_challenges", []),
            "aws_case_studies": tavily_report.get("aws_case_studies", []),
            "market_competitive_intelligence": perplexity_report.get("market_intelligence", {}),
            "technology_infrastructure": perplexity_report.get("technology_footprint", {}),
            "leadership": perplexity_report.get("leadership_team", []),
            "recent_developments": perplexity_report.get("recent_developments", []),
            "strategic_recommendations": tavily_report.get("aws_recommendations", []),
            "methodology_confidence": completeness,
            "sources": (perplexity_report.get("sources", []) + tavily_report.get("sources", [])),
        },
    }

    context.set("report_model", report_model)
    return {"report_model": report_model}


def final_validation_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    report_model = context.get("report_model", {})
    confidence = report_model.get("report_metadata", {}).get("overall_confidence", "MEDIUM")
    quality_report = {
        "domain_verified": bool(report_model.get("domain_verification")),
        "has_case_studies": len(report_model.get("report_sections", {}).get("aws_case_studies", [])) >= 3,
        "has_leadership": len(report_model.get("report_sections", {}).get("leadership", [])) >= 1,
        "overall_confidence": confidence,
    }
    context.set("quality_report", quality_report)
    return {"quality_report": quality_report}


def artifact_node(task: Any, context: WorkflowContext) -> Dict[str, Any]:
    config = load_config()
    report_model = context.get("report_model", {})
    quality_report = context.get("quality_report", {})

    ensure_dir(config.report_output_dir)

    company = report_model.get("report_metadata", {}).get("validated_company_name", "report")
    safe_company = company.replace(" ", "_")
    timestamp = utc_timestamp().replace(" ", "_").replace(":", "-")
    html_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.html"
    json_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.json"

    html = render_html_report(report_model)
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html)

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(
            {"report_model": report_model, "quality_report": quality_report},
            handle,
            indent=2,
        )

    return {"html_report": html_path, "json_report": json_path}
