"""Report rendering, storage, and optional upload helpers.

HTML is rendered deterministically from a validated ``ReportContent`` via a Jinja2
template — the LLM contributes only the content (see agents/shared/schemas.py), never
markup. The template owns layout/CSS, so every report is valid, consistent HTML.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape

from agents.shared.core.config import load_config
from agents.shared.schemas import ReportContent
from agents.shared.utils import ensure_dir, save_report, utc_timestamp

_TEMPLATES_DIR = Path(__file__).parent.parent / "shared" / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_report(content: ReportContent) -> str:
    """Render the HTML report from validated report content."""
    return _jinja_env.get_template("report.html.j2").render(r=content)


def upload_report_if_configured(html_path: Optional[str], config: Any) -> Optional[str]:
    if not html_path:
        return None
    if not config.s3_bucket:
        return None
    key_prefix = config.s3_prefix.strip("/")
    filename = os.path.basename(html_path)
    s3_key = f"{key_prefix}/{filename}" if key_prefix else filename
    s3_client = boto3.client("s3", region_name=config.aws_region)
    s3_client.upload_file(
        html_path,
        config.s3_bucket,
        s3_key,
        ExtraArgs={"ContentType": "text/html"},
    )
    # The reports bucket is private (no public read) — a presigned URL grants time-limited
    # access to this one object instead of requiring the bucket itself to be public.
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.s3_bucket, "Key": s3_key},
        ExpiresIn=config.s3_presigned_url_expiry,
    )


def store_html_report(html_report: str, company_name: str | None = None) -> tuple[str, str | None, str | None]:
    config = load_config()
    ensure_dir(config.report_output_dir)
    safe_company = str(company_name or "report").replace(" ", "_").replace("/", "_")
    timestamp = utc_timestamp().replace(" ", "_").replace(":", "-")
    html_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.html"
    html_path = save_report(html_report, html_path)
    report_url = upload_report_if_configured(html_path, config)
    return html_report, html_path, report_url
