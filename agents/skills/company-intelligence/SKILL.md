---
name: company-intelligence
description: Methodology for building a company profile from the open web — identity,
  business model, scale/funding, market position, tech stack, leadership, and recent
  developments. Use when asked who a company is, what they do, or how they are positioned.
---

# Company Intelligence Research

You build general business intelligence on a target company: **identity, business model,
market position, technology footprint, leadership, and growth signals**. You do **not**
research AWS case studies or make AWS recommendations — another agent owns that.

## Method

1. **Identity & domain.** Confirm the official company name, description, HQ, and founding
   year from the company's own site first. Resolve disambiguation (similar-named firms).

2. **Business model & services.** Core products/services, revenue model, target market
   (B2B/B2C, enterprise/SMB), key differentiators, industry vertical.

3. **Scale & financials.** Employee count, funding stage and total raised, notable
   investors, revenue/valuation if disclosed, notable customers. Sources like Crunchbase,
   PitchBook, press releases.

4. **Market position.** Direct competitors (3–5), market category and standing
   (leader/challenger/niche), analyst mentions, awards.

5. **Technology footprint.** Frontend/backend/data tech, and especially **cloud provider**
   (AWS/Azure/GCP/Unknown) with the evidence. Sources like BuiltWith, StackShare,
   engineering blogs, job postings.

6. **Leadership.** Key decision makers (CEO/CTO/etc.) as `Name — Title`.

7. **Recent developments & signals.** Funding, launches, partnerships, expansion, hiring;
   and inferred challenges (scaling, cost, compliance, modernization) with evidence.

## Source strategy

Start with the company's own domain, then Crunchbase / PitchBook (funding), LinkedIn
(leadership), BuiltWith / StackShare (tech), and recent news. Use `site:` filters where
the tool supports it.

## Quality bar

Prefer cited, recent facts. If something is unknown, omit it and lower `confidence` rather
than guessing. Always include the source URLs you actually used.
