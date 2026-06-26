"""Runtime stack: 3 AgentCore runtimes from one shared image, selected by AGENT_ID.

Workers are created first so the orchestrator can reference their runtime ARNs (injected
as env vars + granted InvokeAgentRuntime). All three use the same container image; only
AGENT_ID (and the orchestrator's extra wiring) differs — the docker-compose model lifted
to AgentCore.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_bedrockagentcore as agentcore
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

# AgentCore runtime name pattern is [a-zA-Z][a-zA-Z0-9_]{0,47} — underscores OK, no hyphens.
WORKER_IDS = ["aws_research", "business_intel"]
ORCHESTRATOR_ID = "deep_intel"


class RuntimeStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        repository: ecr.IRepository,
        reports_bucket: s3.IBucket,
        image_tag: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.container_uri = repository.repository_uri_for_tag(image_tag)
        self.reports_bucket = reports_bucket

        # --- shared runtime config (set real values via `cdk deploy -c key=value`) ---
        ctx = self.node.try_get_context
        self.common_env = {
            # MODEL and TAVILY_MCP_URL are required by load_config() at container startup.
            "MODEL": ctx("model") or "REPLACE_WITH_BEDROCK_MODEL_ID",
            "TAVILY_MCP_URL": ctx("tavilyMcpUrl") or "REPLACE_WITH_TAVILY_MCP_URL",
            "AWS_REGION": self.region,
            # AgentCore container FS is ephemeral; /tmp is writable. Real output goes to S3.
            "REPORT_OUTPUT_DIR": "/tmp/reports",
        }
        # TODO(secrets): move TAVILY_MCP_TOKEN and the machine-OAuth client secret to
        # Secrets Manager and inject/read them at runtime rather than as plain env.

        self._authorizer = self._build_jwt_authorizer()

        # Workers first → capture their ARNs for the orchestrator.
        worker_runtimes: dict[str, agentcore.CfnRuntime] = {}
        for agent_id in WORKER_IDS:
            worker_runtimes[agent_id] = self._make_runtime(agent_id, env=dict(self.common_env))

        # Orchestrator: worker ARNs injected as env + InvokeAgentRuntime granted + S3 write.
        worker_arns = [r.attr_agent_runtime_arn for r in worker_runtimes.values()]
        orch_env = dict(self.common_env)
        orch_env["AWS_RESEARCH_AGENT_ARN"] = worker_runtimes["aws_research"].attr_agent_runtime_arn
        orch_env["BUSINESS_INTEL_AGENT_ARN"] = worker_runtimes["business_intel"].attr_agent_runtime_arn
        orch_env["S3_BUCKET"] = reports_bucket.bucket_name

        self._make_runtime(
            ORCHESTRATOR_ID,
            env=orch_env,
            invoke_runtime_arns=worker_arns,
            allow_reports_write=True,
        )

    # ------------------------------------------------------------------ helpers

    def _make_runtime(
        self,
        agent_id: str,
        *,
        env: dict,
        invoke_runtime_arns: list[str] | None = None,
        allow_reports_write: bool = False,
    ) -> agentcore.CfnRuntime:
        role = self._make_execution_role(agent_id, invoke_runtime_arns, allow_reports_write)
        env = {**env, "AGENT_ID": agent_id}

        runtime = agentcore.CfnRuntime(
            self,
            f"Runtime-{agent_id}",
            agent_runtime_name=agent_id,
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=self.container_uri,
                ),
            ),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC",
            ),
            protocol_configuration="A2A",
            role_arn=role.role_arn,
            environment_variables=env,
            authorizer_configuration=self._authorizer,
        )

        cdk.CfnOutput(self, f"Arn-{agent_id}", value=runtime.attr_agent_runtime_arn)
        return runtime

    def _make_execution_role(
        self,
        agent_id: str,
        invoke_runtime_arns: list[str] | None,
        allow_reports_write: bool,
    ) -> iam.Role:
        role = iam.Role(
            self,
            f"ExecRole-{agent_id}",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description=f"AgentCore execution role for {agent_id}",
        )

        # Bedrock model invocation (scope to your model/inference-profile ARN in prod).
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=["*"],
            )
        )
        # Pull the image + write CloudWatch logs.
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Orchestrator → workers: InvokeAgentRuntime on the worker runtime ARNs (+ endpoints).
        if invoke_runtime_arns:
            resources = []
            for arn in invoke_runtime_arns:
                resources.extend([arn, f"{arn}/*"])
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["bedrock-agentcore:InvokeAgentRuntime"],
                    resources=resources,
                )
            )

        if allow_reports_write:
            self.reports_bucket.grant_write(role)

        return role

    def _build_jwt_authorizer(self):
        """Inbound JWT authorizer (Entra/your IdP). Returns None → defaults to IAM SigV4.

        TODO(auth): copy these values from your existing AgentCore runtime. Provide via
        `cdk deploy -c jwtDiscoveryUrl=... -c jwtAllowedAudience=... -c jwtAllowedClients=...`.
        Discovery URL must end in /.well-known/openid-configuration.
        """
        ctx = self.node.try_get_context
        discovery_url = ctx("jwtDiscoveryUrl")
        if not discovery_url:
            return None

        def _as_list(val):
            if val is None:
                return None
            return val if isinstance(val, list) else [val]

        return agentcore.CfnRuntime.AuthorizerConfigurationProperty(
            custom_jwt_authorizer=agentcore.CfnRuntime.CustomJWTAuthorizerConfigurationProperty(
                discovery_url=discovery_url,
                allowed_audience=_as_list(ctx("jwtAllowedAudience")),
                allowed_clients=_as_list(ctx("jwtAllowedClients")),
            )
        )
