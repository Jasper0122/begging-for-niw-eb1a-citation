"""
Step 2: Embedding-based semantic similarity search.
Adapted from github.com/gyj155/SearchPaperByEmbedding

Finds candidates most semantically similar to your own papers.
Uses title + abstract embeddings — much more accurate than keyword matching.

Models:
  local  — sentence-transformers/all-MiniLM-L6-v2  (free, no API key)
  openai — text-embedding-3-large                   (better, ~$0.01/1k papers)

Run:
  python scripts/search_similar.py \
    --candidates data/profiles/<id>_candidates.json \
    --top 20

  python scripts/search_similar.py \
    --candidates data/profiles/<id>_candidates.json \
    --model openai --top 20
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PaperSearcher:
    def __init__(self, model_type: str = "local", api_key: str = None):
        self.model_type  = model_type
        self.model_name  = ""
        self.embeddings  = None
        self._papers_ref = None

        if model_type == "openai":
            from openai import OpenAI
            self.client     = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.model_name = "text-embedding-3-large"
        else:
            from sentence_transformers import SentenceTransformer
            print("  Loading sentence-transformers (all-MiniLM-L6-v2)...")
            self.model      = SentenceTransformer("all-MiniLM-L6-v2")
            self.model_name = "all-MiniLM-L6-v2"

    # ── text helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _paper_text(paper: dict) -> str:
        parts = []
        if paper.get("title"):
            parts.append(f"Title: {paper['title']}")
        if paper.get("abstract"):
            parts.append(f"Abstract: {paper['abstract'][:500]}")
        topics = paper.get("topics", [])
        if topics:
            kws = ", ".join(t.get("display_name", "") for t in topics[:5])
            parts.append(f"Topics: {kws}")
        return " ".join(parts)

    # ── cache ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_path(papers: list[dict], model_name: str) -> Path:
        key = hashlib.md5(
            json.dumps([p.get("id","") for p in papers]).encode()
        ).hexdigest()[:10]
        return CACHE_DIR / f"emb_{key}_{model_name.replace('/', '-')}.npy"

    def _load_cache(self, papers: list[dict]) -> bool:
        path = self._cache_path(papers, self.model_name)
        if path.exists():
            arr = np.load(str(path))
            if arr.shape[0] == len(papers):
                self.embeddings  = arr
                self._papers_ref = papers
                print(f"  Cache hit: {path.name}  shape={arr.shape}")
                return True
        return False

    def _save_cache(self, papers: list[dict]) -> None:
        path = self._cache_path(papers, self.model_name)
        np.save(str(path), self.embeddings)
        print(f"  Saved cache: {path.name}")

    # ── embedding ─────────────────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> np.ndarray:
        if self.model_type == "openai":
            result = []
            batch  = 100
            for i in range(0, len(texts), batch):
                resp = self.client.embeddings.create(
                    input=texts[i:i+batch], model=self.model_name
                )
                result.extend(item.embedding for item in resp.data)
            return np.array(result)
        else:
            return self.model.encode(
                texts, show_progress_bar=len(texts) > 50, batch_size=64
            )

    def compute_embeddings(self, papers: list[dict], force: bool = False) -> np.ndarray:
        if not force and self._load_cache(papers):
            return self.embeddings
        print(f"  Embedding {len(papers)} papers ({self.model_name})...")
        texts = [self._paper_text(p) for p in papers]
        self.embeddings  = self._embed(texts)
        self._papers_ref = papers
        self._save_cache(papers)
        return self.embeddings

    # ── search ────────────────────────────────────────────────────────────────

    def search_per_paper(self, candidates: list[dict], my_papers: list[dict],
                         top_k_per_paper: int = 10,
                         min_similarity: float = 0.25) -> list[dict]:
        """
        For each of my_papers, find the most similar candidates independently.
        Each candidate is assigned to the my_paper that matched it best (no duplicates).
        Returns a list of groups: [{"my_paper": ..., "results": [...]}, ...]
        Only groups with at least one result are included.
        """
        cand_embeddings = self.compute_embeddings(candidates)

        # my_paper embeddings (small — skip cache)
        my_texts = [self._paper_text(p) for p in my_papers]
        my_embs  = self._embed(my_texts)

        # For each candidate, find which my_paper claims it with highest sim
        # best_for_cand[cand_idx] = (best_sim, best_my_paper_idx)
        best_for_cand: dict[int, tuple[float, int]] = {}

        for pi, my_emb in enumerate(my_embs):
            sims = cosine_similarity(my_emb.reshape(1, -1), cand_embeddings)[0]
            for ci, sim in enumerate(sims):
                if sim >= min_similarity:
                    if ci not in best_for_cand or sim > best_for_cand[ci][0]:
                        best_for_cand[ci] = (float(sim), pi)

        # Assign each candidate to its best-matching my_paper
        buckets: dict[int, list[dict]] = {pi: [] for pi in range(len(my_papers))}
        for ci, (best_sim, pi) in best_for_cand.items():
            buckets[pi].append({
                **candidates[ci],
                "similarity":    best_sim,
                "matched_paper": my_papers[pi],
            })

        # Sort each bucket, cap at top_k_per_paper, drop empty groups
        groups = []
        for pi, my_paper in enumerate(my_papers):
            bucket = sorted(buckets[pi], key=lambda x: x["similarity"], reverse=True)
            bucket = bucket[:top_k_per_paper]
            if bucket:
                groups.append({"my_paper": my_paper, "results": bucket})

        return groups

    def search(self, candidates: list[dict], my_papers: list[dict],
               top_k: int = 30, min_similarity: float = 0.25) -> list[dict]:
        """Averaged-query search (kept for backward compatibility)."""
        cand_embeddings = self.compute_embeddings(candidates)
        my_texts    = [self._paper_text(p) for p in my_papers]
        my_embs     = self._embed(my_texts)
        query_emb   = np.mean(my_embs, axis=0).reshape(1, -1)
        sims        = cosine_similarity(query_emb, cand_embeddings)[0]
        results = [
            {**candidates[idx], "similarity": float(sim)}
            for idx, sim in enumerate(sims) if sim >= min_similarity
        ]
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # ── display ───────────────────────────────────────────────────────────────

    @staticmethod
    def display(results: list[dict], n: int = 10) -> None:
        print(f"\n{'='*75}")
        print(f"Top {len(results)} results (showing {min(n, len(results))})")
        print(f"{'='*75}\n")
        for i, r in enumerate(results[:n], 1):
            flag = "[PREPRINT]" if r.get("type") == "preprint" else "[published]"
            authors = r.get("authorships", [])
            first   = (
                authors[0].get("author", {}).get("display_name", "—")
                if authors else "—"
            )
            print(f"{i:2}. [{r['similarity']:.3f}] {flag}  {(r.get('title') or '')[:65]}")
            print(f"     {first} | {r.get('year','?')} | doi:{(r.get('doi') or '—')[:40]}")
            if r.get("abstract"):
                print(f"     {r['abstract'][:120]}...")
            print()


def _p(s: str) -> None:
    """Print with GBK-safe fallback for non-ASCII chars."""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))


def run(candidates_path: str, top_k: int = 10,
        model_type: str = "local", min_sim: float = 0.25) -> list[dict]:

    data        = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    author_id   = data["author_id"]
    author_name = data["author_name"]
    my_papers   = data["my_papers"]
    candidates  = data["candidates"]

    _p(f"\nSemantic Search (per-paper) — {author_name}")
    _p(f"  My papers: {len(my_papers)}  |  Candidates: {len(candidates)}")

    searcher = PaperSearcher(model_type=model_type)
    groups   = searcher.search_per_paper(
        candidates, my_papers,
        top_k_per_paper=top_k, min_similarity=min_sim
    )

    total = sum(len(g["results"]) for g in groups)
    _p(f"\nResults: {total} candidates across {len(groups)} of your papers\n")
    for g in groups:
        mp = g["my_paper"]
        _p(f"  [{mp.get('title','?')[:60]}]  -> {len(g['results'])} matches")
        for r in g["results"][:3]:
            flag = "[PRE]" if r.get("type") == "preprint" else "[pub]"
            sim  = int(r["similarity"] * 100)
            _p(f"      {sim}% {flag}  {(r.get('title') or '')[:55]}")
        _p("")

    out = OUTPUT_DIR / f"{author_id}_similar.json"
    out.write_text(
        json.dumps({
            "author_id":   author_id,
            "author_name": author_name,
            "my_papers":   my_papers,
            "model":       searcher.model_name,
            "groups":      groups,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _p(f"Saved --> {out}")
    return groups


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True,
                        help="Candidates JSON from crawl_openalex.py")
    parser.add_argument("--top",       type=int,   default=20)
    parser.add_argument("--min-sim",   type=float, default=0.25)
    parser.add_argument("--model",     default="local",
                        choices=["local", "openai"])
    args = parser.parse_args()
    run(args.candidates, args.top, args.model, args.min_sim)
