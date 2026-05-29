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
  Rank by cosine similarity
         │
         ▼
  Score by receptiveness         ← find_citations.py
  (preprint > recent > small team)
         │
         ▼
  Outreach tracker + email drafts
  data/output/{id}_outreach.md
```

**Why embeddings, not keywords:**
Keyword search misses "vision-language model for urban sensing" when your paper says "multimodal LLM for street-view analysis." Embedding models understand both mean the same thing. You get real matches, not accidental ones.

---

## Quickstart

```bash
git clone https://github.com/Jasper0122/begging-for-niw-eb1a-citation.git
cd begging-for-niw-eb1a-citation
pip install -r requirements.txt
```

**Run the full pipeline:**

```bash
# If you have a profile JSON from begging-for-recommenders:
python scripts/find_citations.py \
  --profile ../begging-for-niw-eb1a-recommenders/data/profiles/<id>.json

# Or by author name:
python scripts/find_citations.py --name "Your Full Name"
```

Output: `data/output/{id}_outreach.md` — ranked tracker with email drafts.

---

## Claude Skill + Gmail setup (recommended)

This repo ships with a `/niw-citation` skill for [Claude Code](https://claude.ai/code). The skill runs all scripts for you, judges relevance, writes personalized emails, and — if you connect Gmail — sends them directly.

**Step 1 — Install Claude Code**

Download from [claude.ai/code](https://claude.ai/code) and open this project folder.

**Step 2 — Connect Gmail (optional but recommended)**

In Claude Code, run:
```
/mcp
```
Select **claude.ai Gmail** and complete the OAuth flow. This gives the skill permission to send emails on your behalf.

You only do this once — the auth persists across sessions.

**Step 3 — Run the skill**

```
/niw-citation
```

The skill will:
1. Run all scripts automatically
2. Read every abstract and judge whether each paper is genuinely relevant
3. Write a specific overlap sentence for each email (no generic placeholders)
4. Send emails via Gmail if connected, or show you the final drafts to copy-paste
5. Track sent / replied / cited status in `data/output/<id>_progress.md`

> Without Gmail connected, the skill still does everything except sending — you copy the final emails manually.

---

## Step by step

```bash
# Step 1: crawl candidate papers from OpenAlex
python scripts/crawl_openalex.py --profile data/profiles/<id>.json
# → data/profiles/<id>_candidates.json

# Step 2: rank by semantic similarity (embeddings)
python scripts/search_similar.py --candidates data/profiles/<id>_candidates.json
# → data/output/<id>_similar.json

# Step 3: generate outreach tracker
python scripts/find_citations.py --similar data/output/<id>_similar.json
# → data/output/<id>_outreach.md
```

Re-run Step 3 any time to regenerate the tracker without re-crawling.
Re-run Step 2 with `--min-sim 0.30` to tighten the similarity threshold.

---

## Scoring

Final score = **similarity × 60% + receptiveness × 40%**

**Similarity (0–100%):** cosine similarity between candidate paper embedding and your papers' mean embedding. Higher = more semantically related.

**Receptiveness (0–60 pts):**

| Factor | Points | Why |
|--------|--------|-----|
| Preprint | +30 | Still editable — zero cost to add a citation |
| Published 2025 | +15 | May still revise |
| Published 2024 | +10 | Recently active |
| ≤ 3 authors | +10 | More responsive to individual emails |
| Has DOI | +5 | Findable paper |

**Prioritize:** similarity > 60% AND type = preprint.

---

## Models

| Model | Quality | Cost | Setup |
|-------|---------|------|-------|
| `local` (default) | Good | Free | `pip install sentence-transformers` |
| `openai` | Better | ~$0.01/1k papers | `export OPENAI_API_KEY=...` |

```bash
# Use OpenAI embeddings
python scripts/find_citations.py --profile ... --model openai
```

Embeddings are cached in `data/cache/` — re-running is instant.

---

## Claude Skill (optional)

If you use [Claude Code](https://claude.ai/code), there's a `/niw-citation` skill in `.claude/commands/` that:
1. Runs the pipeline for you
2. Presents results with abstracts
3. Fills in the specific overlap sentence in each email draft using Claude
4. Outputs a finalized tracker

The skill's key value-add: Claude reads both papers and writes a *specific* overlap sentence — not a generic template.

---

## Works best with

**[begging-for-recommenders](https://github.com/Jasper0122/begging-for-niw-eb1a-recommenders)** — the companion tool. They share the same profile JSON format.

- `begging-for-recommenders`: finds people who already cited you → ask for letters
- `begging-for-citations`: finds people who should cite you → grow citation count

---

## Dependencies

```
pyalex>=0.21              # OpenAlex API
sentence-transformers>=2.7 # local embeddings (free)
scikit-learn>=1.3          # cosine similarity
numpy>=1.24
# optional: openai>=1.0   # better embeddings
```

No API keys required for default mode.

---

## Known limits

- **Abstract coverage**: OpenAlex has abstracts for ~70% of papers. Papers without abstracts are embedded from title only — lower match quality.
- **Topic breadth**: OpenAlex topics can be broad; initial candidate pool may include adjacent fields. The similarity filter handles most of this.
- **Threshold tuning**: default `--min-sim 0.25` is intentionally loose. If you get too many irrelevant results, try `--min-sim 0.35`.

---

*Your citation count is partially a discovery problem.*
*These papers exist. They're related. They just haven't found you.*
