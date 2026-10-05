"""Load cdk/config.toml (+ gitignored config.local.toml overlay) for one environment.

Per AWS CDK guidance, config is read once at the top of the app and passed into the stack
as a plain object — no environment lookups inside the stack. Each ``[<env>]`` section holds:

  - **infra** keys CDK builds with: ``image_tag``, ``token_secret_prefix``, ``jwt_*``.
  - an ``[<env>.env]`` table of **app env vars** injected verbatim into every container.

One rule: everything is infra except the ``env`` block. Account-specific values (real
ARNs) live in the gitignored ``config.local.toml``, which deep-merges over ``config.toml``.
Select the section with ``-c env=<name>`` (default dev); ``-c imageTag=<sha>`` overrides the
image tag (CI passes the git sha).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Callable

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"
LOCAL_CONFIG_PATH = CONFIG_PATH.with_name("config.local.toml")


def load_deploy_config(ctx: Callable[[str], object]) -> dict:
    """Return the selected environment's merged config section as a plain dict."""
    env_name = str(ctx("env") or "dev")
    raw = tomllib.loads(CONFIG_PATH.read_text())
    if env_name not in raw:
        raise ValueError(f"cdk/config.toml has no [{env_name}] section (found: {sorted(raw)})")
    cfg = dict(raw[env_name])

    if LOCAL_CONFIG_PATH.exists():  # overlay account-specific values (merge the env table)
        for key, val in tomllib.loads(LOCAL_CONFIG_PATH.read_text()).get(env_name, {}).items():
            cfg[key] = {**cfg.get(key, {}), **val} if isinstance(val, dict) else val

    if ctx("imageTag"):  # CI passes the git sha per build
        cfg["image_tag"] = ctx("imageTag")

    for key in ("MODEL", "TAVILY_MCP_URL"):  # fail fast at synth, not at container start
        if not cfg.get("env", {}).get(key):
            raise ValueError(f"cdk/config.toml [{env_name}] env.{key} is required")

    return cfg
