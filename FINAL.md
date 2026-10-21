# FINAL.md — Path to v1.0

Living tracker for everything required to call this project **finished** and presentable.
Work top to bottom. Update the checkbox and the change log as items land.

- **Owner:** you
- **Created:** 2026-10-21
- **Current test baseline:** server **186 passed**, client **0 tests** (no test tooling installed)
- **Audit status:** `ISSUES.md` v1 **22/22 closed**, v2 **10/10 closed or resolved**, R-1 resolved. **Nothing open.**

---

## 0. Locked decisions

These are settled — do not re-litigate them mid-batch.

| Decision | Value |
|---|---|
| Evaluator shape | Standalone CLI harness **plus** a dev-only API route and dev-only client page |
| Production exposure | Evaluator routes are **mounted only when `settings.environment != "production"`**. Never part of the product surface. |
| Live Sarvam budget | **6 jobs** acceptable for the first full run (3 scenarios × 2 repeats). Everything after that uses replay. |
| Harness in git | **Yes** — commit datasets, metrics, runner, reports code. Only run outputs are gitignored. |
| A/B comparison | **In scope.** Generator configs (`thinking_budget`, model) must be comparable on identical input. |
| Storage for eval results | Files on disk under `server/evals/reports/<run-id>/`. **No DB migration, no schema change.** |
| Evaluation is not a product feature | No client bundle growth in production builds; the page must be dev-gated (`import.meta.env.DEV`). |

---

## 1. Definition of done for v1.0

- [ ] **D1** Server suite ≥ **200 tests** green from `server/`
- [ ] **D2** Client suite ≥ **20 tests** green, `npm test` wired
- [ ] **D3** `npm run lint` clean and `npm run build` green
- [ ] **D4** CI workflow runs server tests + client lint/build/test on every push
- [ ] **D5** Evaluator produces a report for **3 scenarios** with coverage, faithfulness, structure, duplication and per-stage latency
- [ ] **D6** A/B report comparing at least two generator configs on identical input
- [ ] **D7** Evaluator routes verified **absent** when `ENVIRONMENT=production`
- [ ] **D8** Demo workspace seeded; full flow rehearsed end to end against a running backend
- [ ] **D9** `README.md`, `AGENTS.md` and this file updated to reflect reality
- [ ] **D10** No open findings in `ISSUES.md` (already true — keep it true)

---

## 2. Carried over from ISSUES.md / AGENTS.md

- **Nothing is open in `ISSUES.md`.** v1 22/22 and v2 10/10 are closed or resolved with measurements. If a future review reopens anything, log it here **and** in `ISSUES.md`.
- **Carried from `AGENTS.md` → Known Gaps:**
  - [ ] **C1** `client/DESIGN.md` shows as user-modified (spec updates) and is stale. Decide: finish the spec or delete it. **Never edit unprompted.**
  - [ ] **C2** "Polish: none committed — next is user-directed." Resolve by this file; close the line when D1–D8 are done.
- **Deliberately not carried (decided):**
  - P-10 root cause (Sarvam emits duplicate items) — dedup at consolidation is sufficient; storing clean extractions buys DB size only.
  - P-6 Track B (background ingestion) — measured at **3.3 s** worst case; does not pay for its contract change.

---

# BATCH K — Evaluator engine

Goal: prove the pipeline produces **good output**, not just fast output — with reproducible numbers.

## K1 — Package skeleton and CLI

- [ ] Create `server/evals/__init__.py`, `run.py`, `runner.py`, `report.py`
- [ ] CLI: `python -m evals.run --scenario all --repeats 2 [--replay|--refresh] [--out DIR]`
- [ ] Per-stage timing collected with `time.perf_counter()`; stages: `parse`, `aggregate_pdf`, `extraction`, `consolidation`, `generation`, `scoring`
- [ ] Exit non-zero on any scenario failure; never silently continue
- **Files:** `server/evals/*`
- **Acceptance:** `python -m evals.run --help` works with no DB connection and no API call.

## K2 — Datasets and ground truth

