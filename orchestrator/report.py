"""HTML report generator for AWS customer intelligence."""

from typing import Any, Dict, List

from orchestrator.utils import utc_timestamp


AWS_STYLES = """
:root {
  --aws-orange: #FF9900;
  --aws-dark-blue: #232F3E;
  --aws-light-gray: #F2F3F3;
  --aws-white: #FFFFFF;
}
body {
  font-family: Arial, sans-serif;
  margin: 0;
  padding: 0;
  background: var(--aws-light-gray);
  color: #111;
}
header {
  background: var(--aws-dark-blue);
  color: var(--aws-white);
  padding: 24px 32px;
}
header h1 { margin: 0; }
section {
  background: var(--aws-white);
  margin: 16px 32px;
  padding: 16px 20px;
  border-radius: 8px;
}
section h2 {
  color: var(--aws-dark-blue);
  border-bottom: 2px solid var(--aws-orange);
  padding-bottom: 8px;
}
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--aws-orange);
  color: #111;
  font-weight: bold;
}
ul { padding-left: 20px; }
small { color: #555; }
"""


def _list_items(items: List[str]) -> str:
    if not items:
        return "<p>Not available.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def render_html_report(report_model: Dict[str, Any]) -> str:
    meta = report_model.get("report_metadata", {})
    company = report_model.get("report_sections", {}).get("company_profile", {})
    exec_summary = report_model.get("report_sections", {}).get("executive_summary", "")
    aws_cases = report_model.get("report_sections", {}).get("aws_case_studies", [])
    recommendations = report_model.get("report_sections", {}).get("strategic_recommendations", [])

    title = f"AWS Customer Intelligence Report - {meta.get('validated_company_name', 'Unknown')}"

    case_study_html = "".join(
        f"<li><a href=\"{case.get('url', '#')}\" target=\"_blank\" rel=\"noopener noreferrer\">{case.get('company', 'Case Study')}</a> - {case.get('business_outcomes', [''])[0]}</li>"
        for case in aws_cases
    )

    rec_html = "".join(
        f"<li><strong>{rec.get('priority', 'Priority')}:</strong> {rec.get('recommendation', '')}</li>"
        for rec in recommendations
    )

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <style>{AWS_STYLES}</style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p><span class=\"badge\">Confidence: {meta.get('overall_confidence', 'UNKNOWN')}</span></p>
    <small>Generated: {utc_timestamp()}</small>
  </header>

  <section>
    <h2>Executive Summary</h2>
    <p>{exec_summary or 'Not available.'}</p>
  </section>

  <section>
    <h2>Company Profile</h2>
    <p>{company.get('description', 'Not available.')}</p>
  </section>

  <section>
    <h2>Relevant AWS Case Studies</h2>
    <ul>{case_study_html or '<li>Not available.</li>'}</ul>
  </section>

  <section>
    <h2>Strategic Recommendations</h2>
    <ul>{rec_html or '<li>Not available.</li>'}</ul>
  </section>
</body>
</html>"""
