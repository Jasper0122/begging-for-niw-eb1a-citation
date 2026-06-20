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

## 2026-06-19 (manual recovery + buffer restock)
- **Diagnosis:** trigger fired daily 06-16..06-19 but produced 0 drafts. Root cause confirmed = queue had 0 `not_contacted` entries, so every run was forced into cloud refill, which yields 0 in the sandbox (live ORCID/DOI/web harvesting unreliable there). The 06-15 recovery drafts were SENT on 06-16 (Maani/Otani/Potnis/Wang) and got positive replies, draining the queue again.
- **Drafted today (3, in Gmail drafts, NOT sent):**
  - Intelligent Multimodal Retrieval and Reasoning (I-GUIDE) -> yfkang@illinois.edu (open) [StreetViewLLM]
  - Risk-Aware LLM Agents for Geospatial Data Retrieval -> y56gao@uwaterloo.ca (open) [GIScholarBench]
  - Complaint locations prediction w/ image-space + custom LLMs -> cyting@mmu.edu.my (finalized) [StreetViewLLM]
- **Buffer restocked (3 not_contacted, emails committed so the cloud can draft them WITHOUT web-harvesting):**
  - Deep learning completes US flood hazard maps (Nat Commun) -> zhang-ye@mail.tsinghua.edu.cn [DamageArbiter]
  - Deep Semi-Supervised Multi-Task Learning of Building Features -> hueseyin.cakmak@kit.edu [BuildingMultiView]
  - Spatio-temporal variation of building morphology in Indian Cities -> sushobhan.sen@iitgn.ac.in [BuildingView]
- **Excluded from this crawl:** rural-dev/SDG platforms (too generic), 2 editorials/prefaces (non-research), heritage multifractal + IoT disaster framework (off-topic).
- **Local harvest yield:** crawl 263 candidates -> 48 keyword-relevant -> find_contacts 13/38 emails. Thin yield is the real supply ceiling.
- **Durable fix in play:** DDG web-search already disabled in find_contacts.py (18c7ba5, no more hangs) + committed not_contacted buffer means a failed cloud refill no longer starves drafting.
- **Queue:** 3 pending(buffer), 12 drafted, 0 sent(local), 6 skipped, 1 no_contact.
