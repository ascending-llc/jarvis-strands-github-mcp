"""Report rendering and optional upload helpers."""

from __future__ import annotations

import os
from typing import Any, Optional

import boto3

from agents.shared.core.config import load_config
from agents.shared.utils import ensure_dir, render_report, save_report, utc_timestamp


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
    region = config.aws_region
    return f"https://{config.s3_bucket}.s3.{region}.amazonaws.com/{s3_key}"


def render_and_store_report(aggregated_data: dict[str, Any]) -> tuple[str, str | None, str | None]:
    html_report = render_report(aggregated_data)
    config = load_config()
    ensure_dir(config.report_output_dir)
    company = aggregated_data.get("company_overview", {}).get("official_name", "report")
    safe_company = str(company).replace(" ", "_").replace("/", "_")
    timestamp = utc_timestamp().replace(" ", "_").replace(":", "-")
    html_path = f"{config.report_output_dir}/{safe_company}_{timestamp}.html"
    html_path = save_report(html_report, html_path)
    report_url = upload_report_if_configured(html_path, config)
    return html_report, html_path, report_url
