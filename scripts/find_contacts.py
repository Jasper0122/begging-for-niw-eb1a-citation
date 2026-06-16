"""
Step 2.5: Find contact info for candidate paper authors.

Priority of WHO to contact:  corresponding author(s) -> first author -> others.
Priority of HOW to find an email, per author:
  1. ORCID public API (raw_orcid in the authorship payload)
  2. OpenAlex author profile -> homepage_url -> scrape
  3. DOI landing page (publisher prints the corresponding-author email)
  4. Web search (DuckDuckGo) for "<name> <institution> email", then
     cross-check each scraped email against the author's name / institution
     so we don't grab the wrong person's address.

Run:
  python scripts/find_contacts.py --similar data/output/<id>_similar.json
"""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote_plus, unquote

import requests
from pyalex import Authors

TIMEOUT = 8        # per-HTTP-request timeout (s)
WORKERS = 6        # papers processed in parallel

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36"}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.(?:edu|com|org|net|ac\.\w+|edu\.\w+|io|cn|uk|de|fr|au|ca|nl|se|ch|jp|kr|it|es|br|in|sg)\b", re.I)
NOISE    = {"noreply", "support", "info", "contact", "admin", "help", "no-reply",
            "webmaster", "privacy", "security", "postmaster", "editor", "journals",
            "permissions", "customerservice", "office", "enquiries", "sales",
            "marketing", "press", "media", "example", "email", "your"}
STOP_INST = {"university", "universidad", "universidade", "institute", "institut",
             "college", "department", "school", "national", "science", "sciences",
             "technology", "center", "centre", "research", "state", "laboratory",
             "faculty", "academy", "polytechnic", "federal", "engineering"}


def _p(s: str) -> None:
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))


def _deobfuscate(text: str) -> str:
    """Turn 'name [at] host [dot] edu' style obfuscation into real emails."""
    t = text
    t = re.sub(r"\s*[\[\(\{]?\s*(?:at|@)\s*[\]\)\}]?\s*", "@", t, flags=re.I)
    t = re.sub(r"\s*[\[\(\{]?\s*dot\s*[\]\)\}]?\s*", ".", t, flags=re.I)
    return t


def _clean_emails(raw) -> list:
    out = []
    for e in raw:
        e = e.strip().strip(".")
        local = e.split("@")[0].lower()
        if local not in NOISE and len(local) > 1 and e not in out:
            out.append(e)
    return out


def _find_emails(text: str) -> list:
    found = EMAIL_RE.findall(text)
    found += EMAIL_RE.findall(_deobfuscate(text))
    # findall returns the group (TLD) — re-extract full matches
    full = re.findall(r"[\w.+-]+@[\w.-]+\.\w{2,}", text)
    full += re.findall(r"[\w.+-]+@[\w.-]+\.\w{2,}", _deobfuscate(text))
    return _clean_emails(full)


def _name_tokens(name: str) -> list:
    return [t for t in re.split(r"[^a-z]+", (name or "").lower()) if len(t) >= 3]


def _inst_tokens(inst: str) -> list:
    return [t for t in re.split(r"[^a-z]+", (inst or "").lower())
            if len(t) >= 4 and t not in STOP_INST]


def _email_score(email: str, name: str, institution: str) -> int:
    """How confident are we this email belongs to THIS author? Higher = better."""
    local, _, domain = email.lower().partition("@")
    score = 0
    if any(t in local for t in _name_tokens(name)):
        score += 3
    if any(t in domain for t in _inst_tokens(institution)):
        score += 2
    if re.search(r"\.(edu|ac)\b|\.edu\.|\.ac\.", domain):
        score += 1
    return score


def _best_email(emails: list, name: str, institution: str, min_score: int) -> str:
    best, best_s = "", -1
    for e in emails:
        s = _email_score(e, name, institution)
        if s > best_s:
            best, best_s = e, s
    return best if best_s >= min_score else ""


# ---------------------------------------------------------------- per-method

