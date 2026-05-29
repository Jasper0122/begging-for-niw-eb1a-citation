# Case Demo — Citation Growth Tracking

This folder tracks real citation growth for **Zongrong (Jasper) Li** using this tool as part of an NIW/EB-1A petition.

The goal: measure whether active outreach via `/niw-citation` meaningfully accelerates citation velocity compared to the pre-campaign baseline.

---

## Baseline

| Date | Google Scholar | h-index | i10 | Notes |
|------|---------------|---------|-----|-------|
| 2026-05-29 | **39** | 3 | 1 | Pre-campaign baseline. Tool set up. |

Target snapshots: **2026-08-29** (3 months) and **2026-11-29** (6 months).

---

## How to take a snapshot

```bash
# Optional: refresh Google Scholar data first
python ../begging-for-niw-eb1a-recommenders/scripts/fetch_profile.py \
  --scholar-url "https://scholar.google.com/citations?user=XbCCGC4AAAAJ"

# Take snapshot
python case-demo/snapshot.py
```

This writes a dated file to `case-demo/snapshots/YYYY-MM-DD.md` with:
- Google Scholar total + per-paper breakdown
- OpenAlex stats (secondary source, API-accessible)
- Outreach status fields to fill in manually

---

## Snapshots

| File | Date | Total Citations | Change |
|------|------|----------------|--------|
| [2026-05-29.md](snapshots/2026-05-29.md) | 2026-05-29 | 39 | — (baseline) |

_(update this table after each snapshot)_

---

## Why track this for NIW

USCIS evaluates citation count as evidence of impact in your field. A rising citation rate — especially one that correlates with a documented outreach campaign — demonstrates:

1. **Recognition by peers** — other researchers are finding and citing your work
2. **Active participation** — you are engaged with the research community, not just publishing
3. **Growth trajectory** — citation velocity matters as much as total count for EB-1A

The combination of this tracker + `data/output/<id>_progress.md` (outreach log) creates a paper trail linking your actions to citation outcomes.
