# FINAL.md — Path to v1.0

Living tracker for everything required to call this project **finished** and presentable.
Work top to bottom. Update the checkbox and the change log as items land.

- **Owner:** you
- **Created:** 2026-10-21
- **Current test baseline:** server **291 passed**, client **0 tests** (no test tooling installed)
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
| Storage for eval results | Files on disk under `server/app/evals/reports/<run-id>/`. **No DB migration, no schema change.** |
| Evaluation is not a product feature | No client bundle growth in production builds; the page must be dev-gated (`import.meta.env.DEV`). |
| Automatic evaluation | **On by default in development**, off in production. It runs after every successful generation, costs zero extra API calls, and must never be able to fail a generation. |
| Fixture format | `.txt` — `ParserFactory` accepts only `.txt`/`.pdf`/`.docx`, so `.md` fixtures would bypass the real parser path. |

---

## 1. Definition of done for v1.0

- [x] **D1** Server suite ≥ **200 tests** green from `server/` — **291** as of 2026-10-22
- [x] **D2** Client suite ≥ **20 tests** green, `npm test` wired — **46** as of 2026-10-25
- [x] **D3** `npm run lint` clean and `npm run build` green — verified 2026-10-22
- [x] **D4** CI workflow runs server tests + client lint/build/test on every push — `.github/workflows/ci.yml`, 2026-10-25
- [x] **D5** Evaluator produces a report for **3 scenarios** with coverage, faithfulness, structure, duplication and per-stage latency
- [x] **D6** A/B report comparing at least two generator configs on identical input — K6, thinking 2048 vs 0
- [x] **D7** Evaluator routes verified **absent** when `ENVIRONMENT=production` (asserted by `test_routes_are_absent_in_production`)
- [x] **D8** Demo workspace seeded; full flow rehearsed end to end — **not pursued, by decision.** The demo uses real data already generated in the live workspace, so a seed script would add a second source of truth; the flow was verified against the deployed stack instead. Recorded rather than silently dropped.
- [x] **D9** `README.md`, `AGENTS.md` and this file updated to reflect reality — done with the deployment/CI close-out
- [x] **D10** No open findings in `ISSUES.md` (already true — keep it true)

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

Two tiers, because they answer different questions and only one of them needs a reference answer:

| | **Tier 1 — automatic** | **Tier 2 — benchmark** |
|---|---|---|
| Needs ground truth | No — the input knowledge *is* the reference | Yes (`expected.json`) |
| Runs on | Every real generation | 3 curated scenarios |
| Cost | **0 extra API calls**, milliseconds | 6 Sarvam + 6 Gemini jobs |
| Answers | "Did it drop or invent anything?" | "Did it capture what the documents said?" |

## K0 — Phase 0: the metrics (DONE 2026-10-22)

- [x] `server/app/evals/` package: `models.py`, `text.py`, `metrics/`
- [x] `metrics/structure.py` — wraps `validate_brd_data()`, never raises; counts survive a missing section
- [x] `metrics/retention.py` — token-overlap match against extracted requirements, threshold 0.6, dropped items keep their best match + score
- [x] `metrics/groundedness.py` — lexical support rate against the knowledge corpus, labelled `method: "lexical-overlap"`
- [x] `metrics/duplication.py` — case/whitespace/edge-punctuation only; **digits untouched**
- [x] `metrics/latency.py` — per-phase median/min/max, `n` reported so a single run is never mistaken for a distribution
- [x] `GeminiBRDGenerator.last_usage` + optional `model` kwarg (additive)
- [x] 23 tests (20 metrics + 3 generator); suite **186 → 209**
- **Acceptance met:** no DB, no network, no FastAPI in any metric; `BRD_LIST_FIELDS` drift guard against `schemas.brd._REQUIRED_BRD_LISTS`.

## K1 — Package skeleton and CLI — DONE 2026-10-22

