"""Base infrastructure: ECR repository (CI pushes here) and the reports S3 bucket.

Kept separate from the runtime stack so the repo exists before CI can push an image,
and so runtimes can be torn down/redeployed without destroying the image or reports.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct


class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Single image for all 3 agents; CI builds & pushes here.
        # MUTABLE so CI can re-push :latest; switch to IMMUTABLE if you pin :<git-sha>.
        self.repository = ecr.Repository(
            self,
            "AgentImage",
            repository_name="agentcore/aws_deep_intel",
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            image_scan_on_push=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # AgentCore validates pull access against the ECR repository policy at runtime
        # creation time — an IAM policy on the execution role alone is not enough. Grant
        # the service principal here, scoped to this account (matches the execution
        # roles' own trust condition in runtime_stack.py).
        self.repository.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowAgentCorePull",
                principals=[iam.ServicePrincipal("bedrock-agentcore.amazonaws.com")],
                actions=[
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
                conditions={"StringEquals": {"aws:SourceAccount": self.account}},
            )
        )

        # Reports sink (the AgentCore container FS is ephemeral — S3 is the real output).
        self.reports_bucket = s3.Bucket(
            self,
            "ReportsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        cdk.CfnOutput(self, "RepositoryUri", value=self.repository.repository_uri)
        cdk.CfnOutput(self, "ReportsBucketName", value=self.reports_bucket.bucket_name)
