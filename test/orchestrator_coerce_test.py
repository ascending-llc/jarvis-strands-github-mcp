"""Tests for the worker -> orchestrator typed contract (JSON over A2A)."""

from __future__ import annotations

from agents.deep_intel.orchestrator import _coerce
from agents.shared.schemas import AwsFindings, CompanyProfile


def test_coerce_valid_json() -> None:
    profile = CompanyProfile(industry_vertical="FinTech")
    text = profile.model_dump_json()
    result = _coerce(text, CompanyProfile)
    assert isinstance(result, CompanyProfile)
    assert result.industry_vertical == "FinTech"


def test_coerce_strips_code_fences() -> None:
    findings = AwsFindings(confidence="HIGH")
    fenced = f"```json\n{findings.model_dump_json()}\n```"
    result = _coerce(fenced, AwsFindings)
    assert isinstance(result, AwsFindings)
    assert result.confidence == "HIGH"


def test_coerce_malformed_falls_back_to_empty_model() -> None:
    result = _coerce("not json at all", AwsFindings)
    assert isinstance(result, AwsFindings)
    assert result.case_studies == []
