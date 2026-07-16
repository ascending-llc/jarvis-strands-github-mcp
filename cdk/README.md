# CDK — AgentCore deployment

Deploys the three agents as **AgentCore Runtimes** on the **A2A protocol** contract.
One shared ECR image; each runtime selects its agent via the `AGENT_ID` env var.

## Layout
- `app.py` — CDK app; wires the two stacks.
- `config.toml` — checked-in, per-environment deploy config (model, registry, JWT). No secrets.
- `config.local.toml` — gitignored overlay for account-specific values (real ARNs); merges over `config.toml`.
- `stacks/deploy_config.py` — loads `config.toml` (+ `config.local.toml`) into a typed `DeployConfig`, with `-c` flags as one-off overrides.
- `stacks/base_stack.py` — ECR repository + reports S3 bucket (rarely changes).
- `stacks/runtime_stack.py` — 3 `CfnRuntime` (A2A) + per-agent IAM roles.

## Prereqs
```bash
cd cdk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # aws-cdk-lib, constructs
npm install -g aws-cdk                  # the `cdk` CLI (Node)
cdk bootstrap aws://<account>/<region>  # once per account/region
```

## Configure

`cdk/config.toml` has two kinds of values per environment:

- **Typed** (top-level + `[env.jwt]`): drive infrastructure/IAM — `image_tag`,
  `token_secret_prefix`, and the JWT authorizer. Adding one of these touches
  `stacks/deploy_config.py`.
- **Free-form** (`[env.env]`): container env vars passed verbatim into every runtime
  (`MODEL`, `TAVILY_MCP_URL`, `REGISTRY_URL`, ...). **Adding an ordinary app env var means
  editing only this table — no Python change.**

Account-specific values (real ARNs) go in the gitignored `cdk/config.local.toml`, same
shape, deep-merged over `config.toml`. Pick the section with `-c env=dev` (default) or
`-c env=prod`. Per-deploy `-c` overrides: `-c imageTag=<sha>` and the JWT fields
(`-c jwtDiscoveryUrl=`, `-c jwtAllowedAudience=`, `-c jwtAllowedClients=`).

CDK injects the values only it knows on top of `[env.env]`: `AWS_REGION`,
`REPORT_OUTPUT_DIR`, `AGENT_ID`, each agent's `A2A_TOKEN_SECRET_ARN`, the orchestrator's
worker ARNs, and `S3_BUCKET`.

## Create the per-agent secrets (once; rotate by re-putting the value)

Each runtime reads its own token from `{token_secret_prefix}/<agent_id>` — e.g. with the
default prefix `agentcore`:

```bash
for agent in deep_intel aws_research business_intel; do
  aws secretsmanager create-secret --name "agentcore/${agent}" \
    --secret-string "{\"token\":\"<ENTRA_ID_ACCESS_TOKEN>\"}"
done
```

Each runtime's execution role can only read its own secret — a compromised worker can't
read the orchestrator's token or a sibling's.

## Deploy
```bash
# 1. Base infra (creates the ECR repo so CI can push to it)
cdk deploy JarvisAgentsBase

# 2. CI builds & pushes the image  ->  <repo>:<git-sha>  (.github/workflows/ci-ecr.yml)

# 3. Runtimes, using config.toml's [dev] section (override anything with -c)
cdk deploy JarvisAgentsRuntime -c env=dev -c imageTag=<git-sha>
```

## Auth

The agents sit behind the **Jarvis registry**; all deployed A2A traffic flows through
its proxy (`registry_url` in config.toml — demo: `jarvis-demo.ascendingdc.com`, prod:
`jarvis.ascendingdc.com`).

- **Inbound to runtimes** (`[env.jwt]` in config.toml): every runtime gets a
  `customJWTAuthorizer`. `discovery_url` must be the issuer of the tokens that actually
  reach the runtimes — the registry auth-server that proxies calls to them, not Entra
  directly. `allowed_audience`/`allowed_clients` must match the registry's
  `runtimeAccess` config for these agents (confirm by decoding a real token from that
  issuer, or asking the registry team). `discovery_url = "none"` disables JWT and falls
  back to IAM SigV4 (note: the registry cannot live-invoke IAM-only A2A runtimes).
- **Outbound to the registry** (`REGISTRY_URL` in `[env.env]` + `token_secret_prefix`):
  each runtime gets its own `A2A_TOKEN_SECRET_ARN` (`{prefix}/<agent_id>`) plus
  `secretsmanager:GetSecretValue` scoped to that one secret. `agents/shared/auth.py`
  reads a **static Entra ID token** from it (TTL-cached ~5 min, so rotation is picked up
  without restarts) and attaches it to registry-proxied calls. `A2A_BEARER_TOKEN` env
  overrides it for smoke tests; with neither set, the agent falls back to passing
  through its own caller's JWT.
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
  token per agent (see Auth above); a client-credentials flow should eventually replace it.
- **Secrets** (`TAVILY_MCP_TOKEN`): move to Secrets Manager rather than plain env.
