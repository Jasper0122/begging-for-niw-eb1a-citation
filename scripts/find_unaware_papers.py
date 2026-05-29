"""
Find related papers that haven't cited your work yet.
Targets preprints and very recent papers — still editable, most receptive.

Strategy:
  1. Load your papers + resolve their OpenAlex topics
  2. Search for recent papers on those topics
  3. Remove papers that already cite you
  4. Score: preprint > recency > topic overlap > small team
  5. Generate outreach email draft for each

Output: data/output/{author_id}_outreach.md

Run:
  python scripts/find_unaware_papers.py \
    --profile ../begging-for-niw-eb1a-recommenders/data/profiles/<id>.json

  Or use standalone:
  python scripts/find_unaware_papers.py \
    --name "Your Name" --keywords "urban sensing, street view, GeoAI"
"""

import argparse
import json
import re
import time
from pathlib import Path

import pyalex
from pyalex import Works, Authors

pyalex.config.email = "zongrong@tamu.edu"

DATA_DIR   = Path(__file__).parent.parent / "data" / "profiles"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── LOAD PAPERS ─────────────────────────────────────────────────────────────

def load_from_profile(profile_path: str) -> tuple[list[dict], str, str]:
    data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    return data["papers"], data["author_id"], data["author"]["name"]


def load_from_name(name: str) -> tuple[list[dict], str, str]:
    from pyalex import Authors as OAAuthors
    print(f"  Searching OpenAlex for: {name}")
    results = OAAuthors().search(name).get(per_page=5)
    if not results:
        raise ValueError(f"No author found: {name}")
    best = sorted(results, key=lambda x: x.get("cited_by_count", 0), reverse=True)[0]
    author_id = best["id"].split("/")[-1]
    works = (
        Works()
        .filter(author={"id": best["id"]})
        .sort(cited_by_count="desc")
        .get(per_page=10)
    )
    papers = []
    for w in works:
        doi = w.get("doi", "")
        if doi:
            doi = doi.replace("https://doi.org/", "")
        papers.append({
            "title":       w.get("title", ""),
            "doi":         doi,
            "citations":   w.get("cited_by_count", 0),
            "openalex_id": w.get("id", ""),
        })
    return papers, author_id, best.get("display_name", name)


# ─── TOPIC DISCOVERY ─────────────────────────────────────────────────────────

def resolve_paper_topics(papers: list[dict]) -> dict[str, str]:
    """Returns {topic_id: topic_name} from all papers combined."""
    topics = {}
    for p in papers:
        oa_id = p.get("openalex_id", "")

        # Try DOI first
        if not oa_id and p.get("doi"):
            doi = p["doi"].replace("https://doi.org/", "").strip()
            results = Works().filter(doi=doi).select(["id", "topics"]).get()
            if results:
                oa_id = results[0]["id"]
                p["openalex_id"] = oa_id
                for t in results[0].get("topics", [])[:5]:
                    topics[t["id"]] = t.get("display_name", "")

        # Try openalex_id directly
        elif oa_id:
            try:
                work = Works()[oa_id.split("/")[-1]]
                for t in work.get("topics", [])[:5]:
                    topics[t["id"]] = t.get("display_name", "")
            except Exception:
                pass

        # Fallback: title search
        if not oa_id and p.get("title"):
            try:
                results = Works().search(p["title"]).select(["id", "title", "topics"]).get(per_page=3)
                for r in results:
                    if p["title"].lower()[:40] in (r.get("title") or "").lower():
                        p["openalex_id"] = r["id"]
                        for t in r.get("topics", [])[:5]:
                            topics[t["id"]] = t.get("display_name", "")
                        print(f"    Found via title: {r.get('title','')[:60]}")
                        break
            except Exception:
                pass

        time.sleep(0.3)
    return topics


def topics_from_keywords(keywords: str) -> dict[str, str]:
    """Fallback: search OpenAlex concepts by keyword."""
    topics = {}
    for kw in keywords.split(","):
        kw = kw.strip()
        try:
            results = Works().search(kw).select(["id", "topics"]).get(per_page=10)
            for r in results:
                for t in r.get("topics", [])[:3]:
                    topics[t["id"]] = t.get("display_name", "")
        except Exception:
            pass
        time.sleep(0.3)
    return topics


# ─── FIND ALREADY CITING ─────────────────────────────────────────────────────

def get_already_citing(my_oa_ids: list[str]) -> set[str]:
    citing = set(my_oa_ids)
    for oa_id in my_oa_ids:
        try:
            results = (
                Works()
                .filter(cites=oa_id)
                .select(["id"])
                .get(per_page=200)
            )
            for r in results:
                citing.add(r.get("id", ""))
            time.sleep(0.3)
        except Exception:
            pass
    return citing


# ─── FIND RELATED ────────────────────────────────────────────────────────────