- [x] `app/evals/run.py` (CLI), `runner.py`, `report.py`, `compare.py`, `datasets.py`
- [x] CLI: `--scenario <names...>|all`, `--repeats N`, `--replay`, `--thinking-budget N`, `--model NAME`, `--no-dedupe`, `--out DIR`, `--compare A B`, `--list`
- [x] Per-stage timings: `parse`, `aggregate_pdf`, `extraction`, `consolidation`, `generation`, `scoring`
- [x] Exit codes: 0 ok, 1 a scenario failed, 2 bad usage/malformed dataset
- **`--refresh` was dropped**: live mode always re-extracts and rewrites the cache, so a separate "ignore the cache" flag had no meaning. `--replay` is the only cache control.

## K2 — Datasets and ground truth — DONE 2026-10-22

- [x] `app/evals/datasets/<scenario>/inputs/*.txt` — 2–3 documents each (1–2 pages)
- [x] `expected.json` per scenario, with synonym groups
- [x] Four scenarios: `checkout-redesign` (15 facts, 3 docs), `clinic-booking` (14, 2), `helpdesk-migration` (14, 2), plus `smoke` (4, 1) used to validate the plumbing before any authoring
- [x] Load-time validation: unique ids, non-empty phrasing groups, at least one document, `.txt`/`.pdf`/`.docx` only — **before** any API budget is spent
- **Acceptance met:** loading an invalid scenario fails with a message naming the fact.

## K3 — Metrics — DONE 2026-10-22

- [x] `metrics/coverage.py` — fact recall; every group must have ≥1 alternative; emits `missed[].missing_groups`
- [x] `metrics/groundedness.py` — the renamed "faithfulness" metric; lexical support rate, labelled `method: "lexical-overlap"`
- [x] `metrics/structure.py`, `metrics/duplication.py`, `metrics/latency.py`
- [x] `last_usage` on `GeminiBRDGenerator`
- [x] `metrics/retention.py` — added in K0
- **Correction from real data (2026-10-22):** retention as first written was wrong. It matched each source requirement against a *single line in one section* with surface-form tokens, and every one of 13 "dropped" requirements across three live runs was a false positive — the model had merely rewritten them ("is converted into a ticket" → "shall automatically convert emails ... into new tickets"). Two fixes: **light stemming** (`converted`/`convert`, `tickets`/`ticket`) and **corpus scoring with per-line reporting** (score against all requirement sections, report the closest single line). Verified by re-scoring the stored BRDs: all 13 became retained.
- **Deliberate scoping:** matching covers the requirement sections only. A requirement that survives merely as a mention inside `risks_and_decisions` is *not* retained — tested.

## K4 — Runner and replay cache — DONE 2026-10-22

- [x] DB-free replica: `DocumentIngestionService` → `ProjectDocumentBuilder` → `SarvamExtractor` → `SarvamKnowledgeMapper` → `KnowledgeConsolidator` → `GeminiBRDGenerator`
- [x] `--replay` reads `.cache/<scenario>-<sha256(inputs)[:12]>.json`; a live run writes it through the extractor's existing `output_path`
- [x] Cache key hashes the input **bytes**, so editing a fixture invalidates it
- [x] `--no-dedupe` implemented in the runner only
- **Two documented omissions:** the private `_fit_to_aggregate_budget` is not reproduced (fixtures are ~1–4k chars against a 1M budget; a fixture that would exceed it **fails loudly** instead of silently measuring a different pipeline), and multi-document consolidation is not exercised because production takes the single-document path too.
- **`results.json` stores the BRD.** A score you cannot inspect against the document that produced it is not evidence — and this is what made the retention bug diagnosable without a second paid run.

## K5 — Reports — DONE 2026-10-22

- [x] `results.json` + `report.md` + `report.html` per run under `app/evals/reports/<run-id>/`
- [x] HTML is self-contained: inline CSS, CSS-only bars, no JS, no CDN (asserted by test)
- [x] Records mode, model, thinking budget, dedupe, repeats and timestamp — a number is never quoted without its conditions
- **Fixed during the first real run:** booleans were being medianed, so `valid` rendered blank (`median(True, True)` → filtered out). Booleans now come from the first repeat.