- [ ] `server/evals/datasets/<scenario>/inputs/*.md` — 2–3 short docs per scenario (1–2 pages each)
- [ ] `server/evals/datasets/<scenario>/expected.json` — 12–15 atomic facts, each with synonym groups:
      `{"id":"f1","text":"Users sign in with Google SSO","groups":[["sso","single sign-on","google"]]}`
- [ ] Three scenarios, different domains:
  - [ ] `checkout-redesign` (product brief + meeting notes + support themes)
  - [ ] `clinic-booking` (requirements doc + stakeholder transcript)
  - [ ] `helpdesk-migration` (memo + runbook)
- **Acceptance:** each `expected.json` validates against a small schema check in tests (unique ids, non-empty groups).

> This is the biggest single time sink in Batch K — roughly half the batch. Facts must be **unambiguous** in the inputs, or coverage scores become noise.

## K3 — Metrics

- [ ] `metrics/coverage.py` — recall over `expected.json`; a fact matches when **every** group has ≥1 alternative present (case/whitespace-normalized). Emit per-fact detail.
- [ ] `metrics/faithfulness.py` — per BRD item, share of distinctive content words present in the source corpus; flag items below threshold (default 0.5) with samples. **Label as a heuristic in the report.**
- [ ] `metrics/structure.py` — 11 sections present and non-empty; run `validate_brd_data()`; item counts per section.
- [ ] `metrics/duplication.py` — exact-duplicate rate across all list fields (canonical-key approach).
- [ ] `metrics/latency.py` — per-stage median, cold vs warm, end-to-end; token split (prompt/output/thoughts).
- [ ] Add `last_usage: dict | None` to `GeminiBRDGenerator` (set after each call, non-breaking) so tokens are read programmatically instead of scraped from logs.
- **Acceptance:** every metric returns a plain dict, is unit-tested, and never raises on an empty/partial BRD.

## K4 — Runner and replay cache

- [ ] `runner.py` replicates the real pipeline **without the DB**:
      parse → `ProjectDocumentBuilder` → `SarvamExtractor` → `DocumentKnowledgeMapper` → `KnowledgeConsolidator` → `GeminiBRDGenerator`
- [ ] `--replay` reads a cached raw Sarvam response from `server/evals/.cache/<scenario>-<input-hash>.json`; `--refresh` overwrites it
- [ ] Cache key includes a hash of the input documents so edited fixtures invalidate automatically
- [ ] Optional `--no-dedupe` (implemented **in the runner**, never by changing production consolidation) for the dedup A/B
- **Acceptance:** a full `--replay` run touches no network except the Gemini call; a `--replay` run is reproducible in its structure (coverage may vary — that is why repeats exist).

## K5 — Reports

- [ ] `report.py` writes `report.md`, `report.html`, `results.json` per run
- [ ] Markdown: per-scenario tables (coverage %, unsupported items, section fill, dup rate, latency by stage)
- [ ] HTML: self-contained (inline CSS, CSS-bar charts, no JS dependency, no CDN) so it opens from disk during the presentation
- [ ] Report states run mode (cold/warm), repeats, model, thinking budget, and the timestamp
- **Acceptance:** `report.html` renders standalone with the network disabled.

## K6 — A/B comparison

- [ ] `--compare results-a.json results-b.json` → side-by-side table: coverage, unsupported %, dup rate, tokens, latency per stage
- [ ] First A/B to run: **`thinking_budget=0` vs `2048`** on identical replay input
- [ ] Second (optional): dedup on/off via `--no-dedupe`
- **Acceptance:** the comparison is generated by the tool, not hand-assembled.

## K7 — Dev-only route and page

- [ ] `server/app/api/routes/evals.py` with:
  - `GET  /evals/scenarios`
  - `POST /evals/run` → **202** + run id, executed via `BackgroundTasks` (a 3-scenario run is minutes, not seconds)
  - `GET  /evals/runs` and `GET /evals/runs/{run_id}`
- [ ] Mount in `main.py` **only if** `settings.environment != "production"`; log one line at startup saying the eval routes are enabled
- [ ] Reuse `get_current_db_user` (no new auth rules, no anonymous surface)
- [ ] Results read from disk under `server/evals/reports/`; no DB writes
- [ ] Client `/evals` page gated on `import.meta.env.DEV`: scenario list, Run button, run table, link to `report.html`
- **Acceptance:** with `ENVIRONMENT=production`, `GET /evals/scenarios` returns **404/405**, and the client chunk is absent from the production bundle.

