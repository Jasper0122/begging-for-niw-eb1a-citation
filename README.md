<h2 align="center">begging-for-citations</h2>

<p align="center">
Find papers that <em>should</em> be citing you — and ask them to.
</p>

<p align="center">
A hundred papers in your field were published this year.<br>
Some of them are building on exactly what you did.<br>
They just haven't found you yet.
</p>

<p align="center">
<a href="#"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
&nbsp;
<a href="#"><img src="https://img.shields.io/badge/works%20for-NIW%20%7C%20EB--1A-green" alt="NIW EB-1A"></a>
</p>

---

## How it works

```
Your papers (title + abstract)
         │
         ▼
  Resolve OpenAlex topics
         │
         ▼
  Fetch recent related papers    ← crawl_openalex.py
  (with abstracts, 2023–now)
         │
         ▼
  Filter out papers already      ← same script
  citing you
         │
         ▼
  Embed everything with          ← search_similar.py
  sentence-transformers
  Match per paper, rank by cosine similarity
         │
         ▼
  Score by receptiveness         ← find_citations.py
  (preprint > recent > small team)
         │
         ▼
  Find author contact info       ← find_contacts.py
  (OpenAlex homepage, ORCID, arXiv)
         │
         ▼
  Outreach tracker + email drafts + progress log
  data/output/{id}_outreach.md
```

**Why embeddings, not keywords:**
Keyword search misses "vision-language model for urban sensing" when your paper says "multimodal LLM for street-view analysis." Embedding models understand both mean the same thing. You get real matches, not accidental ones.

---

## Recommended: Claude Skill

