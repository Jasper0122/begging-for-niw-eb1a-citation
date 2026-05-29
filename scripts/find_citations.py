"""
Step 3: Generate outreach tracker from similarity results.

Reads the similar.json from search_similar.py,
scores candidates by receptiveness (preprint, recency, team size),
and writes a tracker markdown with email drafts.

Run:
  python scripts/find_citations.py \
    --similar data/output/<id>_similar.json

Or run the full pipeline in one command:
  python scripts/find_citations.py \
    --profile ../begging-for-recommenders/data/profiles/<id>.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = Path(__file__).parent.parent / "data" / "profiles"


def score_receptiveness(paper: dict) -> float:
    """Score by how likely the author will add a citation."""
    s = 0
    if paper.get("type") == "preprint":
        s += 30                    # still editable
    year = paper.get("year", 0)
    if year >= 2025:
        s += 15
    elif year >= 2024:
        s += 10
    n = len(paper.get("authorships", []))
    if n <= 3:
        s += 10                    # small team = more responsive
    elif n <= 6:
        s += 5
    if paper.get("doi"):
        s += 5                     # findable paper
    return round(s, 1)


def combined_score(paper: dict) -> float:
    sim  = paper.get("similarity", 0) * 100    # 0–100
    recv = score_receptiveness(paper)           # 0–60
    # Dampen receptiveness for low-similarity papers so
    # a preprint bonus can't lift an irrelevant paper above a relevant one
    if paper.get("similarity", 0) < 0.50:
        recv *= 0.2
    return round(sim * 0.6 + recv * 0.4, 1)


def draft_email(paper: dict, matched_paper: dict, author_name: str) -> str:
    title   = (paper.get("title") or "your paper")
    authors = paper.get("authorships", [])
    first   = (
        authors[0].get("author", {}).get("display_name", "there")
        if authors else "there"
    )
    last_name = first.split()[-1] if first != "there" else "there"

    my_title = matched_paper.get("title", "my recent work") or "my recent work"
    my_doi   = matched_paper.get("doi", "")
    doi_line = f"\nDOI: https://doi.org/{my_doi}" if my_doi else ""

    is_pre  = paper.get("type") == "preprint"
    timing  = "before you finalize it" if is_pre else "for any future revision"

    return (
        f"Subject: Related work you might want to cite\n\n"
        f"Hi {last_name},\n\n"
        f'I came across your {"preprint" if is_pre else "paper"} '
        f'"{title[:80]}" — it touches on [describe the specific overlap here].\n\n'
        f'My paper "{my_title[:80]}" addresses this through [your approach/method]. '
        f"You might want to consider citing it {timing}.{doi_line}\n\n"
        f"Happy to share a PDF or preprint link.\n\n"
        f"Best,\n{author_name}"
    )


def generate_tracker(groups: list[dict], author_id: str, author_name: str) -> Path:
    # Score and sort each group independently
    for g in groups:
        for r in g["results"]:
            r["combined_score"] = combined_score(r)
        g["results"].sort(key=lambda x: x["combined_score"], reverse=True)

    total = sum(len(g["results"]) for g in groups)
    lines = [
        f"# Citation Outreach Tracker — {author_name}\n",
        f"_Grouped by your paper · {total} candidates total_\n",
        f"_Ranked by: semantic similarity (60%) + receptiveness / preprint status (40%)_\n",
        "---\n",
    ]

    entry_num = 1
    for g in groups:
        mp       = g["my_paper"]
        mp_title = (mp.get("title") or "Untitled")[:80]
        lines += [
            f"# Based on: _{mp_title}_\n",
        ]

        for r in g["results"]:
            is_pre  = r.get("type") == "preprint"
            flag    = "**PREPRINT**" if is_pre else "Published"
            authors = r.get("authorships", [])
            first   = (
                authors[0].get("author", {}).get("display_name", "—")
                if authors else "—"
            )
            sim_pct = int(r.get("similarity", 0) * 100)

            lines += [
                f"## {entry_num}. {(r.get('title') or 'Untitled')[:80]}",
                f"**Score:** {r['combined_score']}  "
                f"**Similarity:** {sim_pct}%  "
                f"**Type:** {flag}  "
                f"**Year:** {r.get('year','?')}  "
                f"**Authors:** {len(authors)}",
                f"**First author:** {first}",
                f"**DOI:** {r.get('doi','—')}",
                f"**OpenAlex:** {r.get('id','—')}",
            ]
            if r.get("abstract"):
                lines.append(f"\n> {r['abstract'][:200]}...")
            lines += [
                "",
                "<details>",
                "<summary>Email draft</summary>",
                "",
                "```",
                draft_email(r, r.get("matched_paper", mp), author_name),
                "```",
                "",
                "</details>",
                "",
                "- [ ] Reviewed relevance  - [ ] Email sent  - [ ] Citation added",
                "",
                "---\n",
            ]
            entry_num += 1

        lines.append("\n")

    out = OUTPUT_DIR / f"{author_id}_outreach.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_pipeline(profile_path: str = None, name: str = None,
                 model: str = "local", top_k: int = 20,
                 min_sim: float = 0.25) -> None:
    scripts = Path(__file__).parent

    # Step 1: crawl
    crawl_args = [sys.executable, str(scripts / "crawl_openalex.py")]
    if profile_path:
        crawl_args += ["--profile", profile_path]
    else:
        crawl_args += ["--name", name]
    subprocess.run(crawl_args, check=True)

    # Determine author_id from crawl output
    candidates_files = sorted(DATA_DIR.glob("*_candidates.json"),
                               key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates_files:
        raise FileNotFoundError("No candidates JSON found after crawl.")
    candidates_path = str(candidates_files[0])

    # Step 2: search
    search_args = [
        sys.executable, str(scripts / "search_similar.py"),
        "--candidates", candidates_path,
        "--top",     str(top_k),
        "--min-sim", str(min_sim),
        "--model",   model,
    ]
    subprocess.run(search_args, check=True)

    # Step 3: tracker (from similar.json)
    similar_files = sorted(OUTPUT_DIR.glob("*_similar.json"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
    if not similar_files:
        raise FileNotFoundError("No similar JSON found after search.")
    run_tracker(str(similar_files[0]))


def run_tracker(similar_path: str) -> None:
    data        = json.loads(Path(similar_path).read_text(encoding="utf-8"))
    author_id   = data["author_id"]
    author_name = data["author_name"]
    groups      = data.get("groups") or []

    # Back-compat: old format had flat "results" list
    if not groups and data.get("results"):
        my_papers = data.get("my_papers", [])
        best_mp   = sorted(my_papers, key=lambda x: x.get("citations", 0), reverse=True)
        best_mp   = best_mp[0] if best_mp else {}
        groups    = [{"my_paper": best_mp, "results": data["results"]}]

    total = sum(len(g["results"]) for g in groups)
    print(f"\nGenerating tracker for {author_name} ({total} candidates across {len(groups)} groups)...")
    out = generate_tracker(groups, author_id, author_name)
    print(f"Saved --> {out}")

    all_results = [r for g in groups for r in g["results"]]
    preprints   = sum(1 for r in all_results if r.get("type") == "preprint")
    print(f"\nBreakdown: {preprints} preprints | {total-preprints} published")
    print("\nTop 5 (across all groups):")
    for r in sorted(all_results, key=lambda x: x.get("combined_score", 0), reverse=True)[:5]:
        flag = "[PRE]" if r.get("type") == "preprint" else "[pub]"
        sim  = int(r.get("similarity", 0) * 100)
        mp   = (r.get("matched_paper") or {}).get("title", "")[:30]
        print(f"  {r.get('combined_score',0):5.1f}  {flag}  {sim}%  {(r.get('title') or '')[:45]}  ← {mp}")


def init_progress(similar_path: str, contacts_path: str = None) -> Path:
    """
    Create a fresh _progress.md from similar.json + optional contacts.json.
    Skill calls this once after Phase 2 judgment to seed the tracker.
    """
    data        = json.loads(Path(similar_path).read_text(encoding="utf-8"))
    author_id   = data["author_id"]
    author_name = data["author_name"]
    groups      = data.get("groups") or []

    contacts: dict = {}
    if contacts_path and Path(contacts_path).exists():
        contacts = json.loads(Path(contacts_path).read_text(encoding="utf-8"))

    rows = []
    n    = 1
    for g in groups:
        mp_title = (g["my_paper"].get("title") or "")[:40]
        for r in g["results"]:
            pid     = r.get("id", "")
            title   = (r.get("title") or "Untitled")[:45]
            c       = contacts.get(pid, {})
            contact = c.get("email") or (c.get("homepage") or "")[:40] or "—"
            rows.append(
                f"| {n} | {title} | {mp_title} | {contact} | — | — | — |"
            )
            n += 1

    lines = [
        f"# Outreach Progress — {author_name}\n",
        f"_Last updated: (skill will fill in date)_\n",
        "| # | Title | Based on | Contact | Sent | Replied | Cited |",
        "|---|-------|----------|---------|------|---------|-------|",
        *rows,
    ]
    out = OUTPUT_DIR / f"{author_id}_progress.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Progress tracker --> {out}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--profile", help="Run full pipeline from profile JSON")
    mode.add_argument("--name",    help="Run full pipeline from author name")
    mode.add_argument("--similar", help="Skip crawl/search, generate tracker only")

    parser.add_argument("--model",    default="local", choices=["local", "openai"])
    parser.add_argument("--top",      type=int,   default=20)
    parser.add_argument("--min-sim",  type=float, default=0.25)
    parser.add_argument("--progress", action="store_true",
                        help="Init progress tracker (needs --similar and optionally --contacts)")
    parser.add_argument("--contacts", help="Path to _contacts.json for progress init")
    args = parser.parse_args()

    if args.progress:
        if not args.similar:
            parser.error("--progress requires --similar")
        init_progress(args.similar, args.contacts)
    elif args.similar:
        run_tracker(args.similar)
    else:
        run_pipeline(args.profile, args.name, args.model, args.top, args.min_sim)
