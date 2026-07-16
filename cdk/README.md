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

# 3. Create the shared Entra token secret (once; rotate by re-putting the value)
aws secretsmanager create-secret --name jarvis/a2a-entra-token \
  --secret-string '{"token":"<ENTRA_ID_ACCESS_TOKEN>"}'

# 4. Runtimes, pointing at that image tag and the Jarvis registry
cdk deploy JarvisAgentsRuntime \
  -c imageTag=<git-sha> \
  -c model=<bedrock-model-id-or-inference-profile-arn> \
  -c tavilyMcpUrl=<tavily-mcp-url> \
  -c registryUrl=https://jarvis.ascendingdc.com \
  -c tokenSecretArn=<arn-of-jarvis/a2a-entra-token> \
  -c jwtAllowedAudience=<audience-from-registry-runtimeAccess-config>
```

## Auth

The agents sit behind the **Jarvis registry** (https://jarvis.ascendingdc.com); all
deployed A2A traffic flows through its proxy.

- **Inbound to runtimes** (`jwt*` context): every runtime gets a `customJWTAuthorizer`.
  `jwtDiscoveryUrl` defaults to the registry auth-server
  (`https://jarvis.ascendingdc.com/.well-known/openid-configuration`) — runtimes accept
  the short-lived JWTs the registry mints when proxying calls to them. You must supply
  `jwtAllowedAudience` and/or `jwtAllowedClients` matching the registry's
  `runtimeAccess` config for these agents. `-c jwtDiscoveryUrl=none` disables JWT and
  falls back to IAM SigV4 (note: the registry cannot live-invoke IAM-only A2A runtimes).
- **Outbound to the registry** (`registryUrl` + `tokenSecretArn` context): all three
  runtimes get `REGISTRY_URL` and `A2A_TOKEN_SECRET_ARN` env vars plus
  `secretsmanager:GetSecretValue` on the token secret. `agents/shared/auth.py` reads a
  **static Entra ID token** from that secret (TTL-cached ~5 min, so rotation is picked
  up without restarts) and attaches it to registry-proxied calls. `A2A_BEARER_TOKEN`
  env overrides it for smoke tests; with neither set, the agent falls back to
  passing through its own caller's JWT.
- **Registration**: the agents must exist in the registry (path = `AGENT_ID`, or set
  `<AGENT_ID>_REGISTRY_PATH`). Use the registry's AgentCore federation sync, or
  `POST /api/v1/agents` manually.
- **Later**: replace the static token with a machine (client-credentials) OAuth flow so
  tokens don't need manual rotation.

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
- **Machine OAuth**: inter-agent auth currently uses a static, manually-rotated Entra
  token (see Auth above); a client-credentials flow should eventually replace it.
- **Secrets** (`TAVILY_MCP_TOKEN`): move to Secrets Manager rather than plain env.