def find_related_recent(topic_id: str, exclude: set, limit: int = 50) -> list[dict]:
    try:
        results = (
            Works()
            .filter(topics={"id": topic_id}, publication_year=">2023")
            .sort(publication_date="desc")
            .select(["id", "title", "authorships", "publication_year",
                     "type", "doi", "topics", "primary_location"])
            .get(per_page=limit)
        )
        return [r for r in results if r.get("id") not in exclude]
    except Exception:
        return []


def extract_keywords(papers: list[dict]) -> set[str]:
    """Pull domain-specific terms from the applicant's paper titles.
    Filters generic academic words so only field-specific terms remain."""
    generic = {
        # function words
        "a","an","the","of","in","for","on","with","and","or","to","from",
        "via","using","based","through","by","is","are","into","its","this",
        "that","their","our","we","as","at","be","been","has","have","can",
        # generic academic nouns / verbs
        "study","analysis","approach","method","model","framework","system",
        "data","dataset","results","case","review","survey","evaluation",
        "assessment","integration","evaluation","application","technique",
        "performance","effect","impact","role","use","used","large","scale",
        "multi","new","novel","deep","learning","based","driven","towards",
        "toward","high","low","real","world","work","paper","research",
        "proposed","development","construction","constructing","extracting",
        "powering","bridging","integrating","arbitration","characterization",
        "cost","natural","enhanced","conceptual","evaluation","language",
        # too-broad domain words that cause cross-field noise
        "built","environment","earth","observation","disparities","coverage",
        "economic","disaster","disasters","databases","database","across",
        "regions","cities","global","spatial","temporal","network","networks",
        "detection","prediction","estimation","mapping","classification",
        # too-common 4-letter words
        "from","with","that","this","have","more","also","been","some",
    }
    keywords = set()
    for p in papers:
        title = (p.get("title") or "").lower()
        # only keep words ≥ 6 chars that aren't in the generic list
        for word in re.findall(r"[a-z][a-z0-9\-]{5,}", title):
            if word not in generic:
                keywords.add(word)
    return keywords


def keyword_overlap(paper: dict, my_keywords: set) -> int:
    """Count how many of the applicant's keywords appear in the candidate title."""
    title = (paper.get("title") or "").lower()
    return sum(1 for kw in my_keywords if kw in title)


# ─── SCORING ─────────────────────────────────────────────────────────────────

def score_paper(paper: dict, my_topic_ids: set, my_keywords: set) -> float:
    s = 0

    # Must have keyword relevance — hard filter
    kw_hits = keyword_overlap(paper, my_keywords)
    if kw_hits == 0:
        return 0.0   # irrelevant, exclude

    # Keyword relevance bonus
    s += min(kw_hits * 10, 30)

    # Topic overlap
    paper_topic_ids = {t.get("id", "") for t in paper.get("topics", [])}
    overlap = len(my_topic_ids & paper_topic_ids)
    if overlap == 0:
        return 0.0   # different field, exclude
    s += min(overlap * 6, 18)

    # Preprint = most editable
    if paper.get("type") == "preprint":
        s += 25

    # Recency
    year = paper.get("publication_year", 0)
    if year >= 2025:
        s += 15
    elif year >= 2024:
        s += 10
    elif year >= 2023:
        s += 5

    # Has DOI
    if paper.get("doi"):
        s += 5

    # Small team = more responsive
    n_authors = len(paper.get("authorships", []))
    if n_authors <= 3:
        s += 8
    elif n_authors <= 6:
        s += 4

    return round(s, 1)


# ─── EMAIL GENERATION ────────────────────────────────────────────────────────