## K6 — A/B comparison — DONE 2026-10-22

- [x] `--compare A B` prints a Markdown table; warns when the runs used different modes
- [x] First A/B measured: **thinking 2048 (live) vs thinking 0 (replay)** on the same cached extraction — recall and retention **identical** (1.0 / 0.857-1.0), unsupported items **87% worse** with thinking off (0.087 → 0.163), generation stage **38.7% faster** (18.0 s → 11.1 s)
- [x] Second (optional): dedup on/off via `--no-dedupe` — **closed as already measured**, not re-run. Batch G recorded the before/after in `ISSUES.md` (147 → 71 and 120 → 48 items, 22.8 s → 14.4 s with thinking restored, `functional_requirements` = 15 in every configuration). Re-running it would reproduce a number that already exists, and `--no-dedupe` remains available in the runner for anyone who wants it.

## K7 — Dev-only routes and dashboard — DONE 2026-10-22

- [x] `app/evals/coordinator.py` — run lifecycle kept out of the router so the one-run rule has a single implementation
- [x] `GET /evals/scenarios` — name, facts, documents, chars, whether a cache exists (disk only)
- [x] `POST /evals/run` → **202** + run id, executed via `BackgroundTasks`; **409** when a run is already in progress
- [x] `GET /evals/runs`, `GET /evals/runs/{id}`, `GET /evals/runs/{id}/report.html`
- [x] `status.json` per run so progress survives a page refresh
- [x] Client `/evals` page (two tabs) and a dev-only **Evaluation** pill on the workspace utility bar
- [x] Report opened through the authenticated client and handed to the browser as a blob — a plain `window.open` would 401
- **OpenAPI:** 34 paths in development, **27 in production** (unchanged), asserted by test
- **Not a bare `threading.Lock`:** the slot is timestamped, so a request whose background task never ran cannot wedge the endpoint for the life of the process. A run still `running` after 15 minutes is reported as **interrupted** rather than spinning forever — that is what a mid-run restart looks like.
- **Bundle proof:** production build contains **zero** "evals" references (`grep -ril evals dist/assets`); the dev server serves the page (HTTP 200, transformed), so the lazy route is real rather than tree-shaken dead code.

## K8 — Tests (offline) — DONE 2026-10-22

- [x] `test_evals_metrics.py` (22), `test_evals_benchmark.py` (26), `test_evals_generation.py` (20)
- [x] No network, no DB, no provider calls: the extractor and generator are injected
- [x] Suite stays under 2 s added runtime
- **Acceptance met:** replay is asserted to call the extractor **zero** times.

## K9 — Docs and ignore rules — DONE 2026-10-22

- [x] `README.md` → "Evaluation harness" section (`README.md:201`)
- [x] `AGENTS.md` → closed entries for K0–K5 (`AGENTS.md:251–330`)
- [x] `.gitignore` → `server/app/evals/reports/`, `.cache/`, `generations/`
- [x] Update §2 of this file

## K10 — Automatic evaluation on every generation (Tier 1) — DONE 2026-10-22

- [x] Collect phase timings in `generation_job_service.py` — `_log_phase` now logs *and* records into a dict from the same measurement (two timers would eventually disagree)
- [x] `_set_phase(job, STATUS_SUCCEEDED, None)` → `succeeded = True`; the recorder runs **after** the try/except, gated on that flag
- [x] One JSON per job in `app/evals/generations/` (last 50, no DB, no migration), written by `evals/store.py`
- [x] `try/except` in `_record_evaluation` outside the job's error handling — a scoring failure logs a warning and cannot fail a generation
- [x] Gated on `settings.environment != "production"` + `eval_on_generation` (default **on**)
- [x] Dev-only `GET /evals/generations` and `GET /evals/generations/{id}` via `register_eval_routes`
- [x] **Bonus:** `tests/conftest.py` makes the suite hermetic — it previously imported `app.main` and only worked because a local `.env` existed, which would have broken CI
- **Verified:** 209 → **229 tests**, suite green with `server/.env` renamed away, 29 OpenAPI paths in dev / **27 in production**

