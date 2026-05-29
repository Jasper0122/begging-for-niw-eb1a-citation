# NIW Citation Outreach Skill

Helps NIW/EB-1A applicants grow citation count by finding related papers that haven't cited their work yet — and drafting personalized outreach emails.

## Working directory
`C:\Users\zongr\Documents\NIW&EB1A\begging-for-niw-eb1a-citation\`

---

## Step 1 — Get the applicant's papers

Ask the user which input they have:

**(A) Profile JSON already exists** (from begging-for-recommenders):
```
data/profiles/<id>.json
```
Use it directly — no need to re-fetch papers.

**(B) Author name only:**
```bash
python scripts/crawl_openalex.py --name "Full Name"
```

**(C) Profile URL (Google Scholar):**
Tell the user to first run begging-for-recommenders:
```bash
python ../begging-for-niw-eb1a-recommenders/scripts/fetch_profile.py \
  --scholar-url "https://scholar.google.com/citations?user=XXXX"
```
Then come back and use `--profile`.

---

## Step 2 — Crawl + Search

**Full pipeline (recommended):**
```bash
python scripts/find_citations.py --profile data/profiles/<id>.json
```

**Or step by step:**
```bash
# Step 1: fetch candidates from OpenAlex
python scripts/crawl_openalex.py --profile data/profiles/<id>.json

# Step 2: rank by semantic similarity
python scripts/search_similar.py --candidates data/profiles/<id>_candidates.json

# Step 3: generate tracker
python scripts/find_citations.py --similar data/output/<id>_similar.json
```

**Use OpenAI embeddings for better quality (optional):**
```bash
python scripts/find_citations.py --profile data/profiles/<id>.json --model openai
```

---

## Step 3 — Present results

Read `data/output/{author_id}_outreach.md` and present the top results as a table:

| # | Similarity | Type | Title | Year | First Author |
|---|-----------|------|-------|------|--------------|
| 1 | 72% | PREPRINT | ... | 2025 | Zhang Wei |
| 2 | 68% | Published | ... | 2024 | Kim J. |

For each result, show:
- Similarity % (semantic closeness to their work)
- Whether it's a preprint (highest priority — still editable)
- Abstract snippet (so they can judge relevance)

Ask: **"Which of these are relevant to your work? I'll fill in the email drafts."**

---

## Step 4 — Fill in email drafts

For each paper the user confirms as relevant:

1. Read the candidate paper's abstract
2. Read the applicant's most relevant paper abstract
3. Write a specific 1-sentence overlap description, e.g.:
   > "Both papers apply vision-language models to street-level urban scene understanding"

Replace the `[describe the specific overlap here]` placeholder in the email draft with this sentence.

Also replace `[your approach/method]` with a specific description of the applicant's contribution.

**Good overlap sentence:** Specific, concrete, explains WHY citation makes sense.
**Bad overlap sentence:** "Both papers are about AI" / "Similar topic area"

Show the completed email. Ask if they want to adjust tone or length.

---

## Step 5 — Output tracker

Save finalized emails back to `data/output/{author_id}_outreach.md`.

Print a send-order recommendation:
1. **Preprints first** — highest acceptance rate, zero revision friction
2. **Then recent published** (2024–2025) — authors still active, possible revision
3. **Skip papers > 2 years old** unless very high similarity

Timeline tip: send in batches of 5, not all at once. Wait 2 weeks before following up.

---

## Key judgment calls

**Relevance check:** If the abstract clearly describes a different application domain (e.g., healthcare, finance) despite high similarity score — skip it. Embedding models sometimes confuse methodological overlap with actual citation relevance.

**Independence check:** If the first author appears in the applicant's existing citations or co-author list — skip. The goal is people who don't know them yet.

**Email tone:** Keep it collegial, not transactional. The email says "you might want to cite" — not "please cite me." Researchers respond to genuine intellectual connection, not requests.
