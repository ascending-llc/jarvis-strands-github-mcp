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
  -c jwtAllowedClients=<frontend-client-id>
```

## Auth

- **Inbound** (`jwt*` context): every runtime gets a `customJWTAuthorizer` built from
  `jwtDiscoveryUrl` / `jwtAllowedAudience` / `jwtAllowedClients` — AgentCore uses the
  discovery URL only to fetch signing keys and validate/decode the caller's JWT. Omit
  `jwtDiscoveryUrl` entirely → runtimes default to IAM SigV4.
- **Inter-agent** is bearer-token **passthrough** (`agents/shared/auth.py`): the platform
  frontend obtains the JWT and invokes `deep_intel` with it; the orchestrator reuses that
  same token when calling the worker runtimes, and the workers validate it against the
  same discovery URL. No OAuth client config, secret, or extra CDK context is needed —
  just make sure the token's audience/client passes the same `jwt*` values on the
  workers. For smoke-testing without the frontend, `A2A_BEARER_TOKEN` can be set on the
  orchestrator's env as a manual token override.
- **Later**: replace passthrough with a machine (client-credentials) OAuth flow so
  orchestrations aren't bounded by the frontend token's lifetime.

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
- **Machine OAuth**: inter-agent auth is currently token passthrough (see Auth above);
  a client-credentials flow should eventually replace it.
- **Secrets** (`TAVILY_MCP_TOKEN`): move to Secrets Manager rather than plain env.