> Note: the benchmark routes (`POST /evals/run`, `/evals/runs`) are still K7 — this only shipped the two read endpoints Phase 1 needs to be observable.

## K11 — Dashboard (Tier 1 + Tier 2 in one place) — DONE 2026-10-22

- [x] `/evals` client page, dev-gated (`import.meta.env.DEV`) and behind `RequireAuth`
- [x] **Tab 1 — Benchmark:** latest runs, fact recall, latency percentiles, link to `report.html`, "Run benchmark" button with a cost confirmation ("6 Sarvam jobs, ~5 min")
- [x] **Tab 2 — Your generations:** last N real runs with health-check numbers, row detail
- [x] Dev-only "Evaluation" pill on the workspace page after a successful generation → `/evals?workspace=…`
- [x] Verify `grep -ril "evals" client/dist/assets` returns nothing after `npm run build`
- [ ] **Exception — the A/B table is not in the tab.** Comparison lives in the CLI (`--compare`) and in `report.html`. Deferred deliberately: it needs a new compare route plus diff logic to answer a question the HTML report already answers, and the dashboard's job is the per-generation numbers. Not a K11 blocker.
- **Acceptance:** the dashboard shows real numbers, not "0 of 0 expected facts" — the benchmark must have been run at least once before the review.

---

# BATCH L — Frontend tests — DONE 2026-10-25

Goal: cover the largest untested surface in the project. It was **zero** test files and no `test` script; it is now **46 tests** across 7 files, wired to `npm test`.

## L1 — Tooling

- [x] Install dev deps: `vitest` 5.0.5, `jsdom` 30, `@testing-library/react` 16, `@testing-library/user-event` 14, `@testing-library/jest-dom` 7
- [x] **`vitest.config.ts`, not `vite.config.ts`** — deliberately separate, because the build config owns the `manualChunks` split for the production bundle and tests must not be able to change what ships. Vitest 5 accepts Vite 8, so no version pinning was needed (the risk that would have blocked this).
- [x] `src/test/setup.ts` → jest-dom matchers + `cleanup()` + the three jsdom gaps the app actually hits (`scrollIntoView`, `crypto.randomUUID`, `URL.createObjectURL`). Without them the failure looks like a bug in the component rather than a missing browser API.
- [x] Scripts: `"test": "vitest run"`, `"test:watch": "vitest"`
- **Acceptance met:** proven with a throwaway toolchain test before any real test was written.

## L2 — Make pure logic testable (behavior-preserving extraction)

These are module-local today; extract without changing behavior.

- [x] `safeExportFilename` + `downloadBlob` → `src/lib/files.ts`
- [x] `errorDetail` → `src/lib/errors.ts`
- [x] `findDuplicateUpload` + `DuplicateMatch` → `src/lib/uploadDedup.ts` — gains an explicit `documents` parameter instead of closing over component state, which is what made it untestable
- [x] `mapJobPhaseToStep` → `src/lib/generation.ts`
- [x] `docMeasure` → `src/lib/layout.ts` as `documentMeasure(sourcesOpen, qaOpen)` (it lives in `WorkspacePage`, not `BRDViewer`)
- **Beyond the list:** the upload pre-check became `validateUploadSelection(files)`, and the L-7 delete-then-upload sequence became `replaceStoredSource(...)`. The second one matters — it is the only cheap way to assert an ordering invariant without rendering a 2,000-line page.
- **Acceptance met:** `build` and `lint` green after every move; `WorkspacePage.tsx` 2,224 → 2,107 lines; messages kept byte-identical (asserted in tests).

## L3 — Unit tests

