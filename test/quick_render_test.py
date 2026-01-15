"""Pytest for deep intel HTML output rendering."""

from __future__ import annotations

import json
from typing import Any, Dict

from agents.shared.utils import extract_json_from_text, render_report, save_report


SAMPLE_AGENT_RESULT: Dict[str, Any] = {
    "role": "assistant",
    "content": [
        {
            "text": """{
  \"company_overview\": {
    \"name\": \"Stripe, Inc.\",
    \"domain\": \"stripe.com\",
    \"industry\": \"Financial Technology\",
    \"sub_sector\": \"Payment Processing Platform\",
    \"description\": \"Stripe builds economic infrastructure for the internet, enabling businesses to accept payments and manage their businesses online.\",
    \"headquarters\": \"San Francisco, California, USA\",
    \"founded\": \"2010\",
    \"employees\": \"8,000+\",
    \"valuation\": \"$50 billion\",
    \"revenue\": \"$14.4 billion annually\",
    \"key_products\": [\"Stripe Payments\", \"Stripe Billing\", \"Stripe Connect\", \"Stripe Atlas\", \"Stripe Radar\"],
    \"notable_customers\": [\"Amazon\", \"Google\", \"Microsoft\", \"Uber\", \"Lyft\", \"Shopify\", \"Instacart\", \"DoorDash\", \"Zoom\", \"Slack\"]
  },
  \"business_intelligence\": {
    \"market_position\": \"Top 3 global payment processor with 15-20% market share\",
    \"business_model\": \"B2B SaaS with transaction-based revenue (2.9% + $0.30 per transaction)\",
    \"target_markets\": [\"Enterprise\", \"Mid-Market\", \"SMB\", \"Startups\"],
    \"geographic_presence\": [\"United States\", \"Europe\", \"Asia-Pacific\", \"Latin America\"],
    \"competitive_landscape\": {
      \"main_competitors\": [\"PayPal/Braintree\", \"Adyen\", \"Square\", \"Checkout.com\"],
      \"key_differentiators\": [\"Developer-first approach\", \"Superior API documentation\", \"Global payment method coverage\", \"Unified platform\"]
    },
    \"recent_developments\": [
      \"Raised $6.5B in Series I funding (March 2023)\",
      \"Launched Optimized Checkout Suite (October 2024)\",
      \"Expanded Amazon partnership for international markets (July 2024)\"
    ]
  },
  \"business_challenges\": {
    \"scalability\": {
      \"description\": \"Processing trillions in payment volume with seasonal peaks\",
      \"impact\": \"Critical - requires massive infrastructure scale\",
      \"aws_relevance\": \"High - auto-scaling and container services needed\"
    },
    \"security_compliance\": {
      \"description\": \"PCI-DSS compliance and fraud detection across 40+ countries\",
      \"impact\": \"Critical - regulatory requirements vary by region\",
      \"aws_relevance\": \"High - AWS security services and compliance frameworks\"
    },
    \"global_infrastructure\": {
      \"description\": \"Real-time payment processing across 190+ countries\",
      \"impact\": \"High - latency and availability requirements\",
      \"aws_relevance\": \"High - AWS global infrastructure and edge locations\"
    },
    \"cost_optimization\": {
      \"description\": \"Managing infrastructure costs while maintaining 99.99% availability\",
      \"impact\": \"Medium - balance between performance and cost\",
      \"aws_relevance\": \"High - AWS cost optimization tools and serverless options\"
    }
  },
  \"aws_opportunities\": {
    \"microservices_migration\": {
      \"opportunity\": \"Migrate to microservices architecture using Amazon EKS\",
      \"potential_impact\": \"40-50% improvement in deployment speed\",
      \"relevant_case_study\": \"FSS achieved 40% cost reduction and 50% efficiency gain\",
      \"priority\": \"High\"
    },
    \"global_payment_infrastructure\": {
      \"opportunity\": \"Leverage AWS global infrastructure for low-latency processing\",
      \"potential_impact\": \"35% reduction in transaction latency\",
      \"relevant_case_study\": \"Nium achieved 99.99% uptime processing $25B+ annually\",
      \"priority\": \"High\"
    },
    \"ai_fraud_detection\": {
      \"opportunity\": \"Implement Amazon SageMaker for real-time fraud detection\",
      \"potential_impact\": \"Enhanced security and compliance capabilities\",
      \"priority\": \"Medium\"
    },
    \"serverless_optimization\": {
      \"opportunity\": \"Use AWS Lambda and auto-scaling for cost-efficient infrastructure\",
      \"potential_impact\": \"40% potential cost reduction\",
      \"priority\": \"Medium\"
    }
  },
  \"industry_insights\": {
    \"market_trends\": [
      \"Embedded finance adoption\",
      \"Real-time payments growth\",
      \"Cryptocurrency integration\",
      \"Buy now pay later expansion\"
    ],
    \"aws_adoption_patterns\": [
      \"Microservices architecture for payment platforms\",
      \"Real-time fraud detection using AI/ML\",
      \"Serverless computing for transaction processing\",
      \"Multi-region deployment for global availability\"
    ],
    \"common_aws_services\": [
      \"Amazon EKS for container orchestration\",
      \"AWS Lambda for serverless processing\",
      \"Amazon API Gateway for integration\",
      \"AWS Security Hub for compliance\"
    ]
  },
  \"strategic_recommendations\": {
    \"immediate_priorities\": [
      \"Evaluate Amazon EKS for microservices migration to improve deployment speed\",
      \"Assess AWS global infrastructure for reducing transaction latency\"
    ],
    \"medium_term_initiatives\": [
      \"Implement AWS cost optimization tools to reduce infrastructure spend\",
      \"Deploy Amazon SageMaker for enhanced fraud detection\"
    ],
    \"long_term_vision\": \"Build a fully cloud-native, globally distributed payment infrastructure on AWS\"
  },
  \"next_steps\": {
    \"discovery_workshop\": \"Schedule AWS architecture review to assess current infrastructure\",
    \"proof_of_concept\": \"Test Amazon EKS migration with non-critical workloads\",
    \"cost_analysis\": \"Perform TCO analysis comparing current infrastructure to AWS\",
    \"timeline\": \"30-60 days for initial assessment\"
  },
  \"confidence_level\": \"HIGH\",
  \"research_completeness\": \"COMPREHENSIVE\"
}""",
        }
    ],
}


def _extract_message_text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError("Unexpected message format")
    first = content[0]
    if not isinstance(first, dict) or "text" not in first:
        raise ValueError("Unexpected message format")
    return str(first["text"])


def test_render_report() -> None:
    message_text = _extract_message_text(SAMPLE_AGENT_RESULT)
    parsed = extract_json_from_text(message_text)
    html = render_report(parsed)
    save_report(html, "reports/quick_render.html")
    assert "AWS Customer Intelligence Report" in html
