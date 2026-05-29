"""
Step 2.5: Find contact info for candidate paper authors.

Tries (in order):
  1. OpenAlex author profile → homepage_url
  2. Scrape homepage for email pattern
  3. arXiv abstract page (preprints)

Run:
  python scripts/find_contacts.py --similar data/output/<id>_similar.json
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests
from pyalex import Authors

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _p(s: str) -> None:
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.(?:edu|com|org|ac\.\w+|io|cn|uk|de|fr)", re.I)
NOISE    = {"noreply", "support", "info", "contact", "admin", "help", "no-reply",
            "webmaster", "privacy", "security", "postmaster"}


def _clean_emails(raw: list[str]) -> list[str]:
    out = []
    for e in raw:
        local = e.split("@")[0].lower()
        if local not in NOISE and len(local) > 2:
            out.append(e)
    return out


def _fetch_openalex_profile(author_oa_id: str) -> dict:
    try:
        # pyalex accepts full OpenAlex URL or short ID
        a = Authors()[author_oa_id]
        return {
            "homepage": a.get("homepage_url") or "",
            "orcid":    a.get("orcid") or "",
        }
    except Exception:
        return {}


def _orcid_email(orcid_url: str) -> str:
    """Fetch ORCID public API for email (only works if author made it public)."""
    orcid_id = orcid_url.rstrip("/").split("/")[-1]
    if not re.match(r"\d{4}-\d{4}-\d{4}-\w{4}", orcid_id):
        return ""
    try:
        url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
        r   = requests.get(url, timeout=8,
                           headers={"Accept": "application/json"})
        if r.status_code == 200:
            data  = r.json()
            emails = (data.get("emails") or {}).get("email") or []
            for e in emails:
                val = e.get("email", "")
                if val:
                    return val
    except Exception:
        pass
    return ""


def _scrape_email(url: str) -> str:
    try:
        r = requests.get(url, timeout=9,
                         headers={"User-Agent": "Mozilla/5.0 (research outreach bot)"})
        if r.status_code == 200:
            found = _clean_emails(EMAIL_RE.findall(r.text))
            return found[0] if found else ""
    except Exception:
        pass
    return ""


def _arxiv_id(paper: dict) -> str:
    doi = paper.get("doi") or ""
    if "10.48550" in doi:
        m = re.search(r"arxiv[./](\d{4}\.\d{4,5})", doi, re.I)
        if m:
            return m.group(1)
    lp = (paper.get("primary_location") or {}).get("landing_page_url") or ""
    m  = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", lp, re.I)
    return m.group(1) if m else ""


def _arxiv_email(arxiv_id: str) -> str:
    url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        r = requests.get(url, timeout=9)
        if r.status_code == 200:
            found = _clean_emails(EMAIL_RE.findall(r.text))
            return found[0] if found else ""
    except Exception:
        pass
    return ""


def find_contact(paper: dict) -> dict:
    authorships = paper.get("authorships") or []
    if not authorships:
        return {}

    first        = authorships[0]
    author_info  = first.get("author") or {}
    institutions = first.get("institutions") or [{}]
    # raw_orcid is already in the authorship payload — no extra API call needed
    raw_orcid    = first.get("raw_orcid") or author_info.get("orcid") or ""

    result = {
        "author_name":  author_info.get("display_name", ""),
        "institution":  institutions[0].get("display_name", ""),
        "email":        "",
        "homepage":     "",
        "orcid":        raw_orcid,
        "source":       "",
    }

    author_oa_id = author_info.get("id", "")   # full URL e.g. https://openalex.org/A...

    # 1. OpenAlex profile → homepage → scrape email
    if author_oa_id:
        profile = _fetch_openalex_profile(author_oa_id)
        if profile.get("homepage"):
            result["homepage"] = profile["homepage"]
            if not raw_orcid and profile.get("orcid"):
                result["orcid"] = profile["orcid"]
            email = _scrape_email(profile["homepage"])
            if email:
                result["email"]  = email
                result["source"] = "homepage"
                return result

    # 2. ORCID public API (only if author made email public)
    if raw_orcid and not result["email"]:
        email = _orcid_email(raw_orcid)
        if email:
            result["email"]  = email
            result["source"] = "orcid"
            return result

    # 3. arXiv abstract page
    arxiv = _arxiv_id(paper)
    if arxiv and not result["email"]:
        email = _arxiv_email(arxiv)
        if email:
            result["email"]  = email
            result["source"] = "arxiv"

    return result


def run(similar_path: str) -> None:
    data        = json.loads(Path(similar_path).read_text(encoding="utf-8"))
    author_id   = data["author_id"]
    author_name = data["author_name"]
    groups      = data.get("groups") or []

    # Back-compat: flat results
    if not groups and data.get("results"):
        groups = [{"my_paper": {}, "results": data["results"]}]

    # Deduplicate by paper id
    seen_ids: set[str] = set()
    all_papers = []
    for g in groups:
        for p in g["results"]:
            pid = p.get("id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_papers.append(p)

    print(f"\nFinding contacts — {author_name}  ({len(all_papers)} papers)")

    contacts: dict[str, dict] = {}
    found_count = 0

    for i, paper in enumerate(all_papers, 1):
        pid   = paper.get("id", "")
        title = (paper.get("title") or "")[:55]
        try:
            _p(f"  [{i:2}/{len(all_papers)}] {title}...")
            contact = find_contact(paper)
            contacts[pid] = contact

            if contact.get("email"):
                found_count += 1
                _p(f"         -> {contact['email']}  ({contact['source']})")
            elif contact.get("homepage"):
                _p(f"         -> homepage only: {contact['homepage'][:55]}")
            else:
                _p(f"         -> not found")
        except Exception as e:
            _p(f"         -> error: {e}")
            contacts[pid] = {}

        time.sleep(0.4)   # be polite to OpenAlex

    out = OUTPUT_DIR / f"{author_id}_contacts.json"
    out.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved --> {out}")
    print(f"Emails found: {found_count}/{len(all_papers)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--similar", required=True,
                        help="Path to _similar.json from search_similar.py")
    args = parser.parse_args()
    run(args.similar)
