"""Tests for the CDK deploy config loader and runtime-stack synthesis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cdk"))

from stacks.deploy_config import load_deploy_config  # noqa: E402


def _write_config(tmp_path, monkeypatch, body: str) -> None:
    from stacks import deploy_config

    path = tmp_path / "config.toml"
    path.write_text(body)
    monkeypatch.setattr(deploy_config, "CONFIG_PATH", path)
    # Isolate from the real (gitignored) cdk/config.local.toml, which may hold real
    # account values — tests must not depend on whatever happens to be on disk.
    monkeypatch.setattr(deploy_config, "LOCAL_CONFIG_PATH", tmp_path / "config.local.toml")


VALID_TOML = """
[dev]
image_tag = "latest"
token_secret_prefix = "agentcore"
jwt_discovery_url = "https://jarvis-demo.ascendingdc.com/.well-known/openid-configuration"
jwt_allowed_audience = ["jarvis-managed-agents"]

[dev.env]
MODEL = "arn:aws:bedrock:us-east-1:1:application-inference-profile/x"
TAVILY_MCP_URL = "https://tavily.example/mcp"
REGISTRY_URL = "https://jarvis-demo.ascendingdc.com"
"""


def test_load_config_returns_plain_dict(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch, VALID_TOML)
    cfg = load_deploy_config(lambda key: None)
    assert cfg["image_tag"] == "latest"
    assert cfg["token_secret_prefix"] == "agentcore"
    assert cfg["jwt_discovery_url"].startswith("https://jarvis-demo")
    assert cfg["jwt_allowed_audience"] == ["jarvis-managed-agents"]
    assert cfg["env"]["REGISTRY_URL"] == "https://jarvis-demo.ascendingdc.com"
    assert cfg["env"]["MODEL"].startswith("arn:aws:bedrock")


def test_local_overlay_merges_env(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch, VALID_TOML)
    (tmp_path / "config.local.toml").write_text(
        '[dev.env]\nMODEL = "arn:local:override"\nEXTRA_FLAG = "on"\n'
    )
    cfg = load_deploy_config(lambda key: None)
    assert cfg["env"]["MODEL"] == "arn:local:override"  # overlay wins
    assert cfg["env"]["EXTRA_FLAG"] == "on"  # new key added
    assert cfg["env"]["TAVILY_MCP_URL"] == "https://tavily.example/mcp"  # base kept


def test_image_tag_override(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch, VALID_TOML)
    cfg = load_deploy_config({"imageTag": "abc123"}.get)
    assert cfg["image_tag"] == "abc123"


def test_unknown_env_section_raises(tmp_path, monkeypatch) -> None:
    _write_config(tmp_path, monkeypatch, VALID_TOML)
    with pytest.raises(ValueError, match=r"no \[staging\] section"):
        load_deploy_config({"env": "staging"}.get)


def test_missing_required_env_raises(tmp_path, monkeypatch) -> None:
    _write_config(
        tmp_path,
        monkeypatch,
        '[dev]\nimage_tag = "latest"\n\n[dev.env]\nTAVILY_MCP_URL = "https://t.example"\n',
    )
    with pytest.raises(ValueError, match=r"env\.MODEL is required"):
        load_deploy_config(lambda key: None)


def _synth(config: dict):
    import aws_cdk as cdk
    import aws_cdk.assertions as assertions
    from aws_cdk import aws_ecr as ecr
    from aws_cdk import aws_s3 as s3

    from stacks.runtime_stack import RuntimeStack

    app = cdk.App()
    aws_env = cdk.Environment(account="123456789012", region="us-east-1")

    class Wrapper(cdk.Stack):
        pass

    w = Wrapper(app, "W", env=aws_env)
    stack = RuntimeStack(
        app,
        "S",
        repository=ecr.Repository.from_repository_name(w, "R", "myrepo"),
        reports_bucket=s3.Bucket.from_bucket_name(w, "B", "my-reports-bucket"),
        config=config,
        env=aws_env,
    )
    return assertions.Template.from_stack(stack)


def _full_config(**overrides) -> dict:
    cfg = {
        "image_tag": "latest",
        "token_secret_prefix": "agentcore",
        "jwt_discovery_url": "https://jarvis-demo.ascendingdc.com/.well-known/openid-configuration",
        "jwt_allowed_audience": ["jarvis-managed-agents"],
        "jarvis_environment": "demo",
        "env": {
            "MODEL": "arn:aws:bedrock:us-east-1:1:application-inference-profile/x",
            "TAVILY_MCP_URL": "https://tavily.example/mcp",
            "REGISTRY_URL": "https://jarvis-demo.ascendingdc.com",
        },
    }
    cfg.update(overrides)
    return cfg


def test_synth_full_registry_config() -> None:
    template = _synth(_full_config())
    runtimes = template.find_resources("AWS::BedrockAgentCore::Runtime")
    assert len(runtimes) == 3

    seen_agent_ids = set()
    for key, resource in runtimes.items():
        props = resource["Properties"]
        agent_id = props["AgentRuntimeName"]
        seen_agent_ids.add(agent_id)
        env = props["EnvironmentVariables"]
        # [<env>.env] values flow through verbatim to every runtime.
        assert env["REGISTRY_URL"] == "https://jarvis-demo.ascendingdc.com", key
        assert env["MODEL"].startswith("arn:aws:bedrock"), key
        assert env["TAVILY_MCP_URL"] == "https://tavily.example/mcp", key
        assert props["Tags"] == {"jarvis-environment": "demo"}, key
        # CDK-injected per-runtime values.
        assert env["AGENT_ID"] == agent_id, key
        assert env["A2A_TOKEN_SECRET_ARN"] == f"agentcore/{agent_id}", key
        authorizer = props["AuthorizerConfiguration"]["CustomJWTAuthorizer"]
        assert authorizer["DiscoveryUrl"].startswith("https://jarvis-demo"), key
        assert authorizer["AllowedAudience"] == ["jarvis-managed-agents"], key
    assert seen_agent_ids == {"aws_research", "business_intel", "deep_intel"}

    # Each role reads only its OWN secret — never a sibling's.
    policies = template.find_resources("AWS::IAM::Policy")
    grants = [p for p in policies.values() if "secretsmanager:GetSecretValue" in json.dumps(p)]
    assert len(grants) == 3

    granted_agents = []
    for policy in grants:
        blob = json.dumps(policy)
        matching_agents = [a for a in seen_agent_ids if f"secret:agentcore/{a}" in blob]
        assert len(matching_agents) == 1, f"expected exactly one agent's secret per role: {blob}"
        agent_id = matching_agents[0]
        assert f"agentcore/{agent_id}-??????" in blob
        assert f":secretsmanager:us-east-1:123456789012:secret:agentcore/{agent_id}" in blob
        granted_agents.append(agent_id)
    assert set(granted_agents) == seen_agent_ids  # each of the 3 agents got its own grant


def test_synth_jwt_none_falls_back_to_sigv4() -> None:
    template = _synth(_full_config(jwt_discovery_url="none"))
    runtimes = template.find_resources("AWS::BedrockAgentCore::Runtime")
    assert all("AuthorizerConfiguration" not in r["Properties"] for r in runtimes.values())