def _orcid_email(orcid_url: str) -> str:
    orcid_id = (orcid_url or "").rstrip("/").split("/")[-1]
    if not re.match(r"\d{4}-\d{4}-\d{4}-\w{4}", orcid_id):
        return ""
    try:
        r = requests.get(f"https://pub.orcid.org/v3.0/{orcid_id}/person",
                         timeout=TIMEOUT, headers={"Accept": "application/json"})
        if r.status_code == 200:
            emails = (r.json().get("emails") or {}).get("email") or []
            for e in emails:
                if e.get("email"):
                    return e["email"]
    except Exception:
        pass
    return ""


def _openalex_homepage(author_oa_id: str) -> dict:
    try:
        a = Authors()[author_oa_id]
        return {"homepage": a.get("homepage_url") or "", "orcid": a.get("orcid") or ""}
    except Exception:
        return {}


def _scrape_page(url: str, name: str, institution: str, min_score: int) -> str:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=BROWSER)
        if r.status_code == 200:
            emails = _find_emails(r.text)
            if emails:
                # homepage is author-specific: accept best even at score 0 if single
                hit = _best_email(emails, name, institution, min_score)
                if hit:
                    return hit
                if min_score == 0 and len(emails) == 1:
                    return emails[0]
    except Exception:
        pass
    return ""


def _doi_landing_email(doi: str, authors: list) -> tuple:
    """Fetch the publisher page once; match scraped emails against top authors."""
    if not doi:
        return "", ""
    url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=BROWSER)
        if r.status_code != 200:
            return "", ""
        emails = _find_emails(r.text)
        if not emails:
            return "", ""
        best, best_s, who = "", 0, ""
        for a in authors:
            nm = (a.get("author") or {}).get("display_name", "")
            inst = a.get("_inst", "")
            for e in emails:
                s = _email_score(e, nm, inst)
                if s > best_s:
                    best, best_s, who = e, s, nm
        if best_s >= 3:                      # require a name match on a journal page
            return best, who
    except Exception:
        pass
    return "", ""


def _ddg_search(query: str) -> tuple:
    """Return (page_html, [result_urls]) from DuckDuckGo HTML endpoint."""
    try:
        r = requests.get("https://html.duckduckgo.com/html/",
                         params={"q": query}, timeout=TIMEOUT, headers=BROWSER)
        if r.status_code != 200:
            return "", []
        html = r.text
        urls = []
        for m in re.findall(r'uddg=([^&"]+)', html):
            u = unquote(m)
            if u.startswith("http") and u not in urls:
                urls.append(u)
        return html, urls[:3]
    except Exception:
        return "", []


def _web_search_email(name: str, institution: str) -> str:
    """Search the web for the author's email and cross-check the match."""
    # DISABLED 2026-06-15: the DuckDuckGo HTML endpoint hangs / times out in the
    # cloud sandbox and contributes ~0 emails in practice (every hit comes from
    # ORCID or the DOI landing page). Skipping it keeps the run fast and stops
    # the whole scheduled routine from stalling on outbound web search.
    return ""
    q = f'"{name}" {institution} email'.strip()
    html, urls = _ddg_search(q)
    if not html and not urls:
        return ""
    # 1) emails directly in the search-result snippets (need a name/inst match)
    hit = _best_email(_find_emails(html), name, institution, min_score=3)
    if hit:
        return hit
    # 2) open the single top result page and look there (cost control)
    for u in urls[:1]:
        if not re.search(r"researchgate|semanticscholar|linkedin\.com/pulse", u):
            email = _scrape_page(u, name, institution, min_score=3)
            if email:
                return email
    return ""


# ---------------------------------------------------------------- orchestrate

