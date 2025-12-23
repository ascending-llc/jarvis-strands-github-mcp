# AWS Customer Intelligence Orchestrator (Strands)

This project implements a multi-agent workflow/graph orchestration using the Strands Agents SDK. It coordinates a master orchestrator, a Perplexity Sonar business intelligence agent, and a Tavily AWS-focused research agent to produce a structured report and HTML artifact.

## Structure

- `orchestrator/` core workflow code
- `prompts/` agent instruction prompts (master, Tavily, Perplexity)
- `reports/` generated HTML + JSON artifacts
- `examples/` sample inputs

## Workflow

Graph orchestration:

1. Input validation
2. Domain verification (Tavily extract)
3. Parallel handoff (Perplexity + Tavily)
4. Integration + validation
5. Gap fill (conditional)
6. Synthesis
7. Final validation
8. Artifact generation

## Running (local with uv)

```bash
uv sync
uv run aws-intel-run examples/input.json
```

## Configuration

Set env vars for API keys and endpoints:

- `TAVILY_API_KEY`
- `PERPLEXITY_API_KEY`
- `TAVILY_BASE_URL`, `TAVILY_SEARCH_PATH`, `TAVILY_EXTRACT_PATH`
- `PERPLEXITY_BASE_URL`, `PERPLEXITY_CHAT_PATH`, `PERPLEXITY_MODEL`
- `REPORT_OUTPUT_DIR`

Endpoints are placeholders by default and should be updated once confirmed.
