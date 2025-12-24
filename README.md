# AWS Customer Intelligence Orchestrator

Multi-agent research system that coordinates specialized agents to produce comprehensive customer intelligence reports. Built with [Strands Agents SDK](https://strandsagents.com) using a parallel graph workflow.

## Overview

**Input:** Company domain + research prompt (e.g., `"Analyze atscale.com for AWS opportunities"`)
**Output:** Professional HTML report + structured JSON data

### Architecture

```
Dispatcher (Domain Verification)
        ↓
    ┌───┴───┐
    ↓       ↓
 Tavily  Perplexity (Parallel Research)
    ↓       ↓
    └───┬───┘
        ↓
   Aggregator (Synthesis)
        ↓
   HTML Report (Jinja2)
```

### Four Specialized Agents

1. **Dispatcher** - Verifies domain and prepares research context
2. **Perplexity Agent** - Business intelligence (company profile, market position, tech stack, leadership)
3. **Tavily Agent** - AWS-focused research (case studies, cloud solutions, opportunities)
4. **Aggregator** - Synthesizes findings and generates structured data for reporting

### Key Features

✅ **Parallel Execution** - Tavily and Perplexity run simultaneously for speed
✅ **Elegant HTML Reports** - Professional AWS-branded reports via Jinja2 templates
✅ **Token Efficient** - Separates data generation from presentation (30-40% token savings)
✅ **Fully Typed** - Type-safe with Pydantic models and proper error handling
✅ **Production Ready** - Structured logging, config validation, comprehensive error handling

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
AWS_DEFAULT_REGION=us-east-1

# Optional Settings (with defaults)
MODEL=anthropic.claude-sonnet-4-v1
REPORT_OUTPUT_DIR=reports
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
PYTHONPATH=. python -m orchestrator.run "Analyze business challenges for example.com"
```

---

## Project Structure

```
orchestrator/
├── agents/                    # Agent implementations
│   ├── __init__.py
│   ├── dispatcher_agent.py    # Domain verification
│   ├── perplexity_agent.py    # Business intelligence
│   ├── tavily_agent.py        # AWS-focused research
│   └── aggregator_agent.py    # Synthesis & recommendations
├── core/                      # Core infrastructure
│   ├── __init__.py
│   ├── config.py              # Configuration & validation
│   ├── exceptions.py          # Custom exception types
│   ├── logging_config.py      # Structured logging
│   └── context.py             # Execution context
├── tools/                     # Tool implementations
│   └── strands_tools.py       # Tavily API wrappers
├── templates/                 # HTML templates
│   └── report.html            # AWS-branded report template
├── graph.py                   # Graph orchestration logic
├── utils.py                   # Utilities (JSON, prompts, reports)
├── schemas.py                 # Pydantic data models
└── run.py                     # CLI entry point

prompts/                       # Agent system prompts
├── dispatcher_agent.md
├── perplexity_agent.md
├── tavily_agent.md
└── aggregator_agent.md

reports/                       # Generated HTML reports (auto-created)
logs/                          # Application logs (auto-created)
```

---

## How It Works

### Workflow Overview

The orchestrator uses a **4-node parallel graph pattern** powered by Strands Agents SDK:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  USER INPUT: "Research AWS opportunities for stripe.com"       │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │   DISPATCHER    │ (Domain Verification)
                   │                 │
                   │ • Validates     │
                   │   domain        │
                   │ • Extracts      │
                   │   company info  │
                   │ • Classifies    │
                   │   industry      │
                   └────────┬────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌──────────────────┐       ┌──────────────────┐
    │  TAVILY AGENT    │       │ PERPLEXITY AGENT │ (Parallel)
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
                 ┌──────────────────┐
                 │   AGGREGATOR     │ (Synthesis)
                 │                  │
                 │ • Combines       │
                 │   findings       │
                 │ • Maps AWS       │
                 │   opportunities  │
                 │ • Creates        │
                 │   strategic      │
                 │   recommendations│
                 │ • Generates      │
                 │   JSON data      │
                 └────────┬─────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  JINJA2 TEMPLATE │ (Report Generation)
                │                  │
                │ • Renders JSON   │
                │   to HTML        │
                │ • AWS-branded    │
                │   styling        │
                │ • Professional   │
                │   layout         │
                └────────┬─────────┘
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

**1. Dispatcher Agent** (Domain Verification)
- Validates company domain accessibility
- Extracts official company name and basic info
- Classifies industry and business model
- Identifies disambiguation issues
- **Output**: JSON with verified domain context
- **Passes to**: Both Tavily and Perplexity agents in parallel

**2. Parallel Research Phase**

**Tavily Agent** (AWS Intelligence):
- Receives dispatcher context automatically
- Searches for AWS case studies in company's industry
- Finds industry-specific cloud solutions
- Identifies competitive AWS adoption patterns
- Maps AWS services to business challenges
- **Output**: JSON with AWS opportunities and case studies
- **Typical Duration**: 30-45 minutes

**Perplexity Agent** (Business Intelligence):
- Receives dispatcher context automatically
- Researches company profile and business model
- Analyzes market position and competitors
- Investigates technology stack and infrastructure
- Identifies leadership team and key personnel
- Tracks recent developments and financial signals
- **Output**: JSON with comprehensive business intelligence
- **Typical Duration**: 60-90 minutes

**3. Aggregator Agent** (Synthesis)
- Automatically receives results from all previous agents via Strands
- Input format: `Inputs from previous nodes: From dispatcher: ..., From tavily: ..., From perplexity: ...`
- Combines findings from all three agents
- Resolves conflicts and fills information gaps
- Maps business challenges to AWS opportunities
- Creates strategic recommendations
- Assesses confidence levels and completeness
- **Output**: Structured JSON with synthesized intelligence

**4. Report Generation** (Jinja2 Template)
- Python code extracts JSON from aggregator
- Jinja2 template renders JSON data to HTML
- AWS-branded professional styling applied
- Saved to `reports/` directory with timestamp
- **Token Efficiency**: 30-40% reduction vs LLM-generated HTML



## Configuration Details

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERPLEXITY_API_KEY` | ✅ | - | Perplexity API key |
| `TAVILY_API_KEY` | ✅ | - | Tavily API key |
| `AWS_ACCESS_KEY_ID` | ✅ | - | AWS access key for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | ✅ | - | AWS secret key |
| `AWS_DEFAULT_REGION` | ❌ | us-east-1 | AWS region |
| `MODEL` | ❌ | sonnet | Bedrock model ID or inference profile |
| `REPORT_OUTPUT_DIR` | ❌ | reports | Output directory for HTML reports |
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
  "status": "Status.COMPLETED",
  "execution_order": ["dispatcher", "tavily", "perplexity", "aggregator"],
  "dispatcher_verification": {...},
  "tavily_research": {...},
  "perplexity_research": {...},
  "final_synthesis": {
    "company_overview": {...},
    "business_intelligence": {...},
    "business_challenges": [...],
    "aws_opportunities": [...],
    "strategic_recommendations": [...],
    "confidence_level": "HIGH",
    "research_completeness": "Complete"
  },
  "html_report_path": "reports/Company_Name_2025-12-24_15-30-00.html"
}
```

---


## Dependencies

Core dependencies:
- `strands-agents` - Multi-agent orchestration
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