This repo ships with a `/niw-citation` skill for [Claude Code](https://claude.ai/code).

**What the skill does that scripts can't:**
- Reads every abstract and judges whether each paper is genuinely relevant (not just topically adjacent)
- Writes a specific, personalized overlap sentence for every email — no generic placeholders
- Decides which emails to send first based on similarity + contact availability
- Sends emails via Gmail if connected
- Tracks sent / replied / cited status across sessions

### Setup

**1 — Clone and install**

```bash
git clone https://github.com/Jasper0122/begging-for-niw-eb1a-citation.git
cd begging-for-niw-eb1a-citation
pip install -r requirements.txt
```

**2 — Open in Claude Code**

Download [Claude Code](https://claude.ai/code), then open this folder as your project.

**3 — Connect Gmail** _(optional but recommended)_

In Claude Code, run:
```
/mcp
```
Select **claude.ai Gmail** → complete the OAuth flow in your browser. One-time setup; auth persists across sessions. Without this, the skill still works — you just copy-paste emails manually at the end.

**4 — Run the skill**

```
/niw-citation
```

That's it. The skill takes over from here.

---

### What happens when you run `/niw-citation`

**Phase 1 — Data collection** _(~2 min, fully automatic)_

The skill finds your papers via Google Scholar profile or author name, fetches related papers from OpenAlex, runs embedding-based similarity ranking, and looks up author contact info. No input needed from you.

**Phase 2 — Relevance judgment**

Claude reads every abstract and filters the list down to papers with genuine overlap. Instead of dumping 20 results on you, you see something like:

```
Screened 12 papers → keeping 7

Group: based on your paper "StreetViewLLM"
  ✅ #1  VertiCue-Bench (59%, PREPRINT, 2025)
         Overlap: both apply vision-language models to street-level geospatial reasoning
         Contact: zhang@mit.edu ✓

  ✅ #2  Urban Mobility Synthesis (51%, 2026)
         Overlap: LLM-based urban spatial understanding
         Contact: not found — suggest ResearchGate

  ⚠️ #3  Fair Geolocation from Humanitarian Docs (56%, 2026)
         Method matches but domain is humanitarian response, not street view
         → Is this relevant to your work?

  (dropped 3: healthcare domain, existing co-author, similarity < 40%)
```

You only need to weigh in on the flagged papers.

**Phase 3 — Email writing**

For each confirmed paper, Claude reads both abstracts and writes a complete, specific email — no placeholders:

```
To: zhang@mit.edu
Subject: Related work you might want to cite

Hi Zhang,

I came across your preprint "VertiCue-Bench: Diagnosing Whether MLLMs Use Height
Cues" — both papers apply vision-language models to street-level geospatial reasoning,
and your height-cue evaluation framework directly complements my geographic extraction work.

My paper "StreetViewLLM" introduces a chain-of-thought prompting approach for extracting
structured geographic information from street-view imagery. You might want to consider
citing it before you finalize your preprint.
DOI: https://doi.org/10.xxxxx

Happy to share a PDF or preprint link.

Best,
Jasper Li
```

You review each one and confirm before anything gets sent.

**Phase 4 — Send**

If Gmail is connected, the skill sends confirmed emails one by one. Maximum 5 per session to avoid spam filters. After sending:

```
First batch sent (3/5):
  ✅ zhang@mit.edu — VertiCue-Bench
  ✅ kim@kaist.ac.kr — Urban VLM
  ✅ (via ResearchGate) — Mapping Humanities

Suggest waiting 2 weeks before the next batch.
```

**Phase 5 — Follow-up (any future session)**

Come back later, run `/niw-citation` again, and say "update progress" or "got a reply from #2." The skill restores your tracker, updates statuses, and surfaces follow-up reminders for emails with no reply after 2 weeks.

```
Status: 5 sent / 2 replied / 1 citation added. Net gain: +1 citation.
```

---

## Script-only mode

If you prefer running scripts directly without Claude Code:

```bash
# Step 1: crawl candidate papers from OpenAlex
python scripts/crawl_openalex.py --profile data/profiles/<id>.json
# → data/profiles/<id>_candidates.json

# Step 2: rank by semantic similarity (per-paper groups)
python scripts/search_similar.py --candidates data/profiles/<id>_candidates.json
# → data/output/<id>_similar.json

# Step 3: generate outreach tracker
python scripts/find_citations.py --similar data/output/<id>_similar.json
# → data/output/<id>_outreach.md

# Step 4: find author contact info
python scripts/find_contacts.py --similar data/output/<id>_similar.json
# → data/output/<id>_contacts.json

# Step 5: initialize progress tracker
python scripts/find_citations.py --progress \
  --similar data/output/<id>_similar.json \
  --contacts data/output/<id>_contacts.json
# → data/output/<id>_progress.md
```

Or run everything in one command:
```bash
python scripts/find_citations.py --name "Your Full Name"
```

The email drafts in `_outreach.md` will have `[describe the specific overlap here]` placeholders — fill those in manually, or use the skill to have Claude write them.

---

## Scoring

Final score = **similarity × 60% + receptiveness × 40%**

**Similarity (0–100%):** cosine similarity between the candidate paper and your matched paper's embedding. Computed per paper — each of your papers searches independently, results grouped by source.

**Receptiveness (0–60 pts):**

| Factor | Points | Why |
|--------|--------|-----|
| Preprint | +30 | Still editable — zero cost to add a citation |
| Published 2025 | +15 | May still revise |
| Published 2024 | +10 | Recently active |
| ≤ 3 authors | +10 | More responsive to individual emails |
| Has DOI | +5 | Findable paper |

Papers with similarity < 50% have their receptiveness score dampened by 80%, so a preprint bonus can't lift an irrelevant paper above a relevant one.

**Prioritize:** similarity > 60% AND type = preprint.

---

## Models

| Model | Quality | Cost | Setup |
|-------|---------|------|-------|
| `local` (default) | Good | Free | `pip install sentence-transformers` |
| `openai` | Better | ~$0.01/1k papers | `export OPENAI_API_KEY=...` |

```bash
python scripts/find_citations.py --profile ... --model openai
```

Embeddings are cached in `data/cache/` — re-running is instant.

---

## Works best with

**[begging-for-recommenders](https://github.com/Jasper0122/begging-for-niw-eb1a-recommenders)** — the companion tool. They share the same profile JSON format.

- `begging-for-recommenders`: finds people who already cited you → ask for letters
- `begging-for-citations`: finds people who should cite you → grow citation count

---

## Dependencies

```
pyalex>=0.21               # OpenAlex API
sentence-transformers>=2.7  # local embeddings (free)
scikit-learn>=1.3           # cosine similarity
numpy>=1.24
requests>=2.28              # contact lookup
# optional: openai>=1.0    # better embeddings
```

No API keys required for default mode.

---

## Known limits

- **Abstract coverage**: OpenAlex has abstracts for ~70% of papers. Papers without abstracts are embedded from title only — lower match quality.
- **Topic breadth**: OpenAlex topics can be broad; initial candidate pool may include adjacent fields. The similarity filter handles most of this.
- **Contact coverage**: emails are found for roughly 20–40% of authors via OpenAlex homepage scraping and ORCID. ResearchGate is a reliable fallback for the rest.
- **Threshold tuning**: default `--min-sim 0.45` is a good starting point. Raise to `0.50` for a tighter list, lower to `0.35` if your field is underrepresented on OpenAlex.

---

*Your citation count is partially a discovery problem.*
*These papers exist. They're related. They just haven't found you.*
