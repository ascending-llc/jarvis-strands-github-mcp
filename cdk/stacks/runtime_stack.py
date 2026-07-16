"""Runtime stack: 3 AgentCore runtimes from one shared image, selected by AGENT_ID.

Workers are created first so the orchestrator can reference their runtime ARNs (injected
as env vars + granted InvokeAgentRuntime). All three use the same container image; only
AGENT_ID (and the orchestrator's extra wiring) differs — the docker-compose model lifted
to AgentCore. All deploy values come from cdk/config.toml (see stacks/deploy_config.py);
-c flags override per deploy.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_bedrockagentcore as agentcore
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from stacks.deploy_config import DeployConfig

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
        config: DeployConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config.validate_for_deploy()
        self.config = config
        self.container_uri = repository.repository_uri_for_tag(config.image_tag)
        self.reports_bucket = reports_bucket

        # App env vars come verbatim from config.toml [env.env] (MODEL, TAVILY_MCP_URL,
        # REGISTRY_URL, ...). CDK layers on the few values only it knows; AGENT_ID and
        # the per-agent A2A_TOKEN_SECRET_ARN are added per runtime in _make_runtime.
        self.common_env = {
            **config.runtime_env,
            "AWS_REGION": self.region,
            # AgentCore container FS is ephemeral; /tmp is writable. Real output goes to S3.
            "REPORT_OUTPUT_DIR": "/tmp/reports",
        }

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
        if self.config.token_secret_prefix:
            env["A2A_TOKEN_SECRET_ARN"] = self.config.token_secret_name(agent_id)

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

    def _token_secret_resources(self, agent_id: str) -> list[str]:
        """IAM resource ARNs for this agent's own token secret ("{prefix}/{agent_id}").

        Secrets Manager appends a random 6-char suffix to secret ARNs, so grant both the
        literal name and the `-??????` wildcard form. Scoped per agent — a runtime can
        only ever read its own secret, never a sibling's.
        """
        name = self.config.token_secret_name(agent_id)
        arn = f"arn:{self.partition}:secretsmanager:{self.region}:{self.account}:secret:{name}"
        return [arn, f"{arn}-??????"]

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

        # Each agent reads its own registry-token secret for outbound A2A calls.
        if self.config.token_secret_prefix:
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["secretsmanager:GetSecretValue"],
                    resources=self._token_secret_resources(agent_id),
                )
            )

        return role

    def _build_jwt_authorizer(self):
        """Inbound JWT authorizer from config.toml [env.jwt] (discovery_url = "none" → IAM SigV4).

        The discovery URL must be the issuer of the tokens that actually reach the
        runtimes — the Jarvis registry auth-server that proxies calls to them — and
        audience/clients must match its runtimeAccess config for these agents.
        """
        jwt = self.config.jwt
        if jwt is None or not jwt.enabled:
            return None
        return agentcore.CfnRuntime.AuthorizerConfigurationProperty(
            custom_jwt_authorizer=agentcore.CfnRuntime.CustomJWTAuthorizerConfigurationProperty(
                discovery_url=jwt.discovery_url,
                allowed_audience=jwt.allowed_audience or None,
                allowed_clients=jwt.allowed_clients or None,
            )
        )
