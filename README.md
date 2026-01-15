# AWS Customer Intelligence Orchestrator

Multi-agent research system that coordinates specialized agents to produce comprehensive customer intelligence reports. Built with [Strands Agents SDK](https://strandsagents.com) and exposed as standalone A2A services.

## Overview

**Input:** Company domain + research prompt (e.g., `"Analyze atscale.com for AWS opportunities"`)
**Output:** HTML report

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
   HTML Report (LLM)
```

### A2A Agents

1. **Deep Intel Agent** - Coordinates A2A calls and synthesizes the final report
2. **AWS Research Agent** - AWS-focused research (case studies, cloud solutions, opportunities)
3. **Business Intel Agent** - Company profile, market position, tech stack, leadership

### Key Features

✅ **Standalone A2A Services** - One container per agent with A2A endpoints
✅ **Parallel Execution** - AWS Research and Business Intel run simultaneously
✅ **HTML Reports** - LLM-generated HTML report saved locally (and optionally to S3)
✅ **Fully Typed** - Type-safe with Pydantic models and proper error handling
✅ **Production Ready** - Structured logging, config validation, comprehensive error handling
✅ **Container Ready** - Docker Compose for local multi-agent runs

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
MAX_TOKENS=8192
BEDROCK_READ_TIMEOUT=300
BEDROCK_CONNECT_TIMEOUT=30
BEDROCK_MAX_ATTEMPTS=3
ORCHESTRATOR_LOG_LEVEL=INFO
```

### Run Standalone Agents (Docker Compose)

```bash
docker compose up --build
```

Standalone agent endpoints:
- `http://localhost:8001/v1/message:send` (deep intel)
- `http://localhost:8002/v1/message:send` (aws research)
- `http://localhost:8003/v1/message:send` (business intel)

Each container runs the same image and selects its agent via `AGENT_ID`.
Deep Intel reaches the other agents via the service DNS names in `docker-compose.yml`.

## A2A Protocol Support

Each agent implements the A2A HTTP+JSON binding and exposes its agent card at:
- `GET /.well-known/agent-card.json`

Each agent exposes:

- `POST /v1/message:send`
- `POST /v1/message:stream` (SSE)
- `GET /v1/tasks/{id}`
- `POST /v1/tasks/{id}:cancel`
- `GET /v1/tasks/{id}:subscribe` (SSE)

---

## Project Structure

```
Dockerfile                      # Single image for all agents
docker-compose.yml              # Three standalone agent services
agents/
├── agent_cards.py             # Agent card builder
├── clients.py                 # A2A HTTP client helpers for sub-agent calls
├── registry.py                # Agent registry + URL resolution
├── skills.py                  # Agent skill definitions for cards
├── aws_research/              # AWS Research agent runtime
│   ├── executor.py            # A2A executor entrypoint
│   └── research_agent.py      # Agent logic + prompts/tools
├── business_intel/            # Business Intel agent runtime
│   ├── executor.py
│   └── research_agent.py
├── deep_intel/                # Deep Intel orchestrator
│   ├── executor.py
│   └── reporting.py           # HTML report storage + optional S3 upload
├── standalone_app.py          # Single-agent A2A service app (per container)
└── shared/                    # Shared helpers
    ├── base_executor.py       # A2A artifact publishing helpers
    ├── core/                  # Config + logging + exceptions
    ├── prompts/               # Agent system prompts
    └── tools/                 # Tavily tool wrappers

reports/                       # Generated HTML reports (bind mounted)
logs/                          # Application logs (bind mounted)
```

---

## How It Works

### Workflow Overview

The system uses standalone A2A services with a Deep Intel agent that calls two
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
- **Output**: HTML report

**4. Report Generation** (LLM HTML)
- Findings are rendered into HTML by the LLM
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
| `DEEP_INTEL_URL` | ❌ | - | Base URL for Deep Intel agent (standalone mode) |
| `AWS_RESEARCH_URL` | ❌ | - | Base URL for AWS Research agent (standalone mode) |
| `BUSINESS_INTEL_URL` | ❌ | - | Base URL for Business Intel agent (standalone mode) |
| `AGENT_ID` | ❌ | - | Agent ID when running a standalone container |
| `AGENT_BASE_URL` | ❌ | http://localhost:8000 | Public base URL for the running agent (agent card) |
| `MAX_TOKENS` | ❌ | 8192 | Maximum tokens per agent |
| `ORCHESTRATOR_LOG_LEVEL` | ❌ | INFO | Logging level (DEBUG/INFO/WARNING) |

### Getting API Keys

- **Perplexity**: https://www.perplexity.ai/api
- **Tavily**: https://tavily.com/api
- **AWS Bedrock**: Configure via AWS Console

---

## Output

### HTML Report

LLM-generated report saved to `reports/Company_Name_YYYY-MM-DD_HH-MM-SS.html` and uploaded to S3 when `S3_BUCKET` is set.

**Sections include:**
- Executive Summary
- AWS Opportunities & Case Studies
- Strategic Recommendations

---


## Dependencies

Core dependencies:
- `strands-agents` - Multi-agent orchestration
- `a2a-sdk` - A2A protocol server + client
- `fastapi` + `uvicorn` - API server
- LLM-generated HTML reporting (no template engine)
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
