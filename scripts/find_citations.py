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


def draft_email(paper: dict, my_papers: list[dict], author_name: str) -> str:
    title   = (paper.get("title") or "your paper")
    authors = paper.get("authorships", [])
    first   = (
        authors[0].get("author", {}).get("display_name", "there")
        if authors else "there"
    )
    last_name = first.split()[-1] if first != "there" else "there"

    my_paper  = sorted(my_papers, key=lambda x: x.get("citations", 0), reverse=True)[0]
    my_title  = my_paper.get("title", "my recent work") or "my recent work"
    my_doi    = my_paper.get("doi", "")
    doi_line  = f"\nDOI: https://doi.org/{my_doi}" if my_doi else ""

    is_pre   = paper.get("type") == "preprint"
    timing   = "before you finalize it" if is_pre else "for any future revision"

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


def generate_tracker(results: list[dict], my_papers: list[dict],
                     author_id: str, author_name: str) -> Path:
    for r in results:
        r["combined_score"] = combined_score(r)
    results.sort(key=lambda x: x["combined_score"], reverse=True)

    lines = [
        f"# Citation Outreach Tracker — {author_name}\n",
        f"_Top {len(results)} semantically similar papers not yet citing your work_\n",
        f"_Ranked by: semantic similarity (60%) + receptiveness / preprint status (40%)_\n",
        "---\n",
    ]

    for i, r in enumerate(results, 1):
        is_pre  = r.get("type") == "preprint"
        flag    = "**PREPRINT**" if is_pre else "Published"
        authors = r.get("authorships", [])
        first   = (
            authors[0].get("author", {}).get("display_name", "—")
            if authors else "—"
        )
        sim_pct = int(r.get("similarity", 0) * 100)

        lines += [
            f"## {i}. {(r.get('title') or 'Untitled')[:80]}",
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
            draft_email(r, my_papers, author_name),
            "```",
            "",
            "</details>",
            "",
            "- [ ] Reviewed relevance  - [ ] Email sent  - [ ] Citation added",
            "",
            "---\n",
        ]

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
    my_papers   = data["my_papers"]
    results     = data["results"]

    print(f"\nGenerating tracker for {author_name} ({len(results)} candidates)...")
    out = generate_tracker(results, my_papers, author_id, author_name)
    print(f"Saved --> {out}")

    # Summary
    preprints = sum(1 for r in results if r.get("type") == "preprint")
    print(f"\nBreakdown: {preprints} preprints | {len(results)-preprints} published")
    print("\nTop 5:")
    for r in sorted(results, key=lambda x: x.get("combined_score", 0), reverse=True)[:5]:
        flag = "[PRE]" if r.get("type") == "preprint" else "[pub]"
        sim  = int(r.get("similarity", 0) * 100)
        print(f"  {r.get('combined_score',0):5.1f}  {flag}  {sim}%  {(r.get('title') or '')[:55]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--profile", help="Run full pipeline from profile JSON")
    mode.add_argument("--name",    help="Run full pipeline from author name")
    mode.add_argument("--similar", help="Skip crawl/search, generate tracker only")

    parser.add_argument("--model",   default="local", choices=["local", "openai"])
    parser.add_argument("--top",     type=int,   default=20)
    parser.add_argument("--min-sim", type=float, default=0.25)
    args = parser.parse_args()

    if args.similar:
        run_tracker(args.similar)
    else:
        run_pipeline(args.profile, args.name, args.model, args.top, args.min_sim)
