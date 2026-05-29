"""
Take a citation snapshot for the case-demo tracker.

Fetches current Google Scholar counts from the profile JSON (most recent run)
and OpenAlex counts live, then writes a dated snapshot to case-demo/snapshots/.

Run:
  python case-demo/snapshot.py

Or after re-running fetch_profile.py to refresh Scholar data:
  python ../begging-for-niw-eb1a-recommenders/scripts/fetch_profile.py \
    --scholar-url "https://scholar.google.com/citations?user=XbCCGC4AAAAJ"
  python case-demo/snapshot.py
"""

import json
from datetime import date
from pathlib import Path

from pyalex import Authors, Works

# ── config ────────────────────────────────────────────────────────────────────
SCHOLAR_ID   = "XbCCGC4AAAAJ"
OPENALEX_ID  = "https://openalex.org/A5104329948"
AUTHOR_NAME  = "Zongrong (Jasper) Li"
INSTITUTION  = "Texas A&M University"
SCHOLAR_URL  = f"https://scholar.google.com/citations?user={SCHOLAR_ID}"

PROFILE_PATH = Path(__file__).parent.parent.parent / \
               "recommender_finder" / "data" / "profiles" / f"{SCHOLAR_ID}.json"
OUT_DIR      = Path(__file__).parent / "snapshots"
OUT_DIR.mkdir(exist_ok=True)

today = date.today().isoformat()


def load_scholar_papers() -> list[dict]:
    if not PROFILE_PATH.exists():
        print(f"  Profile not found at {PROFILE_PATH}")
        print("  Run fetch_profile.py first for up-to-date Scholar counts.")
        return []
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return profile.get("papers", [])


def fetch_openalex() -> dict:
    try:
        a = Authors()[OPENALEX_ID]
        stats = a.get("summary_stats") or {}
        works = Works().filter(
            author={"id": OPENALEX_ID.split("/")[-1]}
        ).select(["title", "cited_by_count", "publication_year"]).get()
        return {
            "citations":   a.get("cited_by_count", 0),
            "h_index":     stats.get("h_index", "—"),
            "i10_index":   stats.get("i10_index", "—"),
            "works_count": a.get("works_count", 0),
            "papers":      sorted(works,
                                  key=lambda x: x.get("cited_by_count", 0),
                                  reverse=True),
        }
    except Exception as e:
        print(f"  OpenAlex fetch failed: {e}")
        return {}


def compute_scholar_stats(papers: list[dict]) -> dict:
    cites = sorted([p.get("citations", 0) for p in papers], reverse=True)
    total = sum(cites)
    h     = sum(1 for i, c in enumerate(cites, 1) if c >= i)
    i10   = sum(1 for c in cites if c >= 10)
    return {"citations": total, "h_index": h, "i10_index": i10,
            "works_count": len(papers)}


def write_snapshot(scholar_papers: list[dict], oa: dict) -> Path:
    gs = compute_scholar_stats(scholar_papers)

    rows = "\n".join(
        f"| {p.get('citations', 0)} | {p.get('year', '—')} "
        f"| {(p.get('title') or 'Untitled')[:80]} |"
        for p in sorted(scholar_papers,
                        key=lambda x: x.get("citations", 0), reverse=True)
    )

    content = f"""# Citation Snapshot — {today}

**Author:** {AUTHOR_NAME}
**Institution:** {INSTITUTION}
**Google Scholar:** {SCHOLAR_URL}
**OpenAlex:** {OPENALEX_ID}

---

## Summary

| Metric | Google Scholar | OpenAlex |
|--------|---------------|---------|
| Total citations | {gs['citations']} | {oa.get('citations', '—')} |
| h-index | {gs['h_index']} | {oa.get('h_index', '—')} |
| i10-index | {gs['i10_index']} | {oa.get('i10_index', '—')} |
| Works indexed | {gs['works_count']} | {oa.get('works_count', '—')} |

> Google Scholar is the primary metric for NIW evidence. OpenAlex is tracked as a secondary, API-accessible source.

---

## Per-paper breakdown (Google Scholar)

| Citations | Year | Title |
|-----------|------|-------|
{rows}

**Total: {gs['citations']}**

---

## Outreach status at this snapshot

_(fill in manually after checking progress tracker)_

- Emails sent via this tool:
- Unique authors contacted:
- Citations added from outreach:

---

## Notes

_(optional: add context about what changed since last snapshot)_
"""

    out = OUT_DIR / f"{today}.md"
    out.write_text(content, encoding="utf-8")
    return out


def main():
    print(f"\nTaking citation snapshot for {AUTHOR_NAME}...")

    print("  Loading Scholar data from profile JSON...")
    scholar_papers = load_scholar_papers()

    print("  Fetching OpenAlex stats...")
    oa = fetch_openalex()

    out = write_snapshot(scholar_papers, oa)
    print(f"\nSnapshot saved --> {out}")

    gs = compute_scholar_stats(scholar_papers)
    print(f"\n  Google Scholar: {gs['citations']} citations, h={gs['h_index']}, i10={gs['i10_index']}")
    if oa:
        print(f"  OpenAlex:       {oa.get('citations')} citations, h={oa.get('h_index')}, i10={oa.get('i10_index')}")


if __name__ == "__main__":
    main()
