"""Legacy research endpoint router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.clients import send_agent_request
from agents.deep_intel.executor import run_deep_intel
from agents.shared.core.exceptions import AgentError

router = APIRouter()


class ResearchRequest(BaseModel):
    prompt: str


@router.post("/research")
async def research(request: ResearchRequest) -> dict:
    try:
        result = await run_deep_intel(request.prompt)
        report_url = result.get("report_url")
        if not report_url:
            raise HTTPException(status_code=500, detail="Report upload failed")
        return {"report_url": report_url}
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/research/deep-intel")
async def research_deep_intel(request: ResearchRequest) -> dict:
    try:
        result = await run_deep_intel(request.prompt)
        return result
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/research/aws")
async def research_aws(request: ResearchRequest) -> dict:
    try:
        payload = {"user_input": request.prompt}
        result = await send_agent_request("aws_research", payload)
        return result
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/research/business")
async def research_business(request: ResearchRequest) -> dict:
    try:
        payload = {"user_input": request.prompt}
        result = await send_agent_request("business_intel", payload)
        return result
    except AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
