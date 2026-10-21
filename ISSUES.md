# BRD-Agent — Audit Report v2 (pipeline performance pass)

- **Date:** 2026-10-19 (v1 audit 2026-09-30 → fully closed 2026-10-19)
- **Scope:** the end-to-end pipeline — source upload → extraction → knowledge consolidation → BRD generation — plus the latency of the surfaces that sit on that path (status polling, exports, Q&A reads).
- **Method:** static read of every stage in the request path, checked against the installed dependency versions (`server/.venv`, Python 3.11.15, google-genai 2.22.0). **No file was modified.** No profiling run exists in the repo, so every severity below is **structural, not measured** — §6 defines the measurement that would confirm it.
- **Prior audit state:** 3 high, 9 medium, 10 low — **all closed**. Their one-line outcomes are preserved in §1.
- **This pass:** 10 new pipeline findings (P-1…P-10). **Batch E (2026-10-19) fixed four** (P-3, P-4, P-5, P-7) and shipped the timing instrumentation; **Batch F (2026-10-20) fixed the biggest one, P-1** — the Gemini thinking pass was 68% of generated tokens and ~17 s of every run. **Batch G (2026-10-20) added and fixed P-10**: the consolidator was handing Gemini 52–60% byte-identical duplicates, so reasoning was being spent on mechanical reconciliation. **Batch H (2026-10-21) fixed P-8** (indexes) and **measured P-2 into closure** — the aggregate PDF build is 0.09 s, i.e. 0.5% of the 20 s extraction phase, so the "one giant `multi_cell`" concern does not apply at real scale. **Batch I (2026-10-21) resolved P-9**: Q&A scoring no longer builds a per-document word set (72 ms → 54 ms, **peak allocation 10.1 MB → 0.5 MB**) and is proven bit-identical; at real workspace sizes it is 0.2 ms either way, so it is cheap insurance, not a visible win. **P-6 is the last open finding.**
- **Also logged 2026-10-19, resolved 2026-10-20:** **R-1** (§8) — the ~1 s `/workspaces` load was Supabase region latency (Seoul, ~120 ms/round trip). The project has since been moved to a fresh **Mumbai (`ap-south-1`)** project with no data migrated; measured TTFB dropped to the ~150–250 ms range. §8 keeps the measurements for the record.

---

## 1. Prior audit — compact summary (all 22 findings closed)

| ID | Title (short) | Closed |
|---|---|---|
| H-1 | PDF export crash on unmapped unicode | 2026-10-10 |
| H-2 | `validate_brd_data` ↔ `BRDMapper` shape mismatch poisoned exports | 2026-10-10 |
| H-3 | Ghost `generation_jobs` wedged workspaces after restart; create race | 2026-10-11 |
| M-1 | Rate limit keyed on rotatable token hash | 2026-10-18 |
| M-2 | Gmail/Drive imports bypassed size caps; Drive buffered whole file | 2026-10-19 |
| M-3 | Documents list returned full `content` per row | 2026-10-10 (`916a50b`) |
| M-4 | Drive connect/disconnect shared grant with Gmail | 2026-10-10 |
| M-5 | Coral primary buttons failed AA contrast | closed by rebrand (5.95:1) |
| M-6 | Parser tests depended on gitignored `datasets/` | 2026-10-19 |
| M-7 | Single-instance assumptions undocumented | 2026-10-19 |
| M-8 | README env table / install / Python version wrong | 2026-10-19 |
| M-9 | Stale root `requirements.txt` install trap | 2026-10-19 |
| L-1 | Dead API surface (2 client modules + 2 routers) | 2026-10-19 |
| L-2 | `test_models.py` outside `tests/` | 2026-10-19 |
| L-3 | `aria-expanded` static values | 2026-10-19 |
| L-4 | Mobile Q&A auto-scroll no-op below `md` | 2026-10-19 |
| L-5 | Empty/scanned sources passed silently | 2026-10-19 |
| L-6 | Raw provider exceptions reached client + job row | 2026-10-19 |
| L-7 | Dedup false-positive with no override | 2026-10-19 |
| L-8 | Design-skill vendor tree committed against the rule | 2026-10-19 |
| L-9 | Gmail browse N+1 Google API calls | 2026-10-19 |
| L-10 | Deploy-posture notes (`ALLOWED_HOSTS`, CSP, `100vh`) | 2026-10-19 |

**Current baseline (verified on this checkout):** `server/.venv/bin/python -m pytest` → **109 passed**; `npm run lint` clean; `npm run build` green; OpenAPI 27 paths; no open findings remain from v1.

**Carried-forward invariants (must not regress — see AGENTS.md):** PDF builder stays latin-1-safe; `get_message()` signature fixed (`import_service.py:53`); export builders keep `(brd, output_path)`; documents list stays content-deferred; job reaper + partial unique index stay; rate limits key on verified `sub`; single-process deploy posture; client-side behavior frozen except where explicitly authorized.