- [x] `files.ts` (9) — spaces, slashes, quotes, control chars, leading dot, 80-char cap, emoji, empty name, `downloadBlob` URL lifecycle
- [x] `errors.ts` (5) — string `detail`, non-string `detail`, missing response, plain Error, non-error values
- [x] `uploadDedup.ts` (14) — in-batch duplicate is a hard error, stored match returns its id, size and extension mismatches, case-insensitive extension, the 10MB boundary (exactly 10MB passes), and the replace ordering (upload never before delete resolves, never after a failed delete)
- [x] `generation.ts` (3) — every phase, `null` while queued, unknown phase falls back to the first step
- [x] `api/googleReconnect.ts` (7) — 409 on the same connector throws, a 409 belonging to the *other* connector is ignored (connecting Drive must not tear down Gmail), missing flag, other statuses, non-axios
- [x] `layout.ts` (3) — 1024 / 880 / 720 for the rail combinations
- **Acceptance met:** 41 of the 46 tests render nothing; the whole suite runs in ~1 s.

## L4 — Component tests (highest value first)

- [x] `BRDQAPanel` (6) — optimistic bubble before the request resolves, answer paragraphs, sources with `source_type`, rollback **and** composer restore on failure, empty submit ignored, only one send while in flight, clear
- [x] Replace ordering — asserted through the extracted `replaceStoredSource` rather than a page render. Two tests: upload is not called while the delete is pending (and is called after it resolves), and a failed delete never uploads. **Not** covered: delete tracking disabling only the affected row.
- [ ] **Deferred:** Generate/Regenerate disabled while `generationStep !== "idle"`. This is inline JSX in a 2,107-line page that needs auth context, a router, and six mocked queries. Skipped deliberately: the harness would be more fragile than the assertion is valuable, and the guard is one `disabled` prop on a button that is already exercised by hand every generation. Revisit only if that button misbehaves.
- **Setup as planned:** `QueryClientProvider` wrapper + `vi.mock("@/api/brd")`. No network, no Supabase. Env placeholders live in `vitest.config.ts` because `@/lib/supabase` throws at import time without them.
- **Acceptance:** each test fails if the behavior it guards is removed.

## L5 — Optional (only if time allows)

- [ ] **Deferred (optional):** accessibility smoke — role/label assertions on the workspace shells.
- [ ] **Deferred (optional):** coverage report in CI (informational, no threshold gate).

---

# BATCH M — CI and demo readiness (M1 shipped; M2/M3 declined by decision)

## M1 — CI

- [x] `.github/workflows/ci.yml`
  - job `server`: Python **3.11** (matches the local venv and `PYTHON_VERSION` on Render), `pip install -r requirements.txt -r requirements-dev.txt`, `python -m pytest -q` from `server/`
  - job `client`: Node **22** (matches `NODE_VERSION` on Cloudflare Pages — the plan said 20, but 22 is what the deployed build uses, and Vite 8 needs ≥ 20.19), `npm ci`, `npm run lint`, `npm test`, `npm run build`
  - pip + npm caching, `timeout-minutes: 10` per job, `concurrency` with `cancel-in-progress` so two quick pushes cannot queue two full runs
- [x] **No secrets required** — the suite is hermetic (`tests/conftest.py` sets placeholder values for all ten required settings, so nothing reaches Supabase, Sarvam or Gemini)
- [x] **CI is a gate, not a deployer.** Render and Cloudflare Pages both auto-deploy on push to `main`, so a failing run does not block a deploy that has already shipped. Toggle Render's *Auto-Deploy → After CI Checks Pass* if that ordering ever matters.
- **Acceptance:** met by inspection — the workflow is the same two commands that are green locally (291 + 46); a deliberate-failure drill is the one part not exercised.

## M2 — Demo seed

**Declined by decision (2026-10-25).** Not built.

- [x] `server/scripts/seed_demo.py` — **not written.** The demo runs against real sources already in the live workspace; a seeded copy would be a second, diverging dataset and one more thing to explain during a walkthrough.
- [x] Idempotency — moot without the script.
- [x] Documented one-liner — moot.

## M3 — Rehearsal

**Declined as a formal rehearsal (2026-10-25).** The deployed stack was verified instead — see below.