def _ordered_authors(paper: dict) -> list:
    auths = paper.get("authorships") or []
    corr  = [a for a in auths if a.get("is_corresponding")]
    first = [a for a in auths if a.get("author_position") == "first"]
    ordered, seen = [], set()
    for a in corr + first + auths:
        aid = (a.get("author") or {}).get("id", "") or (a.get("author") or {}).get("display_name", "")
        if aid and aid not in seen:
            seen.add(aid)
            # stash a best-guess institution string on the authorship
            inst = ""
            insts = a.get("institutions") or []
            if insts:
                inst = insts[0].get("display_name", "")
            elif a.get("raw_affiliation_strings"):
                inst = a["raw_affiliation_strings"][0]
            a["_inst"] = inst
            ordered.append(a)
    return ordered


def find_contact(paper: dict) -> dict:
    authors = _ordered_authors(paper)
    if not authors:
        return {}

    primary = authors[0]
    p_info  = primary.get("author") or {}
    result = {
        "author_name": p_info.get("display_name", ""),
        "institution": primary.get("_inst", ""),
        "email": "", "homepage": "", "orcid": primary.get("raw_orcid") or "",
        "source": "",
    }

    # Phase 1 — cheap, reliable: ORCID + OpenAlex homepage, in author priority order
    for a in authors[:5]:
        info  = a.get("author") or {}
        name  = info.get("display_name", "")
        inst  = a.get("_inst", "")
        orcid = a.get("raw_orcid") or info.get("orcid") or ""
        oa_id = info.get("id", "")

        if orcid:
            em = _orcid_email(orcid)
            if em:
                result.update(author_name=name, institution=inst, orcid=orcid,
                              email=em, source="orcid")
                return result
        if oa_id:
            prof = _openalex_homepage(oa_id)
            if prof.get("homepage"):
                result["homepage"] = prof["homepage"]
                em = _scrape_page(prof["homepage"], name, inst, min_score=0)
                if em:
                    result.update(author_name=name, institution=inst,
                                  email=em, source="homepage")
                    return result

    # Phase 2 — DOI landing page (corresponding email is usually printed there)
    em, who = _doi_landing_email(paper.get("doi") or "", authors[:3])
    if em:
        result.update(author_name=who or result["author_name"], email=em,
                      source="doi_page")
        return result

    # Phase 3 — web search + cross-check, for corresponding then first author
    for a in authors[:2]:
        info = a.get("author") or {}
        name = info.get("display_name", "")
        inst = a.get("_inst", "")
        if not name:
            continue
        em = _web_search_email(name, inst)
        if em:
            result.update(author_name=name, institution=inst,
                          email=em, source="websearch")
            return result
        time.sleep(0.3)

    return result


def run(similar_path: str) -> None:
    data        = json.loads(Path(similar_path).read_text(encoding="utf-8"))
    author_id   = data["author_id"]
    author_name = data["author_name"]
    groups      = data.get("groups") or []
    if not groups and data.get("results"):
        groups = [{"my_paper": {}, "results": data["results"]}]

    seen_ids, all_papers = set(), []
    for g in groups:
        for p in g["results"]:
            pid = p.get("id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_papers.append(p)

    n = len(all_papers)
    print(f"\nFinding contacts — {author_name}  ({n} papers, {WORKERS} workers)")
    contacts, found = {}, 0
    by_source = {}

    def _one(paper):
        pid = paper.get("id", "")
        try:
            return pid, find_contact(paper)
        except Exception as e:
            return pid, {"_error": str(e)}

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(_one, p): p for p in all_papers}
        for fut in as_completed(futures):
            pid, contact = fut.result()
            done += 1
            contacts[pid] = contact
            title = (futures[fut].get("title") or "")[:50]
            if contact.get("email"):
                found += 1
                src = contact.get("source", "?")
                by_source[src] = by_source.get(src, 0) + 1
                _p(f"  [{done:3}/{n}] {title} -> {contact['email']}  ({src})")
            else:
                _p(f"  [{done:3}/{n}] {title}")

    out = OUTPUT_DIR / f"{author_id}_contacts.json"
    out.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved --> {out}")
    print(f"Emails found: {found}/{len(all_papers)}   by source: {by_source}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--similar", required=True)
    args = parser.parse_args()
    run(args.similar)