---

## 2. Pipeline map (as built today)

```
UPLOAD — synchronous inside the HTTP request
  POST /workspaces/{id}/documents/upload
   → temp file (chunked copy, 10 MB cap) → magic sniff → parse
     (pymupdf ≤200 pages / python-docx / txt, 500k char cap) → normalize
   → insert rows → source_revision += N → 201 (StandardDocumentSummary[])
        client blocks for the entire parse; "Uploading…" is the only feedback

GENERATE — 202 + BackgroundTask (own DB session)
  POST /workspaces/{id}/brd/generate
   ┌ 1. processing_sources   (only when unextracted docs exist)
   │    build ONE aggregate PDF of all unextracted docs (fpdf2, ≤1,000,000 chars)
   │    → Sarvam Document AI: create job → poll every 2 s, max 60 attempts → results
   ├ 2. preparing_knowledge  (deterministic Python merge — no LLM)
   └ 3. generating_brd       (ONE Gemini 2.5 Flash call → save brd row)

  Client polls GET /brd/status every 2 s while tracking; only phase changes
  update the UI ("Reading sources ··· Ns").
```

Structurally sound: one Sarvam job for all new docs (not per-doc), consolidation is deterministic, and exactly one Gemini call. Regeneration with no new sources skips stage 1 entirely. The findings below are about *how* the three stages are executed, not about the shape of the pipeline.

---

## 3. New findings — pipeline latency

Severity key: **M** = medium (measurable slowdown or failure risk on the main path) · **L** = low / hygiene. Every item lists the **safe change** that would not alter routes, schemas, status codes, or client contracts.

### ✅ P-1 — BRD generation ran Gemini 2.5 Flash with default *thinking*, and with no timeout or retry — FIXED 2026-10-20

- **Status:** fixed, and the benchmark made the case stronger than the original estimate. Measured on the largest real `ProjectKnowledge` row (14,875 chars, 11 sections) against the live API:

  | Model | Thinking | Time | Thought tokens |
  |---|---|---|---|
  | `gemini-2.5-flash` (was prod) | default | **17.0–22.8 s** | **3,319** |
  | `gemini-2.5-flash` | `thinking_budget=0` | **6.0–6.7 s** | 0 |
  | `gemini-flash-lite-latest` | `thinking_level=MINIMAL` | 37.7 s | 0 |
  | `gemini-flash-latest` | `thinking_budget=0` | 107.5 s | — |
  | `gemini-flash-latest` | default | 278.8 s | — |
  | `gemini-3.1-flash-lite` | `thinking_level=MINIMAL` | **503 ×2** | — |

  Thinking was **68% of the generated tokens** (3,319 of 4,851). **Newer ≠ faster for this task**: the 3.x reasoning-oriented models were 18–46× slower, and 3.1 Flash-Lite was unavailable twice. The fix is therefore the model we already use with reasoning disabled — not a model swap.
- **Quality A/B (same payload, per-section chars):** default 5,949 vs off 5,900 total, **−0.8%**. Eight of eleven sections were byte-identical; `executive_summary` grew +51 and `business_requirements` shrank −112. All 11 sections still populated. End-to-end after the change: **6.72 s**, `thoughts=None`, 11/11 sections, 6,148 chars.
- **Implementation:** new settings `gemini_thinking_budget` (default **0**) and `gemini_timeout_seconds` (default **120**) — budget is config-driven so it can be raised to e.g. 1024 without a code change if quality regresses. `GeminiBRDGenerator` now sends `thinking_config=ThinkingConfig(thinking_budget=...)`, logs the token split (`prompt/output/thoughts/total` + elapsed) on the `brd-agent.generation` logger, and sets `http_options` with a millisecond timeout plus an **explicit 2-attempt retry** on `408/429/500/502/503/504`. The explicit value matters: the SDK retries **5 times by default** (verified in `_api_client.py:905`), so leaving it implicit meant unbounded worst-case latency.
- **Original finding (for the record):** `gemini_brd_generator.py:58-65` sent only `response_mime_type` + `response_json_schema`; model pinned at line 18. No timeout, no retry — a single transient 503 cost one of the `5/hour` generates.

### ✅ P-2 — The aggregate extraction PDF is built as one giant `multi_cell` — CLOSED 2026-10-21, **not material**
- **Original concern:** `server/app/ai/builders/project_document_builder.py:159-163` — a single `pdf.multi_cell(...)` receives `document.content` verbatim; budget is `max_aggregate_chars = 1,000,000`. The worry was that fpdf2 would lay out the whole string in one call, so a near-budget workspace would build a ~140-page PDF before Sarvam saw a byte.
- **Measured 2026-10-21 (Batch H, Run B) on the real 4-document workspace:** 11,549 chars → **30 KB PDF built in 0.09 s**, i.e. **1% of the 1M budget** and **0.5% of the 20.2 s `processing_sources` phase**. A second independent build measured 0.11 s.
- **Verdict:** the finding was arithmetically right about the *ceiling* and wrong about *where real workspaces sit*. Optimizing a 0.09 s step that is 0.5% of a phase whose other 99.5% is a vendor round trip would be effort spent for noise. **Closed with no code change.**
- **Reopen condition (write it down so nobody re-derives it):** if a workspace's aggregate ever approaches `max_aggregate_chars`, the first lever is **lowering that setting** (config only, no layout risk) — chunked `multi_cell` is only warranted if a genuinely large input still proves slow, and any change there must be export-diffed against the current PDF.

