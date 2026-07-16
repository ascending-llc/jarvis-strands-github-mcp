"""Typed deploy configuration, loaded from cdk/config.toml (+ config.local.toml).

Split by concern:
  - Typed fields drive INFRASTRUCTURE shape / IAM: ``image_tag``, ``token_secret_prefix``,
    ``jwt``. Changing these changes the CloudFormation/IAM the stack emits.
  - ``runtime_env`` is a free-form ``str -> str`` map from the ``[<env>.env]`` table,
    passed straight into every container's environment. Adding an ordinary app env var
    (MODEL, TAVILY_MCP_URL, REGISTRY_URL, a new flag, ...) means editing only config.toml
    — no Python change.
  - CDK-only values (AWS_REGION, REPORT_OUTPUT_DIR, worker ARNs, S3_BUCKET, AGENT_ID,
    A2A_TOKEN_SECRET_ARN) are injected by runtime_stack.py, not carried here — only CDK
    knows them.

config.local.toml (gitignored) deep-merges over config.toml per environment, for
account-specific values (real ARNs) that must not be committed.

CLI overrides (for one-off deploys; the file is the primary interface):
    -c env=<section>      select the config section (default: dev)
    -c imageTag=<tag>      override image_tag (CI passes the git sha here)
    -c jwtDiscoveryUrl / jwtAllowedAudience / jwtAllowedClients   override [env.jwt]
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"
# Gitignored overlay for account-specific values (AIP ARNs etc.) that must not be
# committed. Same shape as config.toml; its sections deep-merge over the base file.
LOCAL_CONFIG_PATH = CONFIG_PATH.with_name("config.local.toml")

# Container env vars the app's load_config() requires at startup — fail fast if unset.
REQUIRED_ENV_KEYS = ("MODEL", "TAVILY_MCP_URL")

_JWT_CTX_OVERRIDES = {
    "jwtDiscoveryUrl": "discovery_url",
    "jwtAllowedAudience": "allowed_audience",
    "jwtAllowedClients": "allowed_clients",
}


@dataclass(frozen=True)
class JwtConfig:
    discovery_url: str
    allowed_audience: list[str] = field(default_factory=list)
    allowed_clients: list[str] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return self.discovery_url.lower() != "none"


@dataclass(frozen=True)
class DeployConfig:
    env_name: str
    image_tag: str
    # Per-agent secret naming: each runtime's token lives at f"{prefix}/{agent_id}"
    # (e.g. agentcore/deep_intel) so its execution role only reads its own secret.
    token_secret_prefix: Optional[str]
    jwt: Optional[JwtConfig]
    # Free-form container env, injected verbatim into every runtime. Add app env
    # vars here (in config.toml [<env>.env]) — no Python change needed.
    runtime_env: dict[str, str]

    def token_secret_name(self, agent_id: str) -> str:
        return f"{self.token_secret_prefix}/{agent_id}"

    def validate_for_deploy(self) -> None:
        problems = [f"env.{k}" for k in REQUIRED_ENV_KEYS if not self.runtime_env.get(k)]
        if self.jwt and self.jwt.enabled and not (
            self.jwt.allowed_audience or self.jwt.allowed_clients
        ):
            problems.append("jwt.allowed_audience or jwt.allowed_clients")
        if problems:
            raise ValueError(
                f"cdk/config.toml [{self.env_name}] is missing required values: "
                + "; ".join(problems)
                + ". Fill them in (use config.local.toml for account-specific values)."
            )


def _as_list(val) -> list[str]:
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return [str(v) for v in val]
    return [s.strip() for s in str(val).split(",") if s.strip()]


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay onto base, one level deep for nested tables (env, jwt)."""
    result = dict(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = {**result[key], **val}
        else:
            result[key] = val
    return result


def load_deploy_config(ctx: Callable[[str], object]) -> DeployConfig:
    """Load the section selected by ``-c env=<name>`` (default dev), applying -c overrides."""
    env_name = str(ctx("env") or "dev")
    raw = tomllib.loads(CONFIG_PATH.read_text())
    if env_name not in raw:
        raise ValueError(f"cdk/config.toml has no [{env_name}] section (found: {sorted(raw)})")
    section = dict(raw[env_name])

    if LOCAL_CONFIG_PATH.exists():
        local_section = tomllib.loads(LOCAL_CONFIG_PATH.read_text()).get(env_name, {})
        section = _deep_merge(section, local_section)

    runtime_env = {str(k): str(v) for k, v in dict(section.get("env", {})).items()}

    jwt_raw = dict(section.get("jwt", {}))
    for ctx_key, field_name in _JWT_CTX_OVERRIDES.items():
        if ctx(ctx_key):
            jwt_raw[field_name] = ctx(ctx_key)
    jwt = (
        JwtConfig(
            discovery_url=str(jwt_raw["discovery_url"]),
            allowed_audience=_as_list(jwt_raw.get("allowed_audience")),
            allowed_clients=_as_list(jwt_raw.get("allowed_clients")),
        )
        if jwt_raw.get("discovery_url")
        else None
    )

    return DeployConfig(
        env_name=env_name,
        image_tag=str(ctx("imageTag") or section.get("image_tag") or "latest"),
        token_secret_prefix=(
            str(section["token_secret_prefix"]) if section.get("token_secret_prefix") else None
        ),
        jwt=jwt,
        runtime_env=runtime_env,
    )
