# Outreach Log — Zongrong (Jasper) Li

Auto-updated by the `niw-citation-outreach` routine (runs every 3 days).

---

## 2026-05-29 (manual session)
- **Drafted & sent:** 5 emails via Gmail
  - gcafferata@udesa.edu.ar → Fair Geolocation Extraction from Humanitarian Documents
  - k.mcdonough@lancaster.ac.uk → MapReader: Software and Principles for Computational Map Studies
  - pbhanda2@gmu.edu → Behaviorally Realistic Urban Mobility Synthesis via Fine-Tuned LLMs
  - 20210019@hhu.edu.cn → A multi-source web geocoding optimization method based on road constraints
  - dogii123@hotmail.com → uso das imagens do Street View como instrumento de análise
- **Status updates:** none (baseline)
- **Queue:** 0 pending, 5 draft_created, 0 sent confirmed, 0 replied, 6 skipped, 1 no_contact

## 2026-06-15 (manual recovery — scheduled cloud run fired 14:07 UTC but produced 0 drafts; pipeline re-run locally)
- **Refill:** ran crawl from new 10-paper my_papers seed; topics resolved GIS/mobility/urban (sane); 258 unique candidates, 189 after dedup+keyword filter.
- **Contacts:** find_contacts on 13 high-relevance shortlist -> 4 emails (orcid 3, doi_page 1).
- **Drafted (3, all preprints/open):**
  - TerraBench: Can Agents Reason Over Heterogeneous Earth-System Data? -> Fadillah.Maani@mbzuai.ac.ae (open) [maps to GIScholarBench]
  - Emerging Flexible Designs for Geospatial Multimodal Foundation Models -> potnisav@ornl.gov (open) [maps to StreetViewLLM]
  - Satellite Sociology: Interpreting Spatial Traces of Human Activity from EO Data -> yuichiro@otani.co (open) [maps to StreetViewLLM]
- **Excluded:** Pourebrahim LSTM/GAT environmental-dynamics benchmark (relevance to a specific paper too forced); rest had no email or were off-topic.
- **Status updates:** none.
- **Note:** root cause of empty cloud run unconfirmed (no log access); local crawl + find_contacts + Gmail draft all work. Likely find_contacts web-search timeouts or Gmail step in sandbox.
- **+1 draft (Wang, published):** Reconstructing urban mobility from the built environment -> q.wang@northeastern.edu (finalized, future-work framing) [maps to StreetViewLLM]. Today total = 4 drafts.
- **Code fix:** disabled find_contacts._web_search_email (DuckDuckGo) — it hangs in the cloud sandbox and yields ~0 emails; ORCID + DOI-page retained. Aim: stop scheduled runs stalling on outbound web search.
