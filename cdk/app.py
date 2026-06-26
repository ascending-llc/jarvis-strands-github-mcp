#!/usr/bin/env python3
"""CDK app for deploying the three agents to AgentCore Runtime (A2A protocol).

Two stacks:
  - BaseStack:    ECR repository + reports S3 bucket (rarely changes).
  - RuntimeStack: 3 AgentCore runtimes (one shared image, selected by AGENT_ID) +
                  per-agent IAM execution roles.

Image build/push is owned by CI (.github/workflows/ci-ecr.yml), NOT by CDK — the
runtime stack only references an existing image tag. Roll a new image with
`aws bedrock-agentcore-control update-agent-runtime ...` (the ECS force-new-deployment
analog); pass the tag here via `-c imageTag=<tag>` so `cdk deploy` rolls it explicitly.

    cdk deploy JarvisAgentsBase
    # CI builds & pushes  <repo>:<git-sha>
    cdk deploy JarvisAgentsRuntime -c imageTag=<git-sha> \
        -c model=<bedrock-model-id> -c tavilyMcpUrl=<url>
"""

import os

import aws_cdk as cdk

from stacks.base_stack import BaseStack
from stacks.runtime_stack import RuntimeStack

app = cdk.App()
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

base = BaseStack(app, "JarvisAgentsBase", env=env)

RuntimeStack(
    app,
    "JarvisAgentsRuntime",
    repository=base.repository,
    reports_bucket=base.reports_bucket,
    image_tag=app.node.try_get_context("imageTag") or "latest",
    env=env,
)

app.synth()
