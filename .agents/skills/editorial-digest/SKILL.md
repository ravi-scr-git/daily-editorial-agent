---
name: editorial-digest
description: Daily Editorial Aggregator & Analysis Agent that fetches, translates, and analyzes editorials from Eenadu, The Hindu, The Indian Express, and PIB.
---

# Daily Editorial Digest Workflow (`/editorial-digest`)

This skill defines the end-to-end automated pipeline for capturing, translating, analyzing, and publishing daily editorial and opinion content across four primary sources:
1. **Eenadu (Telugu):** `https://www.eenadu.net/editorial` (including సంపాదకీయం and వ్యాఖ్యానం / Pratibha sections)
2. **The Hindu:** `https://www.thehindu.com/opinion/editorial/`
3. **The Indian Express:** `https://indianexpress.com/section/opinion/editorials/`
4. **PIB (Press Information Bureau):** `https://pib.gov.in` (Official releases, backgrounders, explainers)

---

## 1. Parallel Sourcing & Subagent Delegation

When triggered with `/editorial-digest [date]`, the coordinator agent initiates parallel extraction across all four pillars:

### Pillar 1: Eenadu (Telugu)
- **Target URL:** `https://www.eenadu.net/editorial`
- **Scope:** 
  - Main Editorial (*సంపాదకీయం*)
  - Lead & Sub Commentary (*ప్రధాన వ్యాఖ్యానం*, *ఉప వ్యాఖ్యానం*)
  - Educational/Policy explainers (*ప్రతిభ / Pratibha*)
- **Telugu Linguistic Processing:**
  - Retain the exact Telugu headline in `original_title`.
  - Provide a fluent, high-fidelity English translation in `english_title`.
  - Perform analytical breakdown in clear, professional English.
  - Include key Telugu vocabulary in parentheses alongside English analysis (e.g., *ప్రజారోగ్యం (Public Health)*, *రాజ్యాంగం (Constitution)*, *సమతుల వ్యూహం (Balanced Strategy)*).

### Pillar 2: The Hindu
- **Target URL:** `https://www.thehindu.com/opinion/editorial/`
- **Scope:** Lead editorials and op-ed columns of the day.
- Focus on constitutional law, judicial developments, macroeconomic policy, and international diplomacy.

### Pillar 3: The Indian Express
- **Target URL:** `https://indianexpress.com/section/opinion/editorials/`
- **Scope:** Main editorials and the "Explained" / "Opinion" section.
- Focus on governance critique, administrative reforms, and sector-specific policies.

### Pillar 4: PIB / Official Explainers
- **Target URL:** `https://pib.gov.in`
- **Scope:** Press releases, Cabinet decisions, Ministry backgrounders, and government fact-sheets.
- Focus on official policy context, budgetary outlay data, and legislative milestones.

---

## 2. Standardized Editorial Schema (JSON)

Every captured editorial must be structured into the following JSON format:

```json
{
  "date": "YYYY-MM-DD",
  "source": "Eenadu | The Hindu | Indian Express | PIB",
  "original_title": "Original headline as published",
  "english_title": "English translated headline",
  "url": "https://direct-link-to-article",
  "theme": "Polity & Governance | Economy | International Relations | Science & Tech | Social Justice | Environment",
  "summary": "Concise 3-4 sentence executive summary articulating the core issue, argument, and editorial stance.",
  "key_bullet_points": [
    "Takeaway 1: Essential fact or premise",
    "Takeaway 2: Primary argument or structural conflict",
    "Takeaway 3: Empirical data or committee finding",
    "Takeaway 4: Recommendation or conclusion"
  ],
  "scope": "National | State (AP/Telangana) | Bilateral | Global",
  "impact": {
    "short_term": "Immediate socio-economic, legislative, or administrative implications.",
    "long_term": "Long-term structural, constitutional, or global ramifications."
  },
  "other_characteristics": {
    "tone": "Critical | Reformist | Cautionary | Analytical | Appreciative",
    "acts_and_articles_cited": ["e.g., Article 21, NHA 2017, Jan Aushadhi Scheme"],
    "key_data_and_statistics": ["e.g., 1.43% GDP spending, 43% out-of-pocket expenditure"],
    "exam_policy_relevance": "High relevance for UPSC/State PSC GS-2 (Health, Governance), GS-3 (Economy)."
  }
}
```

---

## 3. Storage and Site Regeneration Pipeline

Once articles are extracted and formatted:
1. Save the array of JSON records to a temporary file (e.g. `scraped_editorials.json`).
2. Upsert the records into the SQLite database:
   ```bash
   python db_manager.py insert scraped_editorials.json
   ```
   *Note: `db_manager.py` deduplicates entries automatically using the article URL.*
3. Rebuild the static dashboard:
   ```bash
   python generate_site.py
   ```
4. Output a summary table in Markdown highlighting:
   - Total editorials processed by source.
   - Core themes covered today.
   - Link to inspect `index.html`.