## K8 — Tests (offline)

- [ ] `server/tests/test_evals_metrics.py` — coverage matching (synonyms, case, partial groups), faithfulness flags, structure on partial BRD, duplication
- [ ] `server/tests/test_evals_runner.py` — fake extractor + fake generator, asserting stage timings are recorded and `--replay` hits the cache
- [ ] `server/tests/test_evals_route.py` — route **absent** when environment is production; present otherwise
- [ ] No network, no DB, no Sarvam/Gemini calls in any test
- **Acceptance:** suite stays under ~2 s added runtime.

## K9 — Docs and ignore rules

- [ ] `README.md` → "Evaluation harness" section: what it measures, how to run it, cost warning for live runs
- [ ] `AGENTS.md` → closed entry + test counts + the invariant that eval routes are dev-only
- [ ] `.gitignore` → `server/evals/reports/`, `server/evals/.cache/`
- [ ] Update §2 of this file

---

# BATCH L — Frontend tests

Goal: cover the largest untested surface in the project. Currently **zero** test files and no `test` script.

## L1 — Tooling

- [ ] Install dev deps: `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`
- [ ] `vite.config.ts` → `test` block (`environment: "jsdom"`, `setupFiles`, `globals: true`)
- [ ] `src/test/setup.ts` → `@testing-library/jest-dom` + cleanup
- [ ] Scripts: `"test": "vitest run"`, `"test:watch": "vitest"`
- **Acceptance:** `npm test` runs and reports "no tests" without configuration errors before L2 lands.

## L2 — Make pure logic testable (behavior-preserving extraction)

These are module-local today; extract without changing behavior.

- [ ] `safeExportFilename` → `src/lib/files.ts`
- [ ] `errorDetail` → `src/lib/errors.ts`
- [ ] `findDuplicateUpload` + `DuplicateMatch` → `src/lib/uploadDedup.ts`
- [ ] `mapJobPhaseToStep` → `src/lib/generation.ts`
- [ ] Any `docMeasure`/layout helper out of `BRDViewer.tsx` → `src/lib/layout.ts`
- **Acceptance:** `npm run build` and `npm run lint` green after each move; `WorkspacePage.tsx` shrinks; no behavior change.

## L3 — Unit tests

- [ ] `files.ts` — spaces, slashes, emoji, empty name, duplicate extension
- [ ] `errors.ts` — Axios error with `detail`, plain Error, non-object, 409 shape
- [ ] `uploadDedup.ts` — in-batch duplicate (hard error) vs stored duplicate (replace dialog), name/type/size keying
- [ ] `generation.ts` — every server phase maps to the expected step; unknown phase falls back
- [ ] `api/googleReconnect.ts` — `isGoogleReconnectRequiredError` / `throwIfGoogleReconnectRequired`
- **Acceptance:** no React rendering needed; fast.

## L4 — Component tests (highest value first)

- [ ] `BRDQAPanel` — optimistic user message appears before the request resolves; on failure the message is rolled back **and the composer text is restored**; sources render with `source_type`
- [ ] `WorkspacePage` — duplicate-upload Replace flow calls delete **then** upload (order asserted); delete tracking disables only the affected row
- [ ] `WorkspacePage` — Generate/Regenerate disabled while `generationStep !== "idle"`
- **Setup:** `QueryClientProvider` wrapper + `vi.mock("@/api/...")`; no real network, no Supabase
- **Acceptance:** each test fails if the behavior it guards is removed.

## L5 — Optional (only if time allows)

- [ ] Accessibility smoke: `@testing-library/jest-dom` role/label assertions on the workspace shells
- [ ] Coverage report in CI (informational, no threshold gate)

---

# BATCH M — CI and demo readiness

## M1 — CI

- [ ] `.github/workflows/ci.yml`
  - job `server`: Python 3.11, `uv pip install -r requirements.txt -r requirements-dev.txt`, `pytest` from `server/`
  - job `client`: Node 20, `npm ci`, `npm run lint`, `npm run build`, `npm test`
  - pip + npm caching
