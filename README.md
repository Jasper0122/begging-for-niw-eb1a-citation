<h2 align="center">begging-for-citations</h2>

<p align="center">
NIW / EB-1A green card toolkit — find the papers that should be citing you, and ask them to.
</p>

<p align="center">
Your citation count doesn't just reflect impact. It's evidence USCIS weighs.<br>
Some of those missing citations aren't gaps in your work — they're papers that haven't found you yet.<br>
This finds them.
</p>

<p align="center">
<a href="#"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
&nbsp;
<a href="#"><img src="https://img.shields.io/badge/works%20for-NIW%20%7C%20EB--1A-green" alt="NIW EB-1A"></a>
</p>

---

## 🧠 What this is

Most researchers grow citations the same way:

> Wait. Hope. Submit to more venues. Repeat.

Passive. Slow. And it ignores a whole class of papers that are building on your ideas right now, this month, and just haven't cited you yet — because they never crossed paths.

**This tool finds those papers before they're finalized.**

It scans recent publications in your field, ranks them by semantic similarity to each of your papers, scores authors by how likely they are to add a citation, finds their contact info, and outputs personalized outreach emails — one per paper, ready to send.

Preprints are the best targets. Still editable. Zero revision friction. One email can add a citation.

---

## 👤 Who this is for

| You have... | What happens |
|---|---|
| Google Scholar profile | Auto-fetches your papers and topics via OpenAlex |
| Author name only | Falls back to name search on OpenAlex |
| Profile JSON from begging-for-recommenders | Reuse it directly — same format |

Works best for researchers with 3+ papers. The more papers you have, the more independently matched groups you get.

---

## ⚡ Quickstart

```bash
git clone https://github.com/Jasper0122/begging-for-niw-eb1a-citation.git
cd begging-for-niw-eb1a-citation
pip install -r requirements.txt
```

**Run the full pipeline:**
```bash
# From your Google Scholar profile:
python scripts/find_citations.py \
  --profile ../begging-for-niw-eb1a-recommenders/data/profiles/<id>.json

# Or by name:
python scripts/find_citations.py --name "Your Full Name"
```

Output lands in `data/output/` — a ranked tracker grouped by your papers, with email drafts per candidate.

---

## 📋 What the output looks like

```markdown
# Based on: "StreetViewLLM: Extracting geographic information..."

## 1. VertiCue-Bench: Diagnosing Whether MLLMs Use Height Cues
**Score:** 51.4  **Similarity:** 59%  **Type:** PREPRINT  **Year:** 2025  **Authors:** 3
**First author:** Zhang Wei
**DOI:** 10.48550/arxiv.2506.xxxxx

> Proposes a benchmark for diagnosing spatial reasoning in multimodal LLMs...

<details>
<summary>Email draft</summary>

Subject: Related work you might want to cite

Hi Zhang,

I came across your preprint "VertiCue-Bench" — [overlap sentence].
My paper "StreetViewLLM" [your contribution]. You might want to consider
citing it before you finalize it.

</details>

- [ ] Reviewed relevance  - [ ] Email sent  - [ ] Citation added
```

One file. Work through it top to bottom. Check boxes as you go.

---

## ⚖️ How it differs from doing it manually

| Manual | This |
|---|---|
| Google Scholar → related articles → skim titles | Embedding-based semantic search across 200+ recent papers |
| Same query for all your papers | Each paper searches independently — no dilution from unrelated topics |
| No signal on who to contact first | Scored: preprint > recent published > small team |
| Guess at emails or give up | Tries OpenAlex homepage, ORCID public API, arXiv abstract page |
| Write emails from scratch | Personalized draft per paper, overlap sentence filled in |

---

## 🏆 Scoring

Final score = **similarity × 60% + receptiveness × 40%**

**Similarity (0–100%):** cosine distance between the candidate paper and the specific paper of yours it matched. Per-paper search — each of your papers finds its own pool independently.

**Receptiveness (0–60 pts):**