def draft_email(paper: dict, my_papers: list[dict], author_name: str) -> str:
    title = paper.get("title", "your paper") or "your paper"
    authors = paper.get("authorships", [])
    first_author = (
        authors[0].get("author", {}).get("display_name", "there")
        if authors else "there"
    )
    last_name = first_author.split()[-1] if first_author != "there" else "there"

    my_paper = sorted(my_papers, key=lambda x: x.get("citations", 0), reverse=True)[0]
    my_title = my_paper.get("title", "my recent work") or "my recent work"
    my_doi   = my_paper.get("doi", "")
    doi_line = f"\nDOI: https://doi.org/{my_doi}" if my_doi else ""

    is_preprint = paper.get("type") == "preprint"
    timing = "before you finalize it" if is_preprint else "for any future revision"

    return (
        f'Subject: Related work you might want to cite\n\n'
        f'Hi {last_name},\n\n'
        f'I came across your {"preprint" if is_preprint else "paper"} '
        f'"{title[:80]}" — it\'s closely related to work I\'ve done on '
        f'[describe overlap in 1 sentence].\n\n'
        f'My paper "{my_title[:80]}" addresses [shared problem / method / dataset]. '
        f'You might want to consider citing it {timing}.{doi_line}\n\n'
        f'Happy to share a preprint or full PDF if useful.\n\n'
        f'Best,\n{author_name}'
    )


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run(papers: list[dict], author_id: str, author_name: str,
        keywords: str = "", max_outreach: int = 20) -> list[dict]:

    print(f"\nCitation Outreach Finder")
    print(f"Author: {author_name}  |  {len(papers)} papers\n")

    # Resolve topics
    print("Resolving topics from your papers...")
    my_topics = resolve_paper_topics(papers)
    if not my_topics and keywords:
        print("  No topics found via papers — falling back to keywords")
        my_topics = topics_from_keywords(keywords)

    if not my_topics:
        print("  No topics found. Pass --keywords to continue.")
        return []

    print(f"  Topics: {', '.join(list(my_topics.values())[:5])}")

    # Already citing
    my_oa_ids = [p["openalex_id"] for p in papers if p.get("openalex_id")]
    print(f"\nFinding papers that already cite you ({len(my_oa_ids)} papers)...")
    already_citing = get_already_citing(my_oa_ids)
    print(f"  {len(already_citing)} papers excluded (already cite you)")

    # Find related
    candidates: dict[str, dict] = {}
    for topic_id in list(my_topics.keys())[:4]:
        name = my_topics[topic_id]
        print(f"\nSearching: {name[:55]}...")
        found = find_related_recent(topic_id, already_citing)
        print(f"  {len(found)} related papers not yet citing you")
        for p in found:
            pid = p.get("id", "")
            if pid and pid not in candidates:
                candidates[pid] = p
        time.sleep(0.5)

    if not candidates:
        print("\nNo candidates found. Try broader keywords.")
        return []

    # Deduplicate by normalized title (catches same paper with different versions)
    seen_titles: set[str] = set()
    deduped: dict[str, dict] = {}
    for pid, p in candidates.items():
        norm_title = re.sub(r"\s+", " ", (p.get("title") or "").lower().strip())[:80]
        if norm_title and norm_title not in seen_titles:
            seen_titles.add(norm_title)
            deduped[pid] = p
    candidates = deduped

    my_topic_ids = set(my_topics.keys())
    my_keywords  = extract_keywords(papers)
    print(f"\nKeywords from your titles: {sorted(my_keywords)[:15]}")

    candidate_list = list(candidates.values())
    for c in candidate_list:
        c["score"] = score_paper(c, my_topic_ids, my_keywords)

    # Filter out zero-score (irrelevant) papers
    candidate_list = [c for c in candidate_list if c["score"] > 0]
    candidate_list.sort(key=lambda x: x["score"], reverse=True)
    top = candidate_list[:max_outreach]

    print(f"\nTotal: {len(candidate_list)} candidates → top {len(top)}")

    # Build tracker markdown
    lines = [
        f"# Citation Outreach Tracker — {author_name}\n",
        f"_Top {len(top)} related papers not yet citing your work_\n",
        f"_Topics: {', '.join(list(my_topics.values())[:3])}_\n",
        "---\n",
    ]
    for i, c in enumerate(top, 1):
        is_preprint = c.get("type") == "preprint"
        flag = "**PREPRINT**" if is_preprint else "Published"
        authors = c.get("authorships", [])
        first_author = (
            authors[0].get("author", {}).get("display_name", "—")
            if authors else "—"
        )
        lines += [
            f"## {i}. {(c.get('title') or 'Untitled')[:80]}",
            f"**Score:** {c['score']}  **Type:** {flag}  "
            f"**Year:** {c.get('publication_year','?')}  "
            f"**Authors:** {len(authors)}",
            f"**First author:** {first_author}",
            f"**DOI:** {c.get('doi','—')}",
            "",
            "<details>",
            "<summary>Email draft</summary>",
            "",
            "```",
            draft_email(c, papers, author_name),
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
    print(f"\nSaved --> {out}")

    preprints = sum(1 for c in top if c.get("type") == "preprint")
    print(f"Breakdown: {preprints} preprints | {len(top)-preprints} published")
    print("\nTop 5:")
    for c in top[:5]:
        flag = "[PRE]" if c.get("type") == "preprint" else "[pub]"
        print(f"  {c['score']:5.1f} {flag}  {(c.get('title') or '')[:60]}")

    return top


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--profile",  help="Profile JSON from begging-for-recommenders")
    group.add_argument("--name",     help="Author name (OpenAlex search)")

    parser.add_argument("--keywords", default="",
                        help="Fallback keywords if topic detection fails, comma-separated")
    parser.add_argument("--max", type=int, default=20,
                        help="Max outreach targets (default 20)")
    args = parser.parse_args()

    if args.profile:
        papers, author_id, author_name = load_from_profile(args.profile)
    else:
        papers, author_id, author_name = load_from_name(args.name)

    run(papers, author_id, author_name, args.keywords, args.max)