- [ ] **No secrets required** — the suite is hermetic (no Sarvam/Gemini/Supabase calls)
- **Acceptance:** a push with a deliberate failure fails the build; a clean push is green.

## M2 — Demo seed

- [ ] `server/scripts/seed_demo.py` (or equivalent) creating a demo workspace with 3–4 realistic documents for the signed-in account
- [ ] Idempotent: running twice does not duplicate sources
- [ ] Documented one-liner in `README.md`
- **Acceptance:** clean database → seed → workspace shows sources → Generate produces a BRD.

## M3 — Rehearsal

- [ ] Cold start from `.env.example` per README (backend + client)
- [ ] Full flow: create workspace → upload → generate → view → export PDF/DOCX → add source → regenerate → Q&A
- [ ] Run the evaluator live once (**6 Sarvam jobs**) and keep the report
- [ ] Record real end-to-end numbers for the presentation: extraction ≈ 20 s, consolidation ≈ 0, generation ≈ 14 s, total ≈ 34 s
- **Acceptance:** rehearsal completed twice with no manual intervention.

## M4 — Docs pass

- [ ] `README.md` reflects every shipped command (eval, seed, test)
- [ ] `AGENTS.md` closed entries for K/L/M, test counts accurate
- [ ] This file: all boxes checked or explicitly deferred with a reason

---

## 3. Known limitations to state honestly

Write these on a slide rather than let an examiner find them:

1. **Coverage is keyword ground truth.** Synonyms must be enumerated per fact; a correct paraphrase using none of them scores as a miss.
2. **Faithfulness is a lexical heuristic**, not entailment. It flags *suspect* claims for review, not proven hallucinations.
3. **Gemini is non-deterministic.** Coverage and latency vary per run — always report repeats and variance, never a single lucky run.
4. **~20 s of every generation is a vendor round trip** (Sarvam). The codebase cannot optimize it; only input size is a lever.
5. **Single-process deployment.** Rate limits, OAuth verifiers and in-process generation do not survive multi-worker scaling (documented in `README.md` → Deploy).
6. **Evaluator is dev-only.** The report is not available in production by design.

---

## 4. Out of scope for v1.0

- P-10 root cause (dedup at consolidation is sufficient)
- P-6 Track B (background ingestion — measured unnecessary)
- BRD version history / diff UI
- Docker, multi-worker, Redis-backed rate limits
- Any production exposure of the evaluator

---

## 5. Verification commands

```bash
# Server
cd server
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_evals_metrics.py tests/test_evals_runner.py
.venv/bin/python -c "from app.main import app; print(len(app.openapi()['paths']))"

# Evaluator
.venv/bin/python -m evals.run --scenario all --repeats 2 --refresh   # 6 Sarvam jobs
.venv/bin/python -m evals.run --scenario all --repeats 3 --replay    # free
.venv/bin/python -m evals.run --compare evals/reports/A/results.json evals/reports/B/results.json

# Client
cd client
npm run lint
npm run build
npm test
```

Production gate check:

```bash
cd server
ENVIRONMENT=production .venv/bin/python -c "from app.main import app; print([r.path for r in app.routes if 'evals' in r.path])"   # expect []
```

---

## 6. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Ground-truth authoring takes longer than the code | Batch K slips | Author datasets **before** metrics; they are the long pole |
| Sarvam/Gemini flakiness during a live run | 503s, partial scenario | Replay mode; retries already explicit in both clients |
| Eval route accidentally mounted in production | Dev tooling exposed | Explicit gate + `test_evals_route.py` asserts absence |
| Client test setup fights Vite/TS config | Batch L stalls | Land L1 alone first and confirm an empty run before writing tests |
| Coverage metric gamed by the model's verbosity | Inflated numbers | Report per-fact detail, not just the aggregate; include unsupported-claim count alongside |

---

## 7. Change log

| Date | Change |
|---|---|
| 2026-10-21 | File created. Batches K/L/M defined. Decisions locked. ISSUES.md confirmed at 0 open items. |