| Factor | Points | Why |
|---|---|---|
| Preprint | +30 | Still editable — zero friction to add a citation |
| Published 2025 | +15 | Authors still active, may revise |
| Published 2024 | +10 | Recently active |
| ≤ 3 authors | +10 | Smaller team = more responsive |
| Has DOI | +5 | Findable paper |

Papers with similarity < 50% have their receptiveness score dampened — a preprint bonus alone can't lift an irrelevant paper above a relevant one.

**Prioritize:** similarity > 60% AND type = preprint.

---

## 📦 Install & run

```bash
git clone https://github.com/Jasper0122/begging-for-niw-eb1a-citation.git
cd begging-for-niw-eb1a-citation
pip install -r requirements.txt
```

No API keys required for default mode. Optional: `OPENAI_API_KEY` for better embeddings.

---

## 🤖 Claude Skill (recommended)

If you use [Claude Code](https://claude.ai/code), run `/niw-citation` instead of the scripts directly.

**Setup:**
1. Open this folder in Claude Code
2. Run `/mcp` → select **claude.ai Gmail** → complete OAuth _(one-time, optional)_
3. Run `/niw-citation`

**What the skill adds on top of the scripts:**

| Scripts | Skill |
|---|---|
| Outputs all candidates | Reads every abstract, judges relevance, drops irrelevant ones |
| Placeholder in email: `[describe overlap]` | Writes the specific overlap sentence from the abstracts |
| Lists results | Decides which 5 to send first |
| No sending | Sends via Gmail with per-email confirmation |
| Static tracker | Updates sent / replied / cited across sessions |

**What a session looks like:**

```
> /niw-citation

Found your profile. Running pipeline...
Screened 12 papers → keeping 7

Group: "StreetViewLLM"
  ✅ #1  VertiCue-Bench (59%, PREPRINT) — zhang@mit.edu ✓
  ✅ #2  Urban Mobility Synthesis (51%) — not found, suggest ResearchGate
  ⚠️ #3  Geolocation from Humanitarian Docs (56%) — method matches but
          domain is humanitarian response. Relevant to your work?

Flagged 1 paper for your review. Writing emails for the confirmed ones now...
```

Gmail not connected? The skill still works — you copy the finalized emails manually.

---

## 🤔 Why not just use ChatGPT / Google Scholar alerts?

Scholar alerts tell you when new papers cite you — after the fact, months later, when the paper is already published.

This runs the search before papers are finalized, targeting preprints and recent papers still in revision. ChatGPT can't search the academic literature; this queries OpenAlex (200M+ works) with embedding-based matching specific to your papers.

---

## 🗂️ Structure

```
scripts/
  crawl_openalex.py     fetch your papers + candidate papers from OpenAlex
  search_similar.py     per-paper embedding search, grouped results
  find_contacts.py      author email lookup (OpenAlex, ORCID, arXiv)
  find_citations.py     score + tracker + progress init

data/
  profiles/   raw API cache (gitignored)
  output/     tracker, progress, contacts (gitignored)
  cache/      embedding cache — re-runs are instant (gitignored)

.claude/
  commands/niw-citation.md   Claude skill
```

---

## ⚠️ Known limits

- **Abstract coverage**: OpenAlex has abstracts for ~70% of papers. No abstract = title-only embedding, lower match quality.
- **Contact coverage**: emails found for ~20–40% of authors. ResearchGate is a reliable fallback for the rest.
- **Threshold tuning**: default `--min-sim 0.45`. Raise to `0.50` for a tighter list; lower to `0.35` if your field is underrepresented on OpenAlex.

---

## Works best with

**[begging-for-recommenders](https://github.com/Jasper0122/begging-for-niw-eb1a-recommenders)** — the companion tool. Shares the same profile JSON.

- `begging-for-recommenders`: people who already cited you → ask for recommendation letters
- `begging-for-citations`: papers that should cite you → grow your citation count

---

*The missing citations aren't missing because your work isn't relevant.*
*They're missing because those authors haven't found you yet.*
