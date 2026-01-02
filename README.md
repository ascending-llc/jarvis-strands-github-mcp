# AWS Customer Intelligence Orchestrator

Multi-agent research system that coordinates specialized agents to produce comprehensive customer intelligence reports. Built with [Strands Agents SDK](https://strandsagents.com) and exposed through an A2A gateway for agent-to-agent collaboration.

## Overview

**Input:** Company domain + research prompt (e.g., `"Analyze atscale.com for AWS opportunities"`)
**Output:** Professional HTML report + structured JSON data

### Architecture

```
Deep Intel (Unified)
        ↓
   ┌────┴─────┐
   ↓          ↓
AWS Research  Business Intel (A2A Calls)
   ↓          ↓
   └────┬─────┘
        ↓
   HTML Report (Jinja2)
```

### A2A Agents

1. **Deep Intel Agent** - Coordinates A2A calls and synthesizes the final report
2. **AWS Research Agent** - AWS-focused research (case studies, cloud solutions, opportunities)
3. **Business Intel Agent** - Company profile, market position, tech stack, leadership

### Key Features

✅ **A2A Gateway** - Multiple agents registered under distinct endpoints
✅ **Parallel Execution** - AWS Research and Business Intel run simultaneously
✅ **Elegant HTML Reports** - Professional AWS-branded reports via Jinja2 templates
✅ **Token Efficient** - Separates data generation from presentation (30-40% token savings)
✅ **Fully Typed** - Type-safe with Pydantic models and proper error handling
✅ **Production Ready** - Structured logging, config validation, comprehensive error handling
✅ **API + CLI** - FastAPI endpoint and CLI entrypoint for local runs

---

## Quick Start

### Prerequisites

- Python 3.10+
- `uv` package manager (or `pip`)
- API keys: Perplexity, Tavily
- AWS credentials for Bedrock

### Installation

```bash
# Clone the repository
cd jarvis-strands-github-mcp

# Install dependencies
uv sync

# Or with pip
pip install -e .
```

### Configuration

Create `.env` file:

```bash
# Required API Keys
PERPLEXITY_API_KEY=your_perplexity_key
TAVILY_API_KEY=your_tavily_key

# AWS Credentials (for Bedrock)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1

# Optional Settings (with defaults)
MODEL=your_bedrock_inference_profile_arn
PERPLEXITY_MODEL=sonar
REPORT_OUTPUT_DIR=reports
A2A_BASE_URL=http://localhost:8000
MAX_TOKENS=8192
BEDROCK_READ_TIMEOUT=300
BEDROCK_CONNECT_TIMEOUT=30
BEDROCK_MAX_ATTEMPTS=3
ORCHESTRATOR_LOG_LEVEL=INFO
```

### Run Research

```bash
# Using the CLI entry point (recommended)
uv run aws-intel-run "Research AWS opportunities for stripe.com"

# Or with python module syntax
PYTHONPATH=. python -m api.main "Analyze business challenges for example.com"

# Run the API server
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Note: the CLI uses the A2A gateway to call other agents. Ensure the API server is running and `A2A_BASE_URL` points to it.

REST endpoints:
- `POST /research` (alias for deep intel)
- `POST /research/deep-intel`
- `POST /research/aws`
- `POST /research/business`

## A2A Protocol Support

This service implements the A2A HTTP+JSON binding for multiple agents:

- `GET /agents/deep-intel/.well-known/agent-card.json`
- `GET /agents/aws-research/.well-known/agent-card.json`
- `GET /agents/business-intel/.well-known/agent-card.json`

Each agent exposes:

- `POST /v1/message:send`
- `POST /v1/message:stream` (SSE)
- `GET /v1/tasks/{id}`
- `POST /v1/tasks/{id}:cancel`
- `GET /v1/tasks/{id}:subscribe` (SSE)

Set `A2A_BASE_URL` so agents can call each other through the gateway (defaults to `http://localhost:8000`).

---

## Project Structure

```
api/
├── app.py                    # FastAPI app factory + A2A gateway mounting
└── main.py                   # FastAPI app + CLI entrypoint
agents/
├── agent_cards.py             # AgentCard builders
├── clients.py                 # Agent-to-agent client helpers
├── gateway.py                 # A2A FastAPI sub-apps
├── registry.py                # Agent registry + URLs
├── reporting.py               # Report rendering + upload
├── aws_research/              # AWS Research agent
│   ├── executor.py
│   └── research_agent.py
├── business_intel/            # Business Intel agent
│   ├── executor.py
│   └── research_agent.py
├── deep_intel/                # Deep Intel agent
│   └── executor.py
└── shared/                    # Shared helpers
    ├── base_executor.py
    ├── core/                  # Config + logging + exceptions
    ├── prompts/               # Agent system prompts
    ├── templates/             # HTML template
    └── tools/                 # Tavily tool wrappers

reports/                       # Generated HTML reports (auto-created)
logs/                          # Application logs (auto-created)
```

---

## How It Works

### Workflow Overview

The system uses an **A2A gateway** with a Deep Intel agent that calls two
specialized agents in parallel:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  USER INPUT: "Research AWS opportunities for stripe.com"       │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │   DEEP INTEL    │ (Unified)
                   │                 │
                   │ • Calls A2A     │
                   │   agents        │
                   │ • Synthesizes   │
                   │   findings      │
                   └────────┬────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌──────────────────┐       ┌──────────────────┐
    │ AWS RESEARCH     │       │ BUSINESS INTEL   │ (Parallel)
    │                  │       │                  │
    │ • AWS case       │       │ • Company        │
    │   studies        │       │   profile        │
    │ • Industry       │       │ • Market         │
    │   solutions      │       │   position       │
    │ • Cloud          │       │ • Tech stack     │
    │   adoption       │       │ • Leadership     │
    │ • ROI patterns   │       │ • Financials     │
    └────────┬─────────┘       └─────────┬────────┘
             │                           │
             │  Wait for both to complete│
             └─────────────┬─────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  HTML REPORT SAVED  │
                │                     │
                │ reports/Company_    │
                │ Name_2025-12-24_    │
                │ 15-30-00.html       │
                └─────────────────────┘
```

### Data Flow Details

**1. Deep Intel Agent** (Orchestration)
- Interprets the user prompt and sets research direction
- **Output**: Orchestrated requests for A2A agents

**2. Parallel A2A Research**

**AWS Research Agent**:
- Receives the user prompt
- Searches for AWS case studies and cloud opportunities
- **Output**: JSON with AWS opportunities and case studies

**Business Intel Agent**:
- Receives the user prompt
- Researches company profile, market position, and leadership
- **Output**: JSON with business intelligence

**3. Deep Intel Agent** (Synthesis)
- Collects results from A2A agents
- Combines findings, resolves conflicts, and creates recommendations
- **Output**: Structured JSON with synthesized intelligence

**4. Report Generation** (Jinja2 Template)
- JSON is rendered into HTML
- Saved to `reports/` directory with timestamp
- Optional S3 upload when configured



## Configuration Details

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | ✅ | - | Perplexity API key |
| `TAVILY_API_KEY` | ✅ | - | Tavily API key |
| `AWS_ACCESS_KEY_ID` | ✅ | - | AWS access key for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | ✅ | - | AWS secret key |
| `AWS_REGION` | ❌ | us-east-1 | AWS region |
| `MODEL` | ❌ | sonar | Bedrock model ID or inference profile |
| `PERPLEXITY_MODEL` | ❌ | sonar | Perplexity model name |
| `REPORT_OUTPUT_DIR` | ❌ | reports | Output directory for HTML reports |
| `A2A_BASE_URL` | ❌ | http://localhost:8000 | Base URL for A2A agent-to-agent calls |
| `MAX_TOKENS` | ❌ | 8192 | Maximum tokens per agent |
| `ORCHESTRATOR_LOG_LEVEL` | ❌ | INFO | Logging level (DEBUG/INFO/WARNING) |

### Getting API Keys

- **Perplexity**: https://www.perplexity.ai/api
- **Tavily**: https://tavily.com/api
- **AWS Bedrock**: Configure via AWS Console

---

## Output

### HTML Report

Professional AWS-branded report saved to `reports/Company_Name_YYYY-MM-DD_HH-MM-SS.html`

**Sections include:**
- Company Overview
- Business Intelligence Summary
- Business Challenges
- AWS Opportunities (with case studies)
- Industry Insights
- Strategic Recommendations
- Next Steps

### JSON Response

```json
{
  "status": "completed",
  "aws_research": {...},
  "business_intel": {...},
  "final_synthesis": {
    "company_overview": {...},
    "business_intelligence": {...},
    "business_challenges": [...],
    "aws_opportunities": [...],
    "strategic_recommendations": [...],
    "confidence_level": "HIGH",
    "research_completeness": "Complete"
  },
  "html_report_path": "reports/Company_Name_2025-12-24_15-30-00.html",
  "report_url": "https://bucket.s3.us-east-1.amazonaws.com/aws-intel-reports/Company_Name_2025-12-24_15-30-00.html"
}
```

---


## Dependencies

Core dependencies:
- `strands-agents` - Multi-agent orchestration
- `a2a-sdk` - A2A protocol gateway + client
- `fastapi` + `uvicorn` - API server
- `jinja2` - HTML template rendering
- `tavily-python` - Tavily API client
- `httpx` - HTTP client
- `pydantic` - Data validation
- `python-dotenv` - Environment configuration

See [pyproject.toml](pyproject.toml) for complete list.

---

## License

[Add your license here]

---

## Support

For issues or questions:
1. Check logs: `tail -f orchestrator.log`
2. Enable debug mode: `ORCHESTRATOR_LOG_LEVEL=DEBUG`
3. Review agent prompts in `prompts/` directory
4. Verify API keys and AWS credentials in `.env`
