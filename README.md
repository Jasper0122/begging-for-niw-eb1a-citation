<h2 align="center">begging-for-citations</h2>

<p align="center">
NIW / EB-1A citation toolkit — find the papers that <em>should</em> be citing you, and ask them to.
</p>

<p align="center">
Your citation count isn't just about how good your work is.<br>
It's about who found it.<br>
A hundred papers in your field were published this year. Some of them are building on exactly what you did.<br>
They just haven't found you yet.
</p>

<p align="center">
<a href="#"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
&nbsp;
<a href="#"><img src="https://img.shields.io/badge/works%20for-NIW%20%7C%20EB--1A-green" alt="NIW EB-1A"></a>
</p>

---

## 🧠 What this is

Citation outreach has the highest ROI of any academic visibility strategy — but almost no one does it systematically.

The standard move is to wait. Publish, post on Twitter, hope Google Scholar picks it up, hope the right person finds it.

This tool flips that:

```
Your papers → OpenAlex topics → recent related papers
                                        ↓
                         filter out papers already citing you
                                        ↓
                    rank by: preprint? recency? topic overlap? small team?
                                        ↓
                         outreach tracker + email drafts
```

**Why preprints first:** A paper under review can still add citations. A published paper can't (without a revision). Preprints are the highest-priority targets — zero friction for the author to add you.

---

## ⚡ Quickstart

```bash
pip install pyalex requests
```

**If you already use [begging-for-recommenders](https://github.com/Jasper0122/begging-for-niw-eb1a-recommenders):**
```bash
# Reuse the same profile JSON
python scripts/find_unaware_papers.py \
  --profile ../begging-for-niw-eb1a-recommenders/data/profiles/<id>.json
```

**Standalone (search by name):**
```bash
python scripts/find_unaware_papers.py --name "Your Full Name"
```

**Standalone (with keyword fallback):**
```bash
python scripts/find_unaware_papers.py \
  --name "Your Full Name" \
  --keywords "urban sensing, street view, geospatial AI"
```

Output lands in `data/output/{author_id}_outreach.md`.

---

## 📋 What the output looks like

```markdown
## 1. Scalable urban scene understanding via multimodal fusion
**Score:** 63  **Type:** PREPRINT  **Year:** 2025  **Authors:** 3
**First author:** Zhang Wei
**DOI:** 10.48550/arXiv.2501.XXXXX

<details>
<summary>Email draft</summary>

Subject: Related work you might want to cite

Hi Wei,

I came across your preprint "Scalable urban scene understanding..."
— it's closely related to work I've done on [describe overlap].

My paper "..." addresses [shared problem]. You might want to consider
citing it before you finalize it.

Best,
[Your Name]
</details>

- [ ] Reviewed relevance  - [ ] Email sent  - [ ] Citation added
```

One file. Work top to bottom. Check boxes as you go.

---

## 🏆 Scoring (what to prioritize)

| Factor | Points | Why |
|--------|--------|-----|
| Preprint status | +30 | Still editable — zero friction to add a citation |
| Published 2025 | +20 | Very recent, might revise |
| Published 2024 | +15 | Recent enough |
| Topic overlap (per topic) | +8 each, cap 24 | Higher overlap = stronger case for citation |
| Has DOI | +5 | Real, findable paper |
| ≤ 3 authors | +10 | Small team = more responsive to emails |
| 4–6 authors | +5 | Still manageable |

**Prioritize:** score ≥ 50, type = PREPRINT. These are your best targets.

---

## ⚖️ How this differs from just searching Google Scholar

| Manual Google Scholar | This |
|---|---|
| Search your keywords, get 1000 results | Filtered to papers in your exact topic cluster |
| No way to filter "papers that don't cite me" | Automatically excludes already-citing papers |
| No signal on who to email first | Scored and ranked by receptiveness |
| No email drafts | Personalized draft per paper, ready to edit |
| Spreadsheet you build by hand | Tracker with checkboxes, auto-generated |

---

## 🔗 Works best with

**[begging-for-recommenders](https://github.com/Jasper0122/begging-for-niw-eb1a-recommenders)** — the companion tool.

They share the same profile JSON format:
- `begging-for-recommenders`: finds people who already cited you → ask for letters
- `begging-for-citations`: finds people who should cite you → grow your citation count

Together they cover both directions of NIW evidence building.

---

## 📦 Install

```bash
git clone https://github.com/Jasper0122/begging-for-niw-eb1a-citation.git
cd begging-for-niw-eb1a-citation
pip install pyalex requests
```

No API keys required. Uses [OpenAlex](https://openalex.org) — free, no auth needed.

---

## ⚠️ Known limits

- **Topic detection**: OpenAlex topics are automatically assigned and sometimes noisy — review the detected topics before trusting results
- **False positives**: "related but shouldn't cite you" will appear — always manually review relevance before sending
- **Rate limits**: adds sleep between requests; 10+ papers may take 2–3 minutes
- **Preprint detection**: relies on OpenAlex type field — some preprints are miscategorized as published

---

## 📬 The email etiquette

Keep it under 5 sentences. Be specific about the overlap. Don't ask — suggest.

> "You might want to consider citing it" > "Please cite my work"

Response rate drops sharply if the email reads like a citation request rather than a genuine heads-up between researchers.

---

*Your citation count is partially a discovery problem, not just a quality problem.*
*These papers exist. They overlap with yours. They just haven't found you.*
