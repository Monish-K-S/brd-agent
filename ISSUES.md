# BRD-Agent — Audit Report v2 (pipeline performance pass)

- **Date:** 2026-10-19 (v1 audit 2026-09-30 → fully closed 2026-10-19)
- **Scope:** the end-to-end pipeline — source upload → extraction → knowledge consolidation → BRD generation — plus the latency of the surfaces that sit on that path (status polling, exports, Q&A reads).
- **Method:** static read of every stage in the request path, checked against the installed dependency versions (`server/.venv`, Python 3.11.15, google-genai 2.22.0). **No file was modified.** No profiling run exists in the repo, so every severity below is **structural, not measured** — §6 defines the measurement that would confirm it.
- **Prior audit state:** 3 high, 9 medium, 10 low — **all closed**. Their one-line outcomes are preserved in §1.
- **This pass:** 9 new pipeline findings (P-1…P-9). **Batch E (2026-10-19) fixed four of them** (P-3, P-4, P-5, P-7) and shipped the timing instrumentation needed to size the rest — see §5. P-1, P-2, P-6, P-8, P-9 remain open.
- **Also logged 2026-10-19, deferred by request:** **R-1** (§8) — the ~1 s `/workspaces` load is Supabase region latency (project sits in **Seoul**, ~120 ms per round trip × 3–4 round trips per request), not React. Measured end-to-end against the dev database; deliberately **not** fixed.

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

### 🟡 P-1 — BRD generation runs Gemini 2.5 Flash with default *thinking*, and with no timeout or retry
- **Where:** `server/app/ai/generators/gemini_brd_generator.py:58-65` (config sets only `response_mime_type` + `response_json_schema`); model pinned at line 18.
- **Why it costs time:** Gemini 2.5 Flash performs dynamic *thinking* by default. This task is a constrained restructuring ("ProjectKnowledge JSON → BRD JSON under a fixed schema", ~250-line instruction block), not open reasoning, so hidden thinking tokens add latency before the first output token without buying much quality. The call is also **non-streaming** and has **no explicit timeout and no retry** — a single transient 503/429 fails the whole run, which costs one of the `5/hour` generates (`config.py:50`) and forces a manual retry.
- **Impact:** likely the single largest controllable chunk of the BRD stage. Unquantified until §6 is run.
- **Safe change:** pass `thinking_config=types.ThinkingConfig(thinking_budget=0)` (confirmed available in the installed google-genai 2.22.0) and set a request timeout + one retry in `http_options`. **Verify output quality on one real workspace before committing** — thinking-off may thin out the synthesis-quality sections (executive summary, derived scope). No API/schema change.

### 🟡 P-2 — The aggregate extraction PDF is built as one giant `multi_cell`
- **Where:** `server/app/ai/builders/project_document_builder.py:159-163` — a single `pdf.multi_cell(...)` call receives `document.content` verbatim; budget is `max_aggregate_chars = 1,000,000` (`config.py:45`).
- **Why it costs time:** fpdf2 lays out the entire string (line-breaking and justification) in one call, then subsets and embeds the DejaVu TTF on `output()`. At the 1M budget this is a multi-hundred-KB text block and a generated PDF of roughly 140 pages (8 pt, `LINE_HEIGHT = 4`) — CPU + memory spent *before* Sarvam sees a byte.
- **Note:** the 200-page cap applies only to **uploaded** PDFs (`pdf_parser.py:40`); the generated aggregate PDF is bounded by characters only.
- **Impact:** adds seconds-to-tens-of-seconds to stage 1 and feeds a very large document to Sarvam, which compounds P-3.
- **Safe change (measure first):** if §6 shows this is material, either lower `max_aggregate_chars`, or split the content into chunks and emit per-chunk `multi_cell` calls (same output, flatter CPU/memory). Do **not** change the builder's output semantics without an export-diff check.

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

### 🟢 P-8 — No index on `workspace_id` for the workspace-scoped tables
- **Where:** only `generation_jobs` has indexes (`db/models/generation_job.py:26,45` + migration `d4e5f6a7b8c9`). `standard_documents`, `brds`, `project_knowledge`, `document_extractions` carry FKs with **no** index — Postgres does not auto-index foreign keys.
- **Correction (2026-10-19, verified via `pg_indexes` while measuring R-1):** `workspaces.user_id` is **not** unindexed — `uq_workspaces_user_lower_name ON workspaces (user_id, lower(name))` has `user_id` as its leading column, so `WHERE user_id = ?` can use it. Drop that table from the migration; the other four still need it.
- **Impact:** every status poll (see P-4), Q&A ask, extraction run, and document listing filters on `workspace_id` → sequential scan once the tables grow. Negligible at demo scale, a real cost beyond it.
- **Safe change:** one Alembic migration adding five indexes (reversible downgrade, no data change).

### 🟢 P-9 — Q&A reads every document's full content on each question
- **Where:** `server/app/services/brd_qa_service.py:72-76` → `get_all_by_workspace_id` (full rows, deferred `content` **not** applied) before scoring relevance; only `MAX_RELEVANT_SOURCES = 8` × `MAX_SOURCE_CONTENT_LENGTH = 12000` reach the prompt.
- **Impact:** up to ~5 MB read and scored in Python per question, discarded down to ≤96 KB. The Gemini call still dominates the user-visible time, so this is low severity.
- **Safe change:** score from summaries/metadata (the same deferred-content projection as P-4/M-3), then fetch content only for the selected ids.

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

**Next — measured, one workspace at a time**
6. **P-1** (thinking budget + timeout/retry) — run the §6 timing first, then A/B it and confirm output quality on one real workspace.
7. **P-8** (indexes, reversible migration — no dependency on the above).

**Conditional / deferred**
8. **P-2** — only if §6 shows the PDF build is material; then chunk the `multi_cell` or lower the aggregate budget.
9. **P-6** (background ingestion needs a processing state + contract change).
10. **P-9** (Q&A summary-first scoring — low payoff until workspaces get large).
11. **R-1** (§8, logged 2026-10-19) — Supabase region round trips behind the ~1 s `/workspaces` load. **Deferred by user request** ("we will look at this later"); measurements and the three options are recorded in §8 so it can be picked up without re-measuring.

**Discipline for every item:** no route/schema/status change; no client change; server diff → **restart the backend**; run `pytest` (126 after Batch E), `npm run lint`, `npm run build`; update AGENTS.md + this file per the established per-batch pattern.

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

---

## 7. Notes on process

- This pass was **read-only**; `git status` showed only the pre-existing uncommitted Batch D changes.
- Severities assume the documented single-process deployment (`uvicorn app.main:app`, no `--workers`). Under multi-worker, P-4/P-5 overhead multiplies and the in-process job posture already fails (M-7).
- Line numbers refer to the working tree as of 2026-10-19 and will drift after edits.

---

## 8. R-1 — `/workspaces` takes ~1 s because of Supabase round trips (measured, **deferred 2026-10-19**)

**Symptom reported:** the workspaces page takes about a second to load.

**Verdict:** not React, not the query, not the payload. It is **network round-trip count to a database in another region**. Measured on this checkout against the live dev database (`DATABASE_URL` → `aws-0-ap-northeast-2.pooler.supabase.com`, i.e. **Seoul**) while the user is in India. **No file was modified** — this section is a record so the work can be picked up later without re-measuring.

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
