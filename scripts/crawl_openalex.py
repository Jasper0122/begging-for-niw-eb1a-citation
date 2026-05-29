"""
Step 1: Crawl candidate papers from OpenAlex.

Given your profile (papers), this script:
  1. Resolves OpenAlex topics from your papers
  2. Finds papers that already cite you (to exclude)
  3. Fetches recent related papers with title + abstract
  4. Saves to data/profiles/{author_id}_candidates.json

Run:
  python scripts/crawl_openalex.py \
    --profile ../begging-for-niw-eb1a-recommenders/data/profiles/<id>.json

  python scripts/crawl_openalex.py --name "Your Name"
"""

import argparse
import json
import re
import time
from pathlib import Path

import pyalex
from pyalex import Works, Authors

pyalex.config.email = "zongrong@tamu.edu"

DATA_DIR = Path(__file__).parent.parent / "data" / "profiles"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def reconstruct_abstract(inverted_index: dict) -> str:
    """Rebuild plain-text abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


def load_profile(profile_path: str) -> tuple[list[dict], str, str]:
    data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    return data["papers"], data["author_id"], data["author"]["name"]


def load_from_name(name: str) -> tuple[list[dict], str, str]:
    print(f"  Searching OpenAlex for: {name}")
    results = Authors().search(name).get(per_page=5)
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
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        papers.append({
            "title":       w.get("title", ""),
            "doi":         doi,
            "citations":   w.get("cited_by_count", 0),
            "openalex_id": w.get("id", ""),
        })
    return papers, author_id, best.get("display_name", name)


def resolve_topics_and_ids(papers: list[dict]) -> tuple[dict[str, str], list[str]]:
    """Returns ({topic_id: name}, [resolved_oa_ids])."""
    topics: dict[str, str] = {}
    oa_ids: list[str] = []

    for p in papers:
        oa_id = p.get("openalex_id", "")

        if not oa_id and p.get("doi"):
            doi = p["doi"].replace("https://doi.org/", "").strip()
            results = Works().filter(doi=doi).select(["id", "topics"]).get()
            if results:
                oa_id = results[0]["id"]
                p["openalex_id"] = oa_id
                for t in results[0].get("topics", [])[:5]:
                    topics[t["id"]] = t.get("display_name", "")

        if not oa_id and p.get("title"):
            results = Works().search(p["title"]).select(["id", "title", "topics"]).get(per_page=3)
            for r in results:
                if p["title"].lower()[:40] in (r.get("title") or "").lower():
                    oa_id = r["id"]
                    p["openalex_id"] = oa_id
                    for t in r.get("topics", [])[:5]:
                        topics[t["id"]] = t.get("display_name", "")
                    print(f"    Resolved: {r.get('title','')[:60]}")
                    break

        if oa_id and oa_id not in oa_ids:
            oa_ids.append(oa_id)
            if not topics:
                try:
                    work = Works()[oa_id.split("/")[-1]]
                    for t in work.get("topics", [])[:5]:
                        topics[t["id"]] = t.get("display_name", "")
                except Exception:
                    pass

        time.sleep(0.3)

    return topics, oa_ids


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
                if r.get("id"):
                    citing.add(r["id"])
            time.sleep(0.3)
        except Exception:
            pass
    return citing


def fetch_candidates(topic_ids: list[str], exclude: set[str],
                     per_topic: int = 60) -> list[dict]:
    """Fetch recent papers per topic with title + abstract."""
    seen_titles: set[str] = set()
    candidates: list[dict] = []

    for topic_id in topic_ids:
        try:
            results = (
                Works()
                .filter(topics={"id": topic_id}, publication_year=">2023")
                .sort(publication_date="desc")
                .select([
                    "id", "title", "authorships", "publication_year",
                    "type", "doi", "topics", "abstract_inverted_index",
                ])
                .get(per_page=per_topic)
            )
        except Exception:
            results = []

        added = 0
        for r in results:
            pid = r.get("id", "")
            if not pid or pid in exclude:
                continue
            title = (r.get("title") or "").strip()
            norm  = title.lower()[:80]
            if norm in seen_titles:
                continue
            seen_titles.add(norm)

            abstract = reconstruct_abstract(r.get("abstract_inverted_index") or {})
            candidates.append({
                "id":           pid,
                "title":        title,
                "abstract":     abstract,
                "type":         r.get("type", ""),
                "doi":          (r.get("doi") or "").replace("https://doi.org/", ""),
                "year":         r.get("publication_year", 0),
                "authorships":  r.get("authorships", []),
                "topics":       r.get("topics", []),
            })
            added += 1

        print(f"  {topic_id.split('/')[-1][:40]:40}  +{added} papers")
        time.sleep(0.5)

    return candidates


def run(profile_path: str = None, name: str = None,
        per_topic: int = 60) -> dict:

    if profile_path:
        papers, author_id, author_name = load_profile(profile_path)
    else:
        papers, author_id, author_name = load_from_name(name)

    print(f"\nCrawl — {author_name}  ({len(papers)} papers)")

    print("\nResolving topics...")
    topics, my_oa_ids = resolve_topics_and_ids(papers)
    if not topics:
        raise ValueError("Could not resolve any topics. Check paper titles or DOIs.")
    print(f"  Topics: {list(topics.values())[:5]}")

    print(f"\nFinding papers already citing you ({len(my_oa_ids)} resolved)...")
    exclude = get_already_citing(my_oa_ids)
    print(f"  Excluding {len(exclude)} papers")

    print(f"\nFetching candidate papers (top {min(4, len(topics))} topics)...")
    candidates = fetch_candidates(list(topics.keys())[:4], exclude, per_topic)
    print(f"\nTotal unique candidates: {len(candidates)}")

    out = DATA_DIR / f"{author_id}_candidates.json"
    out.write_text(
        json.dumps({
            "author_id":    author_id,
            "author_name":  author_name,
            "my_papers":    papers,
            "topics":       topics,
            "candidates":   candidates,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved --> {out}")
    return {"author_id": author_id, "candidates_path": str(out)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--profile", help="Profile JSON from begging-for-recommenders")
    group.add_argument("--name",    help="Author name (OpenAlex search)")
    parser.add_argument("--per-topic", type=int, default=60)
    args = parser.parse_args()
    run(args.profile, args.name, args.per_topic)
