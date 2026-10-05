"""Tests for the deterministic report renderer (ReportContent -> Jinja2 -> HTML)."""

from __future__ import annotations

from agents.deep_intel.reporting import render_report, upload_report_if_configured
from agents.shared.schemas import (
    ReportContent,
    ReportOpportunity,
    ReportRecommendation,
    SnapshotRow,
)


def _sample_content() -> ReportContent:
    return ReportContent(
        company_name="Stripe, Inc.",
        executive_summary="Stripe is a payments company.\n\nSecond paragraph.",
        snapshot=[
            SnapshotRow(attribute="Industry Vertical", value="Fintech", confidence="HIGH"),
            SnapshotRow(attribute="Employee Count", value="Unknown", confidence="LOW"),
        ],
        data_notice="Research connectors returned limited data.",
        opportunities=[
            ReportOpportunity(
                title="ML-Driven Fraud & Risk",
                description="SageMaker-based fraud models.",
                aws_services=["Amazon SageMaker", "Amazon Fraud Detector"],
                case_study=None,
                priority="High",
            )
        ],
        recommendations=[
            ReportRecommendation(title="Validate current state", detail="Do discovery first.")
        ],
        confidence="MEDIUM",
        sources=["https://stripe.com"],
    )


def test_render_report_produces_full_html() -> None:
    html = render_report(_sample_content())
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "Stripe, Inc." in html
    assert "ML-Driven Fraud &amp; Risk" in html  # autoescaped
    assert "Amazon SageMaker, Amazon Fraud Detector" in html
    assert "Validate current state" in html
    assert "Research connectors returned limited data." in html
    assert "https://stripe.com" in html


def test_render_report_escapes_injected_markup() -> None:
    content = _sample_content()
    content.executive_summary = 'Summary with <script>alert("x")</script> tags.'
    html = render_report(content)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_render_report_omits_optional_sections() -> None:
    content = _sample_content()
    content.data_notice = None
    content.sources = []
    html = render_report(content)
    assert "Data Availability Notice" not in html
    assert '<section id="sources">' not in html


def test_upload_report_if_configured_returns_presigned_url(monkeypatch) -> None:
    """The reports bucket is private — uploads must return a presigned URL, not a static
    path-style URL that would require the bucket (or object) to be publicly readable."""
    from agents.deep_intel import reporting

    calls: dict = {}

    class FakeS3Client:
        def upload_file(self, filename, bucket, key, ExtraArgs=None):
            calls["upload"] = (filename, bucket, key, ExtraArgs)

        def generate_presigned_url(self, operation, Params=None, ExpiresIn=None):
            calls["presign"] = (operation, Params, ExpiresIn)
            return "https://example-bucket.s3.amazonaws.com/signed?X-Amz-Signature=abc"

    monkeypatch.setattr(reporting.boto3, "client", lambda *a, **k: FakeS3Client())

    class FakeConfig:
        s3_bucket = "example-bucket"
        s3_prefix = "aws-intel-reports"
        aws_region = "us-east-1"
        s3_presigned_url_expiry = 3600

    url = upload_report_if_configured("/tmp/report.html", FakeConfig())

    assert url == "https://example-bucket.s3.amazonaws.com/signed?X-Amz-Signature=abc"
    assert calls["presign"] == (
        "get_object",
        {"Bucket": "example-bucket", "Key": "aws-intel-reports/report.html"},
        3600,
    )


def test_save_report_tool_accepts_raw_dict_input(tmp_path, monkeypatch) -> None:
    """Exercise save_report through the Strands tool path: input arrives as a raw dict
    (Strands does not instantiate Pydantic params), so the tool must validate itself."""
    import asyncio

    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    # Empty string (not delenv): load_config() re-reads .env with override=False, which
    # would re-add a deleted S3_BUCKET; an existing empty var stays empty → no S3 upload.
    monkeypatch.setenv("S3_BUCKET", "")
    from agents.deep_intel.orchestrator import save_report

    tool_use = {
        "toolUseId": "t1",
        "name": "save_report",
        "input": {"report": _sample_content().model_dump()},
    }

    async def run():
        event = None
        async for event in save_report.stream(tool_use, {}):
            pass
        return event.tool_result

    result = asyncio.run(run())
    assert result["status"] == "success", result
    saved = list(tmp_path.glob("*.html"))
    assert len(saved) == 1
    assert "Stripe, Inc." in saved[0].read_text()
