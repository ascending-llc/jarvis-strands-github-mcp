# CDK — AgentCore deployment

Deploys the three agents as **AgentCore Runtimes** on the **A2A protocol** contract.
One shared ECR image; each runtime selects its agent via the `AGENT_ID` env var.

## Layout
- `app.py` — CDK app; wires the two stacks.
- `stacks/base_stack.py` — ECR repository + reports S3 bucket (rarely changes).
- `stacks/runtime_stack.py` — 3 `CfnRuntime` (A2A) + per-agent IAM roles.

## Prereqs
```bash
cd cdk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # aws-cdk-lib, constructs
npm install -g aws-cdk                  # the `cdk` CLI (Node)
```

## Deploy
```bash
# 1. Base infra (creates the ECR repo so CI can push to it)
cdk deploy JarvisAgentsBase

# 2. CI builds & pushes the image  ->  <repo>:<git-sha>  (.github/workflows/ci-ecr.yml)

# 3. Runtimes, pointing at that image tag
cdk deploy JarvisAgentsRuntime \
  -c imageTag=<git-sha> \
  -c model=<bedrock-model-id-or-inference-profile-arn> \
  -c tavilyMcpUrl=<tavily-mcp-url> \
  -c jwtDiscoveryUrl=https://login.microsoftonline.com/<TENANT_ID>/v2.0/.well-known/openid-configuration \
  -c jwtAllowedAudience=api://<your-api-app-id> \
  -c jwtAllowedClients=<deep-intel-client-id>
```

Workers are created before the orchestrator; their runtime ARNs are injected into
`deep_intel`'s env (`AWS_RESEARCH_AGENT_ARN` / `BUSINESS_INTEL_AGENT_ARN`) and granted
via `bedrock-agentcore:InvokeAgentRuntime`.

## Rolling a new image (decoupled, ECS-style)
CDK is **not** redeployed for code changes. CI pushes a new image, then:
```bash
aws bedrock-agentcore-control update-agent-runtime --agent-runtime-id <id> ...
```
(the ECS `force-new-deployment` analog). Use `-c imageTag=<sha>` + `cdk deploy` only when
you want the rollout tracked in IaC.

## Not yet wired
- **Inbound auth** (`jwt*` context): copy values from your existing AgentCore runtime.
  Omit them entirely → runtime defaults to IAM SigV4.
- **Inter-agent auth**: `deep_intel` → workers needs a bearer token; the seam is in
  `agents/a2a_client.py` (`_auth_token`), a no-op until the machine-OAuth flow is ready.
- **Secrets** (`TAVILY_MCP_TOKEN`, OAuth client secret): move to Secrets Manager rather
  than plain env.
