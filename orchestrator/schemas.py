"""Shared data models and validation helpers."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MasterInput(BaseModel):
    target_domain: str = Field(..., min_length=3)
    company_name_hint: Optional[str] = None
    research_priority: str = "standard"
    special_focus: Optional[List[str]] = None
    time_limit: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    missing_keys: List[str] = []
    errors: List[str] = []


def validate_required_keys(payload: Dict[str, Any], required_keys: List[str]) -> ValidationResult:
    missing = [key for key in required_keys if key not in payload]
    return ValidationResult(valid=len(missing) == 0, missing_keys=missing)