- [x] Cold start — covered by the free-tier deployment itself: a first request after idle is the cold-start case, and it is why `/health` is pinged every 10 minutes.
- [x] Deployment verified end to end from outside: `/health` 200 (`environment: production`), `/health/database` 404, `/evals/*` 404, unauthenticated `/workspaces` 401, SPA deep link 200, CORS preflight 200 for the Pages origin, `VITE_API_URL` baked with zero `localhost` hits.
- [x] Google Drive **picker and import** verified in production (2026-10-26): the Picker opened against the Pages origin and a real Drive file imported into Sources. This closes the smoke test the M-2 batch left open — the streamed `MediaIoBaseDownload` path had only ever run against mocks, and it now has run against Google from Render's egress.
- [x] The evaluator still cannot run in production **by design** (`ENVIRONMENT=production` unmounts `/evals`). Any live benchmark run must happen locally; the last one is `app/evals/reports/20261022T151355`.
- [ ] Real numbers for the presentation — unchanged from the local measurements (extraction ≈ 20 s, consolidation ≈ 0, generation ≈ 14 s, total ≈ 34 s). Expected to be slower on Render's 0.1 CPU; not re-measured.

## M4 — Docs pass

- [x] `README.md` reflects every shipped command — `npm test` and the evaluation CLI are documented; no seed command exists to document. New **Current deployment** section records the hosting, the start command, and the five settings that fail without naming their cause.
- [x] `AGENTS.md` closed entries for K/L/M, test counts accurate — batch L and the deployment/CI entry added; 291 server + 46 client.
- [x] This file: all boxes checked or explicitly deferred with a reason.

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
| 2026-10-22 | **K0 (Phase 0) shipped:** five metrics + 2 additive generator changes, 186 → 209 tests. Added K10 (automatic evaluation, on by default in dev) and K11 (dashboard). Fixed fixture format `.md` → `.txt` (ParserFactory rejects `.md`) and moved the package to `server/app/evals/` so the dev-only route imports within `app`. |
| 2026-10-22 | **K5 shipped:** retention fixed for noun-phrase requirements (2/3 threshold, derivational stemming, `securely`/`secure`) after a real workspace reported 10 of 28 kept when the BRD contained them; generation records now store the BRD and knowledge so a metric change can be re-scored offline; verdict computed server-side; dashboard rewritten as one quiet sentence per generation with expandable evidence. 274 → **291 tests**. |
| 2026-10-22 | **K4 shipped:** benchmark re-cut into three source-density tiers (small/medium/large, 1/3/6 documents, 8/18/28 facts) with `level` driving order; retention broadened to whole-document matching after still flagging correctly re-homed requirements; Evaluation button aligned with Export; generations dashboard gained a median strip and expandable rows with counts. 273 → **274 tests**. |
| 2026-10-22 | **K7 (Phase 3) shipped:** `coordinator.py` run lifecycle, 5 new dev routes (scenarios / run / runs / run detail / report), 409 on concurrent runs, timestamped slot so an abandoned run cannot wedge the endpoint, `status.json` progress, two-tab `/evals` page and a dev-only workspace pill. OpenAPI 29 → **34 dev / 27 production**; production bundle contains zero eval references. 259 → **273 tests**. |
| 2026-10-22 | **K1–K6 + K8 (Phase 2) shipped:** benchmark runner, 4 validated scenarios (smoke + 3 domains), coverage metric, replay cache, `report.md`/`report.html`/`results.json`, and `--compare`. First A/B measured: thinking 0 is 38.7% faster than 2048 but has 87% more unsupported items, with recall/retention unchanged. Retention was corrected against real data (stemming + corpus scoring) after all 13 flags in three live runs proved to be rewording false positives. 229 → **259 tests**. |
| 2026-10-22 | **K10 (Phase 1) shipped:** phase timings recorded, evaluation hook on every successful generation, `app/evals/store.py` + `generations/`, dev-only list/detail eval routes, `register_eval_routes` gate, `eval_enabled` / `eval_on_generation` settings. 209 → **229 tests**; added `tests/conftest.py` so the suite no longer depends on a local `.env` (would have failed in CI). |