### ✅ P-3 — Sarvam extraction had a hard 2-minute client timeout that nothing could override — FIXED 2026-10-19

- **Status:** fixed. New setting `sarvam_timeout_seconds` (`config.py`, default **180**, documented in `server/.env.example`); `SarvamExtractor` accepts an optional `timeout_seconds` (defaults to the setting — the single call site in `document_extraction_service.py` passes nothing, so its signature is unchanged) and derives the poll budget via a `max_attempts` property (`ceil(timeout / 2s)`). Also removed a wasted final `time.sleep` (the old loop slept after its last poll before raising). Timing is now observable: submit logs the Sarvam `job_id`, completion logs poll count + elapsed, timeout/failed/cancelled log their own line under `brd-agent.extraction`.
- **Original finding (for the record):** `sarvam_extractor.py:99-128` — `max_attempts = 60` × `POLL_INTERVAL_SECONDS = 2` (line 19). A job that would have completed at 2:05 was declared failed; the retry re-uploaded the PDF and consumed another `5/hour` generate. No jitter/backoff, no elapsed-time logging, and the ceiling was a constant rather than a setting.

### ✅ P-4 — Status polling loaded the entire BRD JSON every 2 seconds — FIXED 2026-10-19

- **Status:** fixed the way the entry offered. `BRDRepository.get_summary_by_workspace_id()` selects the same row with `.options(defer(BRD.brd_data))` (the M-3 pattern), and `get_brd_status_for_user` switched to it. The status path only reads existence, `source_revision` and `user_edited_at` — all non-deferred, so there is no lazy-load: nothing in that function touches `brd_data`. `get_by_workspace_id` is untouched and still used by `GET /brd`, `PUT /brd`, and both exporters.
- **Original finding (for the record):** `brd_service.py:320-322` called the plain `SELECT *` repository method, materializing the full 11-section document every 2 s just to answer "does a BRD exist and is its `source_revision` current".

### ✅ P-5 — Every status poll reconstructed `BRDService` (new `genai.Client`) — FIXED 2026-10-19

- **Status:** fixed by making the generator lazy. `BRDService.__init__` now stores the schema path and `brd_generator` is a cached property that builds `GeminiBRDGenerator` on first use; `generate_brd_for_user` is unchanged. Read paths (status / exports / edit) no longer allocate a genai client, and — as a side effect — `GET /brd/status` no longer 500s when `GEMINI_API_KEY` is missing.
- **Original finding (for the record):** `api/routes/brd.py:138` → `BRDService.__init__` eagerly built `GeminiBRDGenerator` (`brd_service.py:50`), which calls `genai.Client(...)` and raises if the key is absent — 30 allocations/minute per polling client, plus a read endpoint that depended on an AI credential.

### 🟡 P-6 — Upload parsing is synchronous, up to 10 files × 200 pages per request
- **Where:** `server/app/api/routes/standard_document.py:199-299` — decode → magic → parse → normalize loop inside the request handler, then one `create_documents_from_ingestion` commit.
- **Impact:** worst-case request is tens of seconds (10 × a large PDF); the client shows only "Uploading…", and a proxy/ingress timeout can kill a request whose parse work is already done, forcing a re-upload. Each in-flight upload also occupies one threadpool worker for its whole duration.
- **Safe change:** the honest fix is background ingestion + a processing state, which **changes the API contract** — out of scope unless explicitly authorized. Until then: document the ceiling and consider a lower files-per-request cap. The per-file caps themselves are already correct (chunked copy, magic sniff, parse caps before heavy work).

### ✅ P-7 — No response compression on the API — FIXED 2026-10-19

