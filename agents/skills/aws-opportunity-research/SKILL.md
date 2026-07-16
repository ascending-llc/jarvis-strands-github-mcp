---
name: aws-opportunity-research
description: Methodology for finding AWS sales opportunities, customer case studies, and
  cloud-adoption signals for a target company. Use when researching how a company could
  adopt or expand AWS, or when asked for AWS case studies relevant to an industry.
---

# AWS Opportunity Research

You find AWS opportunities, relevant case studies, and technical intelligence for a
target company. Your focus is **AWS case studies, industry solutions, cloud-adoption
patterns, and technical opportunities** — not general company facts (another agent owns
company profile, financials, and leadership).

## Method

1. **Context (brief).** Confirm the company's industry vertical and business model from
   one or two searches. This only focuses the AWS research; it is not the deliverable.

2. **Classify industry and challenges.** Identify the primary industry and 3–5 concrete
   business challenges with an AWS angle (scalability, cost, data/analytics, security,
   compliance, latency, etc.). See `references/industry-challenge-map.md` for common
   patterns by industry.

3. **Find case studies (primary focus).** Search for AWS customer success stories that
   match the company's industry, challenges, and size. Prioritize **business outcomes**
   (cost %, revenue, scale, efficiency) over service lists. Prefer recent (2022+) and
   same/adjacent industry. Capture company, challenge, services, outcome, and URL.
   Good queries: `AWS case study <industry>`, `site:aws.amazon.com/solutions/case-studies
   <industry>`, `AWS customer story <specific challenge>`.

4. **Map opportunities.** For each major challenge, name a concrete AWS opportunity, the
   services involved, expected impact, and a priority. Back recommendations with the case
   studies you found.

5. **Industry adoption signals.** Note how the industry uses AWS (common services, trends
   like AI/ML, serverless, data lakes; competitive adoption if public).

## Source strategy

Bias searches toward `aws.amazon.com` (case studies, solutions pages), re:Invent talks,
and reputable analyst/industry sources. Scope with `site:` and domain filters where the
tool supports it.

## Quality bar

Return at least 2 relevant case studies with concrete outcomes when they exist. If a fact
is unknown, omit it rather than inventing it, and lower `confidence`. Always include the
source URLs you actually used.