- **Status:** fixed with `GZipMiddleware(minimum_size=1000)`. Verifying it end-to-end surfaced two things worth recording:
  1. **It must be the *first* `add_middleware` call (innermost).** The stack is applied so the first-added middleware sits closest to the routes. Added last (outermost), the `BaseHTTPMiddleware` layer underneath (SlowAPI) re-streams every body, so responses arrive with `more_body=True` and the `minimum_size` gate never applies — measured on the real app: a 43-byte `/health` body came back gzipped (65 bytes on the wire, magic `\x1f\x8b`, no `Content-Length`). Placed innermost it behaves correctly: `/health` passes through untouched (43 bytes, `Content-Length` intact) while `/openapi.json` (25 kB) compresses to 2.7 kB.
  2. **PDF/DOCX are excluded via `exclude_content_types`** (on top of Starlette's `DEFAULT_EXCLUDED_CONTENT_TYPES`). `FileResponse` is a streaming response, so exports would otherwise be compressed unconditionally: wasted CPU on already-compressed files and a dropped `Content-Length` on downloads.
- **Original finding (for the record):** `server/app/main.py` had no gzip middleware — the full 11-section BRD JSON and every status/document payload shipped uncompressed.

### ✅ P-8 — No index on `workspace_id` for the workspace-scoped tables — FIXED 2026-10-21 (3 indexes, not 5)
- **Correction first:** the original entry claimed five tables needed an index. Checked against live `pg_indexes` on 2026-10-21, **two of them were already indexed** — `brds` and `project_knowledge` each declare `workspace_id` with `unique=True`, and Postgres backs that with `brds_workspace_id_key` / `project_knowledge_workspace_id_key`. `generation_jobs` was already covered too (`ix_generation_jobs_workspace_id` + the partial unique from `b8c9d0e1f2a3`). This is the same over-count pattern as the `workspaces.user_id` correction in R-1: a `unique` constraint is easy to miss when reading only the column definition.
- **The real gap was three indexes**, all created by migration `c1d2e3f4a5b6`: `ix_standard_documents_workspace_id`, `ix_document_extractions_workspace_id`, and `ix_document_extraction_documents_standard_document_id`.
- **Why the third one:** `uq_extraction_document` is `(document_extraction_id, standard_document_id)`, so it **cannot** serve a lookup by `standard_document_id` alone — which is exactly the predicate the ORM cascade issues when a document is deleted.
- **Verified:** `alembic upgrade head` → all three present in `pg_indexes`; a reverse query for any `workspace_id`/`standard_document_id` column that is not the leading column of some index now returns **zero rows**; `downgrade -1` removes all three; `upgrade head` restores them.
- **Model + migration both changed on purpose** — mirroring DDL in `__table_args__`/`index=True` follows the `generation_jobs` precedent and is what lets the test assert on model metadata rather than a live database.
- **Original finding (for the record):** `standard_documents`, `brds`, `project_knowledge`, `document_extractions` carry FKs with no index — Postgres does not auto-index foreign keys. Correct about the mechanism, over-broad about the scope.

### ✅ P-9 — Q&A tokenizes every document's full content on each question — RESOLVED 2026-10-21, **not material at real scale**
- **What it was:** `brd_qa_service.py` read every document's full `content`, then built a **set of every distinct word** in each document, intersected it with the question's terms, and threw the set away — per document, per question. On a workspace at the capped size (10 files × 500k chars) that is 5M characters tokenized to answer a question about at most a handful of words.
- **Correction to the original proposed fix:** *"score from summaries/metadata, then fetch content only for the selected ids"* **cannot preserve behaviour.** A document's content contributes up to `len(question_terms)` points and `MIN_RELEVANCE_SCORE` is 2, so a document with no title match can still qualify on content alone — nothing can be eliminated without reading it. Exactness forbids pruning, which is why the fix had to keep reading content.
- **What was changed instead:** the scan targets the question's terms directly (`_term_pattern` + lookarounds that reproduce `[a-zA-Z0-9]+` boundaries exactly) and stops as soon as every eligible term has been seen. The token filter (`len >= 3`, stop words) was hoisted to `MIN_TERM_LENGTH` / `STOP_WORDS` so the indexer and the scanner can never disagree. **Selection is bit-identical** — proven by 300 seeded fuzz cases plus 8 questions against the old algorithm, kept in the test file as an oracle.
- **Measured (2026-10-21, 10 docs × 500k chars):** wall clock **72 ms → 54 ms** (1.3×); peak allocation **10.1 MB → 0.5 MB (20.5× less)**. A substring prefilter was also tried and rejected — with a realistic question every term appears in every document, so it saves nothing.
- **Verdict: not material today.** At the real 11.5k-char workspace this is 0.2 ms either way. The change is kept because it is a strict improvement (exact, cheaper, and 20× less garbage per question under concurrency), not because it fixed a visible problem.
- **Reopen condition:** if workspaces approach the 5M-char cap, move scoring **into Postgres** (`regexp` per term in the `WHERE`, so content never crosses the wire and only the 8 selected rows are fetched). That is the only fix that avoids the read, and it changes the query shape enough to deserve its own batch.

### ✅ P-10 — ProjectKnowledge carried 52–60% byte-identical duplicates, so Gemini was paid to reconcile them — FIXED 2026-10-20

- **Where:** `server/app/ai/consolidators/knowledge_consolidator.py::_merge_documents` — its docstring stated *"No deduplication or conflict resolution is performed"*, and it simply `extend`ed every field.
- **Why it cost time:** the BRD prompt explicitly forbids merging "separate requirements merely because they relate to the same feature", so Gemini had to decide, item by item, which repeats were genuine duplicates and which were merely similar. That is hidden thinking-token work spent on a mechanical problem.
- **Measured on both real workspaces** (each is one aggregate extraction over several documents, so the duplicates are *inside a single extraction*, not only across documents): **147 → 71 items (−76, 52%)** and **120 → 48 (−72, 60%)**.
- **Effect on the BRD call** (14.9k-char payload): prompt **5,010 → 3,125 tokens**; with dynamic thinking **4,201 → 2,755** thought tokens and **22.8 s → 18.1 s**; with `gemini_thinking_budget=2048` **14.4 s**. `functional_requirements` = **15 in every configuration tested** (dynamic / 2048 / 1024 / 0).
- **Fix:** `_canonical_key` (dataclass → `asdict` → dict/list recursion → whitespace-collapse + lowercase → sorted-key JSON) and `_dedupe` (first-seen order). Applied to **both** the single-document and merge paths, driven by one `_LIST_FIELDS` tuple so a newly added field cannot silently skip dedup.
- **Deliberately *not* done:** fuzzy or semantic dedup. Normalization never touches digits or punctuation, so a changed threshold (`"3.5 seconds"` vs `"35 seconds"`) or actor keeps both items, and near-duplicates still reach Gemini. 12 tests pin both sides of that line, including the must-not-merge cases.
- **Note:** existing `project_knowledge` rows keep their duplicates until that workspace is regenerated.

---

## 4. Checked and found fine (do not "optimize" these)

- **Job lifecycle:** reaper + partial unique index + `IntegrityError`-adopt are correct; commits between phases release the DB connection while Sarvam/Gemini run.
- **Background task isolation:** sync `run_generation_job` runs in the threadpool with its own `SessionLocal` — it does not block the event loop; the 202 returns immediately.
- **Skip-aware regeneration:** `has_new_sources` gates stage 1, so regenerating an edited BRD costs one Gemini call only.
- **Consolidation:** deterministic merge, no third LLM hop, no N+1 DB reads.
- **Upload hardening:** chunked copy with a hard 10 MB ceiling, content-based magic checks (5-byte PDF header, PK zip + `[Content_Types].xml`, NUL/UTF-8 sample), caps applied *before* heavy work.
- **List projections:** documents list is content-deferred (M-3); status polling stops entirely when no job is tracked (`refetchInterval` gated on `trackedJobId`).
- **Client caching:** BRD `staleTime` 5 min, gmail-search `gcTime` 90 s, workspace list 60 s — no redundant refetch pattern found on the pipeline path.

---

## 5. Fix order

**Batch E — done 2026-10-19** (contract-safe, no route/schema/client change)
1. ~~**E-0**~~ phase timing logs (PDF build / Sarvam / consolidation / Gemini / total) — `_log_phase` in `generation_job_service.py`, stage logs in `document_extraction_service.py` + `sarvam_extractor.py`, all at INFO.
2. ~~**P-4**~~ status-path BRD summary projection (`defer(brd_data)`).
3. ~~**P-3**~~ config-driven Sarvam ceiling (`sarvam_timeout_seconds`, default 180) + poll/elapsed logging.
4. ~~**P-7**~~ `GZipMiddleware` (innermost, exports excluded).
5. ~~**P-5**~~ lazy Gemini generator (also decouples status from `GEMINI_API_KEY`).

**Batch F — done 2026-10-20** (contract-safe, server-only)
6. ~~**P-1**~~ Gemini `thinking_budget=0` via `gemini_thinking_budget` (default 0) + `gemini_timeout_seconds` (120) + explicit 2-attempt retry + token-split logging. **17–23 s → 6.7 s, output within 0.8%.** Model benchmark (§P-1) also ruled out the 3.x family for this task (18–46× slower; 3.1 Flash-Lite 503s).
7. ~~**P-8** pending~~ — deferred; superseded in priority by the R-1 region move, which resolved the latency that made it visible.

**Batch G — done 2026-10-20** (contract-safe, server-only)
8. ~~**P-10**~~ deterministic dedup in `KnowledgeConsolidator` — identical items dropped at consolidation, near-duplicates kept for Gemini. **52–60% of items were duplicates; BRD call 22.8 s → 14.4 s at `thinking_budget=2048`, prompt 5,010 → 3,125 tokens.**
9. ~~**`gemini_thinking_budget` default**~~ raised `0` → **`2048`**, so the reasoning pass is restored now that the input is clean (see P-10).

**Batch H — done 2026-10-21** (contract-safe, server-only)
10. ~~**P-8**~~ three missing indexes (migration `c1d2e3f4a5b6`) — `standard_documents.workspace_id`, `document_extractions.workspace_id`, `document_extraction_documents.standard_document_id`. **Corrected from five tables to three**: `brds`/`project_knowledge` were already indexed by their `unique` constraints.
11. ~~**P-2**~~ **measured into closure — not material.** Aggregate PDF build **0.09 s** for 11,549 chars (1% of the 1M budget, 0.5% of the phase). No code change.

**Batch I — done 2026-10-21** (contract-safe, server-only)
12. ~~**P-9**~~ Q&A scoring scans for the question's terms instead of tokenizing each document into a word set. **Bit-identical selection** (oracle-tested), **72 ms → 54 ms** and **10.1 MB → 0.5 MB peak** at the cap; irrelevant at today's sizes, kept as cheap insurance.

**Next — measured**
13. **P-6** (background ingestion needs a processing state + contract change). This is the **last open finding**; Batch J proposes instrumenting it first (Track A) and only building Track B once upload time is measured.

**Resolved / out of scope**
14. ~~**R-1**~~ (§8) — **resolved 2026-10-20** by moving to a fresh Mumbai project; no code change needed.

**Discipline for every item:** no route/schema/status change; no client change; server diff → **restart the backend**; run `pytest` (183 after Batch I), `npm run lint`, `npm run build`; update AGENTS.md + this file per the established per-batch pattern.

---

## 5e. Batch H results (2026-10-21)

- **Suite:** 148 → **154 passed** (+6 in new `server/tests/test_workspace_indexes.py`). App boots, 27 OpenAPI paths. `npm run lint` clean, `npm run build` green, **zero client diff**.
- **Diff:** 3 model files, migration `c1d2e3f4a5b6`, 1 new test file, docs.
- **Migration drill:** `upgrade head` → 3 indexes in `pg_indexes` → reverse gap query returns **0 rows** → `downgrade -1` removes all 3 → `upgrade head` restores. Reversibility tested, not assumed.
- **Run A (regenerate, no new sources — free):** `preparing_knowledge` ≈ 3 ms (consolidation, incl. dedup); `generating_brd` **13.9 s** with `prompt=3125`, `thoughts=1491`, 11/11 sections, 15 functional requirements.
- **Run B (real Sarvam job, result discarded, nothing written):** on the 4-document workspace — aggregate PDF build **0.09 s**, Sarvam round trip **20.1 s** (10 polls, 19.5 s server-side), so `processing_sources ≈ 20.2 s` and **the vendor round trip is 99.5% of it**.
- **The end-to-end picture after Batches F/G/H** on a fresh-source generation: `~20.2 s extraction + ~0.003 s consolidation + ~13.9 s BRD ≈ 34 s`. The next-largest lever is no longer in this codebase.
- **Still open:** P-6, P-9.

---

## 5f. Batch I results (2026-10-21)

- **Suite:** 154 → **183 passed** (+29 in new `server/tests/test_brd_qa_selection.py`). App boots, 27 OpenAPI paths; `npm run lint` clean, `npm run build` green; **zero client diff**.
- **Diff:** `app/services/brd_qa_service.py`, `app/db/models/__init__.py` (incidental, see below), 1 new test file, docs.
- **Equivalence, not just tests:** the old scoring algorithm is preserved inside the test file as an oracle and compared against the new one over a hostile corpus (underscores, hyphens, decimals, substrings, accented text, empty content) plus 300 seeded fuzz strings and 8 full-selection questions. Two real divergences were caught this way before they shipped: the old set excluded tokens shorter than 3 chars and stop words, and a non-ASCII term like `café` can never be a token.
- **Measured at the cap (10 × 500k chars):** 72 ms → 54 ms wall clock (1.3×); **10.1 MB → 0.5 MB peak allocation (20.5× less)**. At the real 11.5k-char workspace: 0.2 ms either way.
- **Rejected:** scoring from titles/summaries (`MIN_RELEVANCE_SCORE = 2` means a content-only document can always qualify, so no pruning is safe) and a substring prefilter (every term appears in every document with a realistic question).
- **Incidental fix:** `app/db/models/__init__.py` was missing `GoogleConnection`, so `import app.db.models` produced an incomplete mapper registry — any script touching an ORM entity without also importing the integrations died with `KeyError: 'GoogleConnection'`. It bit two measurement scripts the same day. One line, now complete.
- **Still open:** P-6 only.

---

## 5d. Batch G results (2026-10-20)

- **Suite:** 136 → **148 passed** (+12 in new `server/tests/test_knowledge_consolidator.py`; 2 assertions in `test_gemini_generator.py` updated for the new default).
- **Diff:** `ai/consolidators/knowledge_consolidator.py`, `core/config.py`, `.env.example`, 1 new test file, docs. **Zero client diff.**
- **Real-data verification (both existing workspaces, run through the patched consolidator):** `147 → 71 items (−76, 52%)` and `120 → 48 (−72, 60%)`.
- **Timings (same 14.9k-char payload):** dynamic 22.8 s → deduped 18.1 s; deduped + `2048` **14.4 s**; deduped + `1024` 10.6 s. Functional requirements = **15 in every configuration**.
- **Still open:** P-2, P-6, P-8, P-9.

---

## 5c. Batch F results (2026-10-20)

- **Suite:** 126 → **136 passed** (+10 in new `server/tests/test_gemini_generator.py`; no existing test changed).
- **Diff:** `ai/generators/gemini_brd_generator.py`, `core/config.py`, `.env.example`, 1 new test file, docs. **Zero client diff.**
- **Measured end-to-end (real API, real ProjectKnowledge):** 6.72 s, `thoughts=None`, 11/11 sections, 6,148 chars — vs 17.0–22.8 s and 3,319 thought tokens before.
- **Still open:** P-2, P-6, P-8, P-9.

---

## 5b. Batch E results (2026-10-19)

- **Suite:** 109 → **126 passed** (+17 in new `server/tests/test_pipeline_latency.py`; no existing test changed).
- **Diff:** 8 server files (`main.py`, `core/config.py`, `services/brd_service.py`, `services/document_extraction_service.py`, `services/generation_job_service.py`, `repositories/brd_repository.py`, `ai/extractors/sarvam_extractor.py`, `.env.example`) + 1 test file + docs. **Zero client diff.**
- **Verified:** app boots (27 OpenAPI paths, unchanged); `/health` uncompressed with `Content-Length`, `/openapi.json` 25 kB → 2.7 kB; `defer` confirmed at the SQL level (`.brd_data` absent from the status SELECT, present in the full one); phase timing line emitted.
- **Still open:** P-1, P-2, P-6, P-8, P-9.
- **Manual smoke (needs a real workspace):** run one generation and read the new timing lines to fill in §6, then download a PDF/DOCX to confirm exports are byte-identical (they are excluded from gzip by content type).

---

## 6. Measurement plan (instrumentation shipped in Batch E; run it next)

The timing instrumentation now exists — every generation logs, at INFO:

- `brd-agent.extraction` — `Submitted Sarvam extraction job <id>`, the aggregate-PDF line (`N document(s), M chars in X.XXs`), `Sarvam job <id> completed after N poll(s) in X.Xs`, and the total Sarvam wall time;
- `brd-agent.generation` — `phase=processing_sources|preparing_knowledge|generating_brd took X.XXs` plus `succeeded in X.XXs` / `failed … after X.XXs`.

So one real generation (2–3 sources, then a regenerate) answers most of §3. Record: aggregate chars, PDF build seconds, Sarvam submit→complete seconds and poll count, consolidation seconds, Gemini seconds. Then A/B P-1 (`thinking_budget=0` vs default) on the same workspace and compare the `generating_brd` line — that is the number that decides whether P-1 is the win it looks like.

Only after that should P-2's severity be settled — it is the one item where a fix could add risk (export-layout change) for an unproven gain.

### 6a. Measured 2026-10-21 (Batch H, Run B)

One real Sarvam job on the 4-document workspace, result discarded (nothing written):

| Stage | Time | Share |
|---|---|---|
| Aggregate PDF build | **0.09 s** (11,549 chars → 30 KB) | 0.5% |
| Sarvam round trip | **20.1 s** (10 polls; 19.5 s server-side) | **99.5%** |
| `processing_sources` total | ~20.2 s | 100% |

Plus `preparing_knowledge` ≈ 3 ms (consolidation incl. dedup) and `generating_brd` 13.9 s (Batch G measurement). So a fresh-source generation is **≈34 s**, of which **20 s is a vendor call this codebase cannot speed up** — the only lever there is input size, and 11.5k chars is already small.

**Consequence for P-2:** closed. The premise (a multi-hundred-KB, ~140-page PDF) describes the `max_aggregate_chars` ceiling, not any real workspace — this one uses **1%** of the budget. Reopen only if a workspace approaches that ceiling, and lower the budget before touching the builder.

---

## 7. Notes on process

- This pass was **read-only**; `git status` showed only the pre-existing uncommitted Batch D changes.
- Severities assume the documented single-process deployment (`uvicorn app.main:app`, no `--workers`). Under multi-worker, P-4/P-5 overhead multiplies and the in-process job posture already fails (M-7).
- Line numbers refer to the working tree as of 2026-10-19 and will drift after edits.

---

## 8. R-1 — `/workspaces` took ~1 s because of Supabase round trips (measured 2026-10-19, **RESOLVED 2026-10-20**)

**Symptom reported:** the workspaces page takes about a second to load.

**Verdict:** not React, not the query, not the payload. It is **network round-trip count to a database in another region**. Measured on this checkout against the live dev database (`DATABASE_URL` → `aws-0-ap-northeast-2.pooler.supabase.com`, i.e. **Seoul**) while the user is in India. **No file was modified** — this section is a record so the work can be picked up later without re-measuring.

**Resolution (2026-10-20):** the project was moved to a fresh **`ap-south-1` (Mumbai)** Supabase project — schema rebuilt from `alembic upgrade head`, **no data or auth users migrated**. TTFB dropped into the ~150–250 ms range. No application code changed; only `DATABASE_URL`, `SUPABASE_URL`, and the client's `VITE_SUPABASE_*` values. Two findings from that cutover are worth keeping: `psql` requires `postgresql://` while SQLAlchemy requires `postgresql+psycopg://` (only psycopg 3 is installed, so a bare scheme raises `ModuleNotFoundError: psycopg2`), and Google's `redirect_uri_mismatch` for a new project is fixed by adding `https://<ref>.supabase.co/auth/v1/callback` to the OAuth client **and saving it**.

### 8.1 Per-hop costs

| Hop | Measured |
|---|---|
| DNS resolve | 3 ms |
| TCP connect to Seoul | 119–123 ms |
| `psycopg.connect` (TCP + TLS + auth) | **792–2165 ms** |
| One `SELECT 1` on an already-open connection | ~118 ms |
| One statement + explicit `COMMIT` | ~360–400 ms |

So: a statement in an open transaction costs ~120 ms (one RTT), while the pooler charges roughly 2–3× that for transaction boundaries (BEGIN / COMMIT / ROLLBACK).

### 8.2 The actual `/workspaces` request (the page's one `GET`)

`GET /workspaces` issues a **single** list query — there is no N+1 on this page. But FastAPI's `get_current_db_user` dependency adds a `users` PK lookup, and the `Session` wraps both in a transaction that is rolled back on close:

| Stage | Measured (6 runs) |
|---|---|
| Session checkout (warm pool) | ~0 ms |
| `users` SELECT — first statement of the request | **388–550 ms** |
| `workspaces` SELECT | 124–223 ms |
| implicit `ROLLBACK` on `db.close()` | 120–198 ms |
| **backend total** | **623–895 ms** |

With 4 workspace rows, data volume is irrelevant — it is pure latency × round trips. Adding browser/JS overhead lands on the ~1 s the user sees.

**Why it sometimes feels worse than 1 s:** `db/session.py` sets `pool_recycle=300`. Every 5 minutes of idleness retires the pooled connection, so the next request also pays the 0.8–2.1 s handshake above.

### 8.3 What each fix would buy (measured, not estimated)

| Variant | Measured |
|---|---|
| **A.** Current path (2 SELECTs + implicit ROLLBACK) | 623–697 ms |
| **B.** Drop the per-request `users` SELECT (cache user existence in-process) | ~486 ms |
| **C.** Read-only **AUTOCOMMIT** session — no BEGIN, no ROLLBACK | **122–141 ms** |

C's first call was 2585 ms because that probe used its own cold engine (that number *is* the handshake cost).

### 8.4 Options, in order of payoff

1. **Move the Supabase project to `ap-south-1` (Mumbai).** ~120 ms → ~25 ms per RTT, so it improves *every* surface at once: workspaces, the 2 s generation-status poll, Q&A, document lists, uploads. **No code change** — new project + `pg_dump`/restore + env swap + the two migrations re-applied. Needs a maintenance window, not a refactor.
2. **Co-locate the backend with the DB** (deploy in `ap-northeast-2`). No data migration at all; app→DB drops to ~1–2 ms, so a request becomes ~130–250 ms. Trade-off: every browser request then pays the India→Seoul hop instead. Cheapest to try, worst steady-state for India users.
3. **Cut round trips in code** (no infrastructure change, complementary to either of the above):
   - read-only GET routes on an AUTOCOMMIT session → the C number above;
   - cache the per-request `users` existence check → saves ~150–200 ms;
   - optionally one combined user + workspaces query → saves another RTT.

   **Caveat for (3):** GET routes are not purely read-only — `ensure_user_exists` inserts on first login and `GET /brd/status` runs the stale-job reaper. This needs a dedicated read-only dependency (or explicit handling of those two writers), not a flag flipped on the global engine.

### 8.5 Before acting on this

Confirm the attribution in devtools: if `GET /workspaces` shows **TTFB ≈ 650–900 ms** and the remainder is quick, this section is the explanation. If TTFB is low and the time is in JS/module loading, the cause is the **Vite dev server** compiling modules on first navigation (a dev-only, once-per-session cost) — a different fix entirely. That check was not run.

### 8.6 Incidental observation (unverified through the API, low)

While reproducing the request path, calling `UserService.ensure_user_exists()` with a `CurrentUser` whose `email` is `None` raised a 500-class error instead of failing cleanly:

```
psycopg.errors.NotNullViolation: null value in column "email" of relation "users" violates not-null constraint
INSERT INTO users (id, email, name) VALUES (..., NULL, NULL)
```

Google sign-in always supplies an `email` claim, so this is latent rather than live: a token without one (different auth method, or a claim change on Supabase's side) would 500 on the first request instead of returning a 4xx. It was **not** reproduced through HTTP and no data was written (the statement failed at flush and rolled back). Worth a guard if the auth surface ever widens.
