# BRD-Agent — Read-Only Audit Report

- **Date:** 2026-09-30
- **Branch inspected:** `redesign/space` @ `a22b1ed` (working tree clean; `client/DESIGN.md` user-modified diff was present earlier — untouched per project rule)
- **Scope:** full repo (FastAPI `server/`, React/Vite `client/`, docs, config, tests, deps)
- **Method:** static review + verified runs. Nothing in the codebase was changed to produce this report. All "verified" claims below were reproduced against the checked-out code (`server/.venv`, Python 3.11.15).

---

## 1. Executive summary

The project is in good shape overall: authn/authz is consistent, hardening layers (upload caps, magic sniffing, rate limits, Fernet, RLS, OAuth PKCE/state) are real and tested, and the frontend is clean (lint green, build green). The audit's **3 high**, **9 medium**, and **10 low/hygiene** issues are now **100% closed — all 22 fixed.** H-1/H-2 (2026-10-10), H-3 (2026-10-11); M-3 (2026-10-10, `916a50b`), M-4 (2026-10-10, connector separation), M-1 (2026-10-18, verified-user rate-limit keying), M-6/M-8/M-9 (2026-10-19, self-contained parser tests, README truth, root `requirements.txt` removed), M-2 (2026-10-19, Gmail cap + streamed Drive download + aggregate extraction budget), M-5 (verified 2026-10-19 — the 2026-10-01 rebrand had already switched accent buttons to ink-on-coral, 5.95:1), M-7 (2026-10-19, single-worker deploy documented), L-10 (2026-10-19, deploy posture + `--shell-chrome` already-fixed item), L-1/L-2/L-3/L-5 (2026-10-19 Batch A+B: dead API surface deleted, stray test file moved, `aria-expanded` pair completed, empty-content guards on the txt/pdf parsers), L-4/L-6/L-7 (2026-10-19 Batch C: sentinel-based mobile auto-scroll, provider-error sanitization with raw detail moved to server logs, duplicate-upload Replace dialog) and L-8/L-9 (2026-10-19 Batch D: skills tree untracked + ignored, Gmail browse batched to one HTTP round trip). The dominant theme:

> **Export integrity and job lifecycle are the two weak surfaces.** A crash-class bug still exists in the PDF path (incomplete unicode normalization + a validation/mapper mismatch that lets structurally-broken BRD data reach both exporters), and generation jobs can wedge a workspace permanently after a server restart. Both are cheap to fix.

### Verification snapshot (run on this checkout)

| Check | Result |
|---|---|
| `server: .venv/bin/python -m pytest` | ✅ 31 passed |
| `client: npm run lint` | ✅ clean (exit 0) |
| `client: npm run build` | ✅ green (~258 ms, vendor chunks emitted) |
| Alembic | ✅ single linear head `62d4ff311943`, reversible downgrades |
| Secrets in git | ✅ none (`server/.env`, `client/.env.local` ignored; only `*.example` tracked) |
| 429 + `Retry-After` | ✅ reproduced end-to-end (`1/minute → Retry-After: 60`, `1/hour → 3600`) |
| Fresh-clone test run | ✅ green — `datasets/` dependency removed, parser tests are self-generating (M-6) |

---

## 2. Issues — priority order

Severity key: **H** = high (data-integrity / crash / availability / security-adjacent) · **M** = medium (correctness, abuse-resistance, accessibility, deploy risk) · **L** = low / hygiene.

---

### ✅ H-1 — PDF export can still crash on characters the normalizer doesn't map — FIXED 2026-10-10

- **Status:** fixed (uncommitted working tree at time of writing). `_normalize_text` map extended (~20 entries: arrows, `≥≤≠≈`, `€→EUR`, `✓/✗`, `√∞`, `▪◆™`, CJK punctuation) plus a terminal `encode("latin-1", errors="replace")` safety net, so unknown chars degrade to `?` instead of 500ing. Locked by `test_pdf_build_survives_unmapped_unicode` + `test_normalize_text_always_latin1_safe` in `server/tests/test_export_builders.py`. DOCX builder untouched (keeps real Unicode).
- **Original finding (for the record):**
- **Where:** `server/app/ai/builders/brd_document_builder.py:710` (`_normalize_text`)
- **Constraint:** fpdf2 2.8.8 core Helvetica supports U+0000–U+00FF only (AGENTS.md latin-1 rule; prior crash 2026-09-18).
- **Verified:** `_normalize_text` maps only 7 characters (`— – ' ' " " •`) plus a no-op `"..." → "..."`. Direct testing of the installed fpdf2 shows `FPDFUnicodeEncodingException` for at least these plausible LLM outputs, all of which **survive** the normalizer:

  `→ ≥ ≤ € ✓ ✗ ← ↑ ↓ √ ∞ ≠ ≈ ⇒ ▪ ◆ ™` and CJK punctuation `、 ，`
  (chars like `± ×` are in latin-1 and pass.)
- **Impact:** one `→` in a Gemini-generated requirement line → 500 on **Download PDF**, no BRD retrievable as PDF, error banner in-app. The existing regression test (`server/tests/test_export_builders.py:106` `test_pdf_build_survives_non_latin1_content`) only exercises the 6 mapped chars, so the suite stays green while real output can still crash.
- **Suggested fix (any one, in increasing robustness):**
  1. Extend the map with the common set above (`→ ->`, `≥ >=`, `≤ <=`, `€ EUR`, `✓ √`-free approximations, etc.).
  2. Belt-and-braces: after mapping, force `text.encode("latin-1", errors="replace").decode("latin-1")` (or a transliterate step) so **no** future char can ever reach fpdf2 un-mapped. This converts "unknown crash" into "visible `?`" permanently.
  3. Switch the BRD PDF to the `DejaVuSans.ttf` fonts already vendored at `server/app/ai/fonts/` (used by `project_document_builder.py`), which removes the latin-1 class entirely. Note: changes metric/typography posture of the export — bigger visual diff than options 1–2.
- Add a test case feeding an unmappable char (`→`) to lock the fix.

### ✅ H-2 — `validate_brd_data()` shape validation doesn't match `BRDMapper` → poisoned BRD breaks exports — FIXED 2026-10-10

- **Status:** fixed (uncommitted working tree at time of writing). `validate_brd_data` now requires all 11 sections plus exactly the mapper's hard reads (`executive_summary.content`, `project_overview.project_name/description`, per-entry stakeholder `name`, list-typed plural fields) — malformed PUTs 422 at the door. Both export service methods wrap `brd_mapper.map()` into a new `BRDMalformedError`, translated by both export routes to 422 with a "Regenerate the BRD" hint, so rows poisoned before the fix degrade gracefully instead of 500ing. Locked by new `server/tests/test_brd_shape.py` (11 tests). Verified: pytest 50 passed, route/service imports clean.
- **Original finding (for the record):**
- **Where:** `server/app/schemas/brd.py:79` (`validate_brd_data`) vs. `server/app/ai/mappers/brd_mapper.py:37` (`BRDMapper.map` — `data["content"]`-style hard key access)
- **Verified:** `PUT /workspaces/{id}/brd` with `{"executive_summary": {}, "project_overview": {}, ...}` (all 11 sections empty objects) **passes** `validate_brd_data` (it only checks section keys, dict-ness, depth ≤ 6, string ≤ 50k, total ≤ 1 MB), is persisted, and then `BRDMapper().map()` raises `KeyError: 'content'` — which is exactly what **both** export endpoints (`export_brd_pdf_for_user` / `export_brd_docx_for_user`) call on every request. The row is stuck: every PDF/DOCX download 500s until a regenerate overwrites it.
- **Impact:** any client bug, partial edit, or deliberate PUT can permanently break a workspace's exports (and the viewer renders from loosely-typed `brd_data` on the client, so the UI may half-work while downloads are dead).
- **Suggested fix (pick one or combine):**
  1. Mirror the 11-section shape in a Pydantic model and validate `PUT` bodies against it (strongest; keeps the API contract honest).
  2. Wrap `brd_mapper.map()` in the two export methods and return a clean 422/409 with a "regenerate required" hint when the stored document is malformed.
  3. Make mapper field reads `.get()`-tolerant with empty defaults (weakest — hides corruption rather than flagging it).

### ✅ H-3 — `generation_jobs` have no timeout/reaper → workspace wedged after restart; also a create-vs-create race — FIXED 2026-10-11

- **Status:** fixed. `GenerationJobService.reap_stale_jobs()` (timeout `generation_job_timeout_minutes=15`) runs lazily per workspace in `create_job_for_user` + `get_brd_status_for_user`; partial unique index (migration `b8c9d0e1f2a3`, applied, reversible) closes the race with IntegrityError-adopt; client shows a Retry watchdog after 20 min stalled. Locked by 9 new tests (incl. real-SQLite ghost drill); 70 passed, build/lint green.

- **Where:** `server/app/api/routes/brd.py:112` (`if job.status == "queued"` — only queued jobs ever get a background task), `server/app/services/generation_job_service.py` (no staleness handling anywhere), `GenerationJobRepository.get_active_by_workspace_id` (`status not in ("succeeded","failed")`)
- **Verified in code:** the pipeline runs in an in-process `BackgroundTasks` task. If the uvicorn process dies/restarts while a job is `queued`/`running`, the row is never terminalized. Every subsequent `POST /generate` finds that dead job "active", returns it with **status `running`**, and never starts work — while the frontend's reload-resume effect (`client/src/pages/WorkspacePage.tsx` ~line 633) adopts the ghost job and polls it every 2 s forever (no client-side timeout either). The workspace can never regenerate without manual DB surgery.
- **Race (same area):** two concurrent `POST /generate` can both pass the active-check (no unique partial index like `WHERE status IN ('queued','running')`), enqueueing two parallel pipelines; `save_brd` then double-writes (last commit wins, user edits silently lost).
- **Suggested fix:**
  1. On app startup (lifespan) — or in `get_brd_status_for_user` — reap jobs stuck in `queued/running` beyond a generous cap (e.g. > 15 min; Sarvam poll alone is ~2 min max, Gemini a bit more) → mark `failed` with `"Server restarted mid-run"`.
  2. Add a partial unique index enforcing one active job per workspace (migration), and treat `IntegrityError` as "adopt existing job" — closes the race.
  3. Optional: client-side watchdog — after N minutes of polling with no phase movement, surface "still running? Retry" instead of an eternal spinner.

---

### ✅ M-1 — Rate limiting is keyed on the bearer token hash, so it's trivially bypassed by refreshing — FIXED 2026-10-18

- **Status:** fixed. `get_current_user` now stashes the verified JWT `sub` on `request.state.user_id` (after signature/audience/issuer checks — an unverified `sub` is never trusted, so forged tokens can't aim a bucket at another user) and `rate_limit_key` keys on `user:<sub>`, falling back to remote address for headerless requests (Google OAuth callbacks — same bucketing as before). The `sha256(token)` key is gone: rotating/refreshing a token no longer resets a bucket. Verified safe by reading the installed slowapi source: for decorated routes the middleware defers to the endpoint decorator, which runs *after* FastAPI resolves `Depends(get_current_user)`, so the stash is always populated before the key func reads it. Locked by `server/tests/test_rate_limit.py` (5 tests: rotated-token regression, per-user bucket isolation, IP fallback, state-over-token keying, stash contract). Verified: pytest 75 passed.
- **Where (original):** `server/app/core/rate_limit.py:17` — `digest = sha256(token)` → `user:<digest>`
- **Verified (original):** Supabase access tokens rotate on every refresh (~hourly automatically, on demand via `refreshSession`), so the same user gets a **fresh counter per token**. The `5/hour` BRD-generate limit (the expensive LLM path) is defeatable by simply refreshing the session — or by the built-in 401-refresh-retry path in `client/src/api/client.ts`.
- **Fix (original):** resolve the user from the JWT `sub` claim in the key function (decode without verification *only* to read `sub` is unsafe for keying; better: the dependency already verifies — stash `user.id` on `request.state` in `get_current_user` and key on that, falling back to remote address).

### ✅ M-2 — Gmail / Drive imports bypass the extraction-size caps (and Drive buffers the whole file in RAM) — FIXED 2026-10-19

- **Status:** fixed, three-part.
  1. **Gmail cap:** `GmailImportService.import_messages` now rejects any message whose extracted body exceeds `settings.max_extracted_chars` with a `ValueError` ("Message too large: …"), and Gmail's import handler gained the `"too large" → 413` branch it was missing (`gmail/router.py`) so it matches the upload and Drive paths. The cap lives in the orchestration service, not `GmailEmailMapper`, keeping the mapper a pure transformer.
  2. **Drive streaming:** `DriveService.download_file` no longer buffers with a single `.execute()`. It streams via `MediaIoBaseDownload` into a bounded `io.BytesIO`, checking `buffer.tell()` after every chunk and raising once past `settings.max_upload_bytes` — so an oversized or mis-declared file is rejected without ever being fully resident in RAM. The "File too large" wording deliberately reuses the router's existing `"too large" → 413` mapping. The declared-size pre-check and the post-download length check both remain (cheap early reject + defense-in-depth). A `max_bytes` parameter was added for testability.
  3. **Aggregate budget:** new `max_aggregate_chars` setting (default **1,000,000**, in `config.py` + `.env.example`) bounds the total content fed to the single project PDF handed to Sarvam. `DocumentExtractionService._fit_to_aggregate_budget` includes documents in order, truncates the one that crosses the boundary with an explicit `[Content truncated to fit the extraction budget.]` marker, and **drops** the rest — which stay `is_extracted = False` so a later run picks them up once the budget frees up. `link_source_documents` and the `is_extracted` marking now use only the included ids (previously every row was marked extracted regardless, which would have silently lost the dropped ones).
  Locked by `server/tests/test_import_caps.py` (7 tests: Gmail reject + happy path, Drive abort-past-ceiling + allows-up-to-ceiling, aggregate under/over/zero budget). Verified: pytest **93 passed**.
- **Where (original):** `server/app/integrations/gmail/mapper.py:108` (`_extract_content` — no `max_extracted_chars` cap); `server/app/integrations/drive/service.py:191` (`download_file` — full `.execute()` into memory **before** the size re-check in `import_service.py`); `server/app/ai/builders/project_document_builder.py` (no caps on aggregate content)
- **Verified asymmetry (original):** the upload path enforces 10 MB / 500k chars / 200 pages at the parser, but email bodies and Drive files entered `standard_documents` with no character ceiling (Drive trusts the metadata `size` field, then buffers everything), and `content` is Postgres `Text` — unlimited. A 30 MB mail thread or a mis-declared Drive file flowed straight into the Sarvam project-PDF (and its cost) without the caps the upload path guarantees.
- **Fix (original):** cap Gmail-mapped content at `settings.max_extracted_chars` (reject or truncate+flag); stream Drive downloads with a hard byte ceiling (`MediaIoBaseDownload` with a max-bytes guard) instead of buffering.

### ✅ M-3 — `GET /workspaces/{id}/documents` returns full `content` for every source — FIXED 2026-10-10

- **Status:** fixed in commit `916a50b`. `StandardDocumentSummary` (no `content`) added in `server/app/schemas/standard_document.py`; GET list + upload 201 + upload dedup pre-check now use it, backed by `get_summaries_by_workspace_id()` with a deferred `content` column (`server/app/repositories/standard_document_repository.py:36`); per-document GET keeps full `StandardDocumentResponse`; client type in `client/src/api/documents.ts` dropped `content`. Locked by `server/tests/test_document_summaries.py` (6 tests). Verified: pytest 37 passed, `npm run build` + `npm run lint` green.
- **Original finding (for the record):**
- **Where:** `server/app/api/routes/standard_document.py:344` → `StandardDocumentResponse.content: str` (`app/schemas/standard_document.py:15`)
- **Verified:** each document carries up to 500k chars; the sources rail in `client/src/pages/WorkspacePage.tsx` renders only title/type/metadata/count — the content is never displayed. A 10-source workspace can ship multi-MB JSON on every mount and every post-upload/delete invalidation.
- **Fix:** add a list-projection endpoint (or `include_content=false` query param; repository-level deferred column) and use it from the client's `getDocuments`. Keep the per-document endpoint (also currently unused by the UI — see L-1) for full content.

### ✅ M-4 — Disconnecting Drive silently kills Gmail (and connecting Drive grants `gmail.readonly`) — FIXED 2026-10-10

- **Status:** fixed by separation (uncommitted working tree at time of writing). Gmail and Drive each own their `google_connections` row (`provider` `"gmail"`/`"drive"`, migration `f7a1c9e4b206`, pre-split rows wiped — no real users); storage/refresh shared via `GoogleOAuthStore`, connect/disconnect/status per connector. `DRIVE_SCOPES` narrowed to `drive.file`-only. Dead grants (e.g. Testing-mode 7-day refresh expiry behind the reported picker failure) raise `GoogleReconnectRequiredError` → 409 `{"reconnect_required": True, "connector": ...}` on picker-token, both imports, and Gmail browse; client shows a Reconnect CTA (Drive picker/import, Gmail browser/import) instead of cryptic errors. Disconnect dialogs now state the other connector is unaffected. Locked by `server/tests/test_google_connections.py` (11 tests, SQLite). Verified: pytest 61 passed, `npm run build` + `npm run lint` clean, migration applied to local DB (single head `f7a1c9e4b206`).
- **Original finding (for the record):**

- **Where:** `server/app/integrations/drive/service.py` (`delete_connection`/`revoke_connection` delegate to the shared `google_connections` row; `DRIVE_SCOPES` includes `GMAIL_READONLY_SCOPE`)
- **Verified:** last-connect-wins sharing is documented in AGENTS.md, but the client disconnect dialog ("Disconnect Google Drive?") never says it also disconnects Gmail and revokes the shared grant — a real user-facing surprise. Conversely a Drive-only user ends up with Gmail read access they never asked for in the Drive flow.
- **Fix (UX-only, keeps single-row posture):** mention the shared connection in both disconnect dialogs and the connect confirm; optionally, on Drive connect for an existing Gmail connection, keep scopes as-is but surface the account email union in the Sources rail.

### ✅ M-5 — Coral primary buttons fail WCAG AA contrast (stated project goal) — FIXED (by the 2026-10-01 rebrand; verified + closed 2026-10-19)

- **Status:** closed. The finding applied to the pre-rebrand `accent` variant (`bg-accent-action text-white`). That token no longer exists — the Sourcify rebrand changed the accent button to **ink-on-coral**: `bg-signal text-ink` (`client/src/components/ui/button.tsx:21`) with `--color-signal: #ff5c3b` and `--color-ink: #151515` (`client/src/index.css:27,41`). Recomputed: `#151515` on `#FF5C3B` = **5.95:1**, comfortably past AA's 4.5:1 for `text-sm`. Hover (`--color-signal-deep: #e0431f`) is darker, so contrast only improves. AGENTS.md already records the governing rule ("Filled coral takes black labels — white-on-coral fails AA"). No code change was needed for this close.
- **Original finding (for the record):**
- **Where:** `client/src/index.css:43` tokens; `client/src/components/ui/button.tsx:21` (`accent` variant: `bg-accent-action text-white`, labels at `text-sm font-semibold`)
- **Computed (verified by formula):** `#FF5A36` on white = **3.10:1**; hover `#D94324` on white = **4.39:1**. AA needs **4.5:1** for normal text (`text-sm` is below the large-text exemption). Everything else in the system passed: ink-on-canvas 17.0:1, ink-on-surface 18.3:1, steel-on-surface 5.6:1, steel-on-canvas 5.2:1. Disabled state (hairline bg + muted text) is a disabled control, exempt.

### ✅ M-6 — Parser tests fail on a fresh clone: they depend on gitignored `datasets/` — FIXED 2026-10-19

- **Status:** fixed by deleting `datasets/` outright and making the parser tests self-contained. `server/tests/test_parsers.py` now builds its own fixtures at test time from deps the parsers already require (`pymupdf` for the PDF, `python-docx` for the DOCX, a direct write for the TXT), written into a `tmp_path_factory` dir — no binary files in git, no external data. The dead `datasets/` entry was dropped from `.gitignore`. Assertions were also strengthened while rewriting: the old `len >= 1` + non-empty checks became real round-trip assertions (`source_type`, `title`, marker string present in `content`, `metadata` fields, PDF `page_count`), plus previously-untested error paths (missing file ×3, wrong extension ×3, `max_extracted_chars` / `max_pdf_pages` caps via `monkeypatch`, empty DOCX) and transcript detection (attendees/duration extraction + speaker-turn normalization — the docx parser's most complex logic had zero coverage). 3 tests → 14; suite 75 → 86. Verified green with `datasets/` absent.
- **Verified (original):** moved `datasets/` aside → `3 failed, 28 passed` (`server/tests/test_parsers.py` — txt/pdf/docx end-to-end cases). `.gitignore:2` ignored `datasets/`, so these fixtures existed only on this machine while the test docstring said "checked-in sample datasets". AGENTS.md's "31 tests green" was only true locally. Any CI on a fresh checkout was red.
- **Fix (original):** either un-ignore + commit small synthetic fixtures (regenerate tiny txt/pdf/docx into `tests/fixtures/`), or `pytest.mark.skipif` on missing datasets with a loud reason.

### ✅ M-7 — Single-instance assumptions beyond the documented PKCE note — FIXED 2026-10-19 (documented)

- **Status:** fixed by documenting the constraint, as the entry's own fix recommended. The README gained a **Deploy** section stating the backend is single-process (`uvicorn app.main:app`, no `--workers N`, no replicas), naming the three in-memory surfaces and what breaks under scaling (rate buckets counted per worker → N× the intended quota; OAuth state/PKCE verifier mismatch → `Invalid or expired OAuth state` on callback; `BackgroundTasks` generation killed by restart), and spelling out the migration path (rate limits + verifiers + pipeline onto Redis or the DB, until then pin `--workers 1` and scale vertically). The same section documents the production settings that were no-ops as configured (`ALLOWED_HOSTS`, `ENVIRONMENT`, `CORS_ORIGINS`) — see **L-10**. The code posture is unchanged and correct for the documented single-worker deployment.
- **Where (original):** in-memory slowapi storage (`core/rate_limit.py`), two in-memory OAuth verifier dicts (`integrations/gmail/router.py`, `integrations/drive/router.py` — the PKCE one is commented), in-process `BackgroundTasks` pipeline (`api/routes/brd.py` + `generation_job_service.run_generation_job`).
- **Verified (original):** all fine on one uvicorn process (the current posture). Under N workers/replicas: rate buckets split per worker, a connect initiated on worker A fails its callback on worker B (`Invalid or expired OAuth state`), and long generations are invisible/killable by restarts (compounds **H-3**).

### ✅ M-8 — README setup instructions are wrong/broken as written — FIXED 2026-10-19

- **Status:** fixed. The backend env table now matches `app/core/config.py`: `SUPABASE_ANON_KEY` → **`SUPABASE_PUBLISHABLE_KEY`**, plus the four required vars that were missing entirely (`FRONTEND_URL`, `TOKEN_ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `GEMINI_API_KEY`) — each with its generate-one-liner, since omitting `TOKEN_ENCRYPTION_KEY` / `OAUTH_STATE_SECRET` is a fail-fast boot error and the old table could not boot the app. A `Required` column was added and the table points at `server/.env.example` for the optional tuning knobs. Install docs are now uv-primary (`uv venv` + `uv pip install --python .venv/bin/python -r requirements.txt`) with a plain `python -m venv` + `pip install` alternative, and "Python 3.12+" became "Python 3.11+" to match the shipped venv (3.11.15). The frontend's `VITE_SUPABASE_ANON_KEY` was left alone — it is correct for Supabase JS. While in the API overview, the two dead routes (`POST /workspaces/{id}/extract`, `POST /workspaces/{id}/knowledge/consolidate`) were dropped per **L-1** (docs-only; the routes themselves are still exposed).
- **Verified (original):** three mismatches —
  1. `README.md:98` env table listed `SUPABASE_ANON_KEY`, but `app/core/config.py:22` requires `SUPABASE_PUBLISHABLE_KEY` (`.env.example` was correct) → copy-pasting README gave a boot validation error.
  2. `README.md:76` said `pip install -r requirements.txt` — the documented venv has **no pip module** (AGENTS.md: uv only: `uv pip install --python .venv/bin/python -r requirements.txt`).
  3. `README.md:65` said "Python 3.12+" but the shipped venv is **3.11.15** (works fine — so just pick one and align).
- **Fix (original):** correct the table, switch install command to the uv form, align the Python version note.

### ✅ M-9 — Stale root `requirements.txt` is an install trap — FIXED 2026-10-19

- **Status:** fixed by deleting the file (`git rm requirements.txt`). Verified nothing referenced it — no Dockerfile, CI config, Makefile, or Procfile anywhere in the repo, and the README's install steps already begin with `cd server`, so `server/requirements.txt` was always the one that mattered. A comments-only "pointer" file was rejected on purpose: `pip install -r requirements.txt` would then succeed while installing nothing, which is a worse failure mode than an absent file.
- **Verified (original):** `requirements.txt` (repo root) was a subset of `server/requirements.txt` missing every integration dep: `google-api-python-client`, `google-auth-oauthlib`, `google-api-core`, `slowapi`, `requests-oauthlib`, `httplib2`, `uritemplate`, `protobuf`, etc. A contributor installing from the root file got an app that crashed at import.

---

### ✅ L-1 — Dead API surface: client + server — FIXED 2026-10-19

- **Status:** fixed by deleting the dead surface rather than hiding it. Client: `client/src/api/extractions.ts` + `client/src/api/projectKnowledge.ts` removed (repo-wide grep confirmed zero imports outside their own definitions). Server: the two routers (`app/api/routes/document_extraction.py`, `app/api/routes/project_knowledge.py`), their now-unused response schemas (`app/schemas/document_extraction.py`, `app/schemas/project_knowledge.py`), the `main.py` imports/`include_router` lines, and the settings only they consumed (`rate_limit_extract`, `rate_limit_consolidate` + the two `RATE_LIMIT_*` lines in `.env.example`) are gone. Nothing called them — the generation pipeline invokes `DocumentExtractionService` / `ProjectKnowledgeService` **directly** (`tests/test_generation_jobs.py` mocks the services on `job_module`, never the routes), and no test hit the URLs. Verified after removal: app boots, OpenAPI has **27 paths** with `extractions` / `project-knowledge` absent; remaining `document_extraction`/`project_knowledge` matches are all the DB/AI **models** the pipeline still needs. The DB tables, RLS policies, and services are untouched — only the HTTP surface went.
- **Original finding (for the record):** `client/src/api/extractions.ts` and `client/src/api/projectKnowledge.ts` were imported nowhere; the matching server routes remained exposed (rate-limited, authenticated) although the pipeline now owns those steps internally via `generation_jobs`. Harmless today; drift risk later.

### ✅ L-2 — `server/test_models.py` sits outside the `tests/` package — FIXED 2026-10-19

- **Status:** fixed with `git mv server/test_models.py server/tests/test_models.py`. `tests/` already has `__init__.py`, so it imports as `tests.test_models` with `server/` as basedir and the `app.*` imports resolve unchanged (suite run from `server/` per AGENTS.md). `server/` root now has zero stray `.py` files. Test still collected and passing — no assertion changes.
- **Original finding (for the record):** it **was** collected and passing (`test_models.py::test_models_and_relationships_load`, one model/relationship smoke test that `tests/` does not duplicate) — not dead code, only a layout inconsistency: the sole test file living at the server root.

### ✅ L-3 — `aria-expanded` static values — FIXED 2026-10-19

- **Status:** fixed by completing the disclosure pair. The two *expand* buttons were the real gap — `Show sources` (`WorkspacePage.tsx` sources rail) and `Show Q&A` (`WorkspacePage.tsx` Q&A rail) now carry `aria-expanded="false"`. The two *collapse* buttons keep `aria-expanded="true"` (`WorkspacePage.tsx` sources, `BRDQAPanel.tsx` header) — that value is **correct, not stale**, because each button is conditionally rendered: the "Hide …" button only exists while its panel is open, so `true` is the live state of the region it controls. The original complaint (screen readers hearing a constant "expanded") was really the missing `false` on the collapsed-state buttons, since those were the only ones reachable while a panel was shut. No styling impact: these are raw `<button>`s with hand-written classes, so no `aria-expanded:` variant from `button.tsx` is involved.
- **Original finding (for the record):** `WorkspacePage.tsx:1107` and `BRDQAPanel.tsx:130` hardcoded `aria-expanded="true"` on the collapse buttons, and the collapsed-state expand buttons carried no `aria-expanded` at all.

### ✅ L-4 — Mobile Q&A auto-scroll can't work below `md` — FIXED 2026-10-19

- **Status:** fixed with an **end sentinel + `scrollIntoView`** (the option the audit itself named), in `client/src/components/brd/BRDQAPanel.tsx` only. The dead `scrollRef.current?.scrollTo(...)` is gone; a 1px `aria-hidden` sentinel div now anchors the end of the scroll content and the effect calls `endRef.current?.scrollIntoView({ block: "nearest" })`. One mechanism serves both breakpoints: below `md` it scrolls the *page* (the panel has no height bound), at `md+` it scrolls the inner container. `block: "nearest"` skips the scroll when the end is already visible, and omitting `behavior` lets `html`'s motion-safe `scroll-behavior: smooth` (`index.css:423-427`) decide smooth-vs-instant — so reduced-motion is honored automatically, matching the old `scrollTo` exactly. The `max-h-`/dvh mobile-height alternative was rejected: it would give the phone layout an inner scrollbar (scroll-trap risk) for no gain.
- **Original finding (for the record):** the aside only gets a height constraint from `md:` up, so on phones the unbounded `flex-1 overflow-y-auto` div made `scrollTo` a no-op and new answers never scrolled into view.

### ✅ L-5 — Empty/scanned sources pass silently — FIXED 2026-10-19

- **Status:** fixed at the parser level, matching `docx_parser`'s existing guard. `TxtParser` now raises `ValueError("No readable text found in: …")` after reading (covers 0-byte **and** whitespace-only files, checked before the char cap exactly like docx), and `PdfParser` raises the same message when the joined page text is empty (covers image-only/scanned PDFs with no text layer). Both routes that run parsers already map `ValueError` → **400** (`standard_document.py` upload handler and the Drive import handler, which 413s only when the message says "too large"), so an unextractable upload now fails loudly instead of being stored, marked extractable, and carried as an empty section into the Sarvam project PDF.
- **Tests:** `test_docx_empty_raises` generalized into parametrized `test_empty_content_raises` over four fixtures — `empty_txt_path` (0-byte), `blank_txt_path` (whitespace-only), `image_only_pdf_path` (page with no text layer), `empty_docx_path` — asserting the same `No readable text` message from all three parsers.
- **Original finding (for the record):** only `docx_parser` raised "No readable text found". A 0-byte `.txt` or an image-only PDF (0 extracted chars) was stored and marked extractable; the project PDF then carried an empty section and the BRD silently lacked that source.

### ✅ L-6 — Raw provider exception strings reach the client and audit — FIXED 2026-10-19

- **Status:** fixed in `server/app/services/generation_job_service.py`. The single leak site (`except Exception as exc: _fail_job(job, str(exc) or "Generation failed")`) now calls a new module-level `public_error_message(exc)` and logs the detail instead: `logger.exception("Generation job %s failed (workspace %s)", job_id, workspace_id)` under the new `brd-agent.generation` logger. Mapping (keyword/type, regex with word boundaries so an id containing `429` can't misfire): rate/quota → *"The AI service is busy right now…"*, safety/filter → *"…blocked by the AI safety filters…"*, timeout/connect (incl. `isinstance(TimeoutError, ConnectionError)`) → *"Couldn't reach the AI service…"*, missing key/auth → *"…isn't configured correctly on this server…"*, else generic *"Something went wrong while generating the BRD…"*. **`str(exc)` is never persisted or returned.** The other four `_fail_job` sites and the stale-reaper already pass fixed friendly strings and are untouched; the client (`Generation failed. {error}`) needed no change.
- **Two corrections to the original finding:** (1) the *audit* half is inaccurate — `AuditMiddleware` records only method/path/status/latency and no `audit()` call carries an error body, so raw text reached the **DB job row + client** only. (2) More importantly there was **no server-side logging of job failures at all**, so the fix *adds* logging rather than merely relocating the text — without it, dropping `str(exc)` would have destroyed all failure detail.
- **Tests:** `test_generation_jobs.py` +9 — parametrized `test_public_error_message_maps_known_conditions` (6 cases incl. generic fallback), the id-`429` false-positive guard, and two `execute_job` drills (friendly stored + raw absent from `job.error`; raw present in `caplog`). 96 → **105 passed**.
- **Original finding (for the record):** `_fail_job(str(exc))` stored library/SDK messages (`google-genai`, `sarvamai`) returned verbatim in `GET /brd/status` and rendered at `WorkspacePage.tsx` — internal-detail leak + scary UX.

### ✅ L-7 — Dedup can false-positive — FIXED 2026-10-19

- **Status:** fixed client-side with a **Replace dialog — no API change, no migration** (`client/src/pages/WorkspacePage.tsx` only). `findDuplicateUpload` now returns a discriminated `DuplicateMatch`: an **in-batch** repeat stays a hard error (nothing to replace — *"…appears more than once in this selection"*), while a match against a **stored** source opens a `Replace this source?` Dialog naming the file. Confirm chains `deleteMutation.mutateAsync(id)` → **in its `.then()`** → `uploadMutation.mutate(files)` — sequential on purpose, because the server re-checks the dedup triple against committed rows and a parallel upload would race the uncommitted delete (409). If the delete fails the dialog stays open with an inline `StateAlert` and the old source is untouched. Bonus: the upload error block now shows `errorDetail(error)` (the server's 409 `detail` string) instead of the generic *"Upload failed. Try again."*, so a race still explains itself. Cancel closes via the same `onOpenChange` guard as the delete dialog; black `default` variant for Replace (coral stays reserved for Generate/Regenerate per AGENTS.md).
- **Rejected:** content-hash dedup (needs an Alembic column + backfill and would *newly* 409 identical bytes stored under two names) and a server `?replace=true` flag (API contract change for the same UX). The server's triple check (`standard_document.py:upload_file_key` → 409) is unchanged and still enforces.
- **Original finding (for the record):** the triple `(file_name, extension, size_bytes)` was enforced **twice** — server 409 *and* a client hard-block that showed a red alert and returned — so an edited file keeping name+size could never be added, with no override.

### ✅ L-8 — Design-skill vendor tree is committed against the project rule — FIXED 2026-10-19

- **Status:** fixed the way the entry itself offered — **untrack + ignore**, honoring the rule as written rather than amending it. `git rm -r --cached client/.agents client/skills-lock.json` (76 paths staged for removal from git; **files stay on disk** for local agent use) plus `.gitignore` entries (`client/.agents/`, `client/skills-lock.json`) under a comment quoting the AGENTS.md rule. Verified before doing it: nothing in the product reads those paths — zero references from app code or config (the only `.agents` hits were inside `server/.venv`'s Google discovery cache), so no build/config change was needed. After: `git ls-files client/.agents client/skills-lock.json` → **0**, dirs still present on disk. `client/skills-lock.json` was included because it is part of the same installed-skills vendor set, not app config.
- **Original finding (for the record):** AGENTS.md said skills were "supporting expertise only — never `--persist` them into the project", yet `client/.agents/skills/**` (75 tracked files incl. `ui-ux-pro-max` data CSVs, 3.6 MB on disk) was in git. Either the rule or the tree had to change.

### ✅ L-9 — Gmail browse is N+1 sequential Google API calls — FIXED 2026-10-19

- **Status:** fixed with **batch HTTP** (the entry's first suggestion) in `server/app/integrations/gmail/service.py`. New `GmailService.get_messages(user_id, message_ids)`: credentials + discovery client are built **once**, then every `messages.get(format="full")` rides a single `new_batch_http_request` — **2 calls total instead of 1 + N HTTP plus 2(N+1) setup calls** (worst case was 21 round trips + 42 credential/build setups for a 20-result search). Results are re-emitted **in input order** (collected by `request_id`, not callback arrival); a failed sub-response is raised after the batch, which the routes already map to 400 — exactly the old loop's behavior, so no status/shape change. If `batch.execute()` itself fails (known googleapiclient batch quirks), the same ids are fetched **sequentially on the same built client** — batch trouble degrades to slower, not broken, and credentials are still read once. Both routes (`recent` 5, `search` ≤20) dropped their duplicated per-id loop for one call + a mapper pass.
- **Constraint respected:** `get_message(user_id, message_id)` is untouched — `import_service.py:53` (and `test_import_caps.py`) depend on it for the body-fetch path.
- **Tests:** new `server/tests/test_gmail_browse.py` (4) with a faked Google client (`monkeypatch.setattr("googleapiclient.discovery.build", ...)` — the service imports `build` inside the method, at call time): ① 20 ids → `get_credentials`/`build` called **once**, one batch execute, zero sequential GETs, input order preserved; ② batch-execute failure → sequential fallback returns everything with one build + one credential read; ③ failed sub-response propagates (400 parity); ④ empty id list builds nothing at all. 105 → **109 passed**.
- **Original finding (for the record):** `recent_gmail_messages` / `search_gmail_messages` did `messages.list` then a `messages.get` **per result** (up to 20), each rebuilding the client — worst-case ≈ 20 serial RTTs against a 30/min quota.

### ✅ L-10 — Small deploy-posture notes — FIXED 2026-10-19

- **Status:** closed.
  1. **`ALLOWED_HOSTS` no-op** — now documented in the README's new Deploy section (with a `Production settings` table explaining that empty defaults to `["*"]`, making `TrustedHostMiddleware` a no-op and leaving Host-header spoofing unmitigated) and warned about in `server/.env.example`. The value itself belongs in the operator's prod `.env`, which is gitignored and not ours to set.
  2. **No CSP on API responses** — documented as intentional: the API is JSON-only and sets its own headers via `SecurityHeadersMiddleware`; SPA headers (CSP/HSTS/`X-Frame-Options`) belong at the static host (`vercel.json`/`netlify.toml`), which `client/.env.example` already noted.
  3. **Hardcoded `calc(100vh-65px)`** — **already fixed** by the 2026-10-01 Sourcify rebrand, before this entry was re-checked. `--shell-chrome: 3.5625rem` is defined at `client/src/index.css:88` and used by all three sites (`TopBar.tsx:14`, `WorkspacePage.tsx:1144`, `BRDQAPanel.tsx:89`) — a header-height tweak now propagates everywhere. Verified by grep; no change needed.
- **Original (for the record):**
  - `allowed_hosts` defaulted to `["*"]` and `server/.env` didn't set `ALLOWED_HOSTS` → `TrustedHostMiddleware` was a no-op as configured.
  - No CSP on API responses (fine for API-only backend; noted for completeness).
  - `calc(100vh-65px)` (WorkspacePage:1077, BRDQAPanel:90) hardcoded the TopBar height.

---

## 3. Things checked and found OK (explicitly *not* issues)

- **Authn:** JWKS with `timeout=5`, RS256+ES256, `audience="authenticated"`, issuer pinned, 503 on JWKS outage vs 401 on bad token, `sub` required. Correct posture for Supabase.
- **Authz:** every workspace-scoped service checks ownership via `get_workspace_for_user` before touching rows; cross-workspace document URLs 404 (`document.workspace_id != workspace_id`). No horizontal access path found.
- **OAuth:** signed state JWT with `jti`, single-use pop, 10-min expiry + purge, PKCE verifier stored server-side, redirect URIs fixed by config, `authorization_url` allowlisted to `accounts.google.com` client-side, 303 post-callback. Solid.
- **Rate limits actually double-fire safe:** middleware `_should_exempt` skips decorated routes → no double counting; `Retry-After` handler validated end-to-end (200 → 429 with 60 s / 3600 s per window).
- **Exports:** fresh temp file per request + `BackgroundTask` unlink; filename sanitizer (`safe_export_filename`) strips path/quote/control chars, caps at 80; DOCX builder (Arial) correctly keeps real `• –` while PDF keeps `-`/`--` fallbacks (per AGENTS.md) — modulo H-1's unmapped set.
- **Migration graph:** strictly linear, single head; `generation_jobs` RLS matches the 7 sibling tables; `unique workspace name per user` is a functional unique index (`lower(name)`) consistent with the case-insensitive service check + `IntegrityError` → 409 fallback.
- **Frontend client:** 401 refresh-single-flight (`refreshPromise` dedupes concurrent refreshes), one retry, sign-out + redirect fallback; 429 message merge from `Retry-After`; timeouts sane (30 s global; generate returns 202 instantly now).
- **React-query usage:** status polling only while a job is tracked (`refetchInterval` gated by `trackedJobId`), BRD stale 5 min, batched invalidates, reload-resume + completion detection via `active_job`/`last_job` identity (no flag heuristics). The generation state machine is well-built — its only hole is the ghost-job case inherited from H-3.
- **Parsers:** size/page/char caps applied *before* heavy work in all three upload parsers; magic sniffing (PDF header, PK + `[Content_Types].xml`, NUL/UTF-8 sample) is genuinely content-based.
- **Hygiene:** no `console.log`/TODO/FIXME left in app code; no tracked `.DS_Store`/`__pycache__`/`.pyc`; `.env.example` complete and matches config fields; `ENVIRONMENT` gates `/health/database` + HSTS as documented.
- **Token crypto:** Fernet fail-fast via required setting; lazy migrate-on-read (`decrypt_token_or_legacy`) correctly re-encrypts plaintext rows.

## 4. Dependency inventory (current, verified installed/pinned)

- **Server:** fastapi 0.141.1, starlette 1.6.0, uvicorn 0.52.4, slowapi 0.1.10, pyjwt 2.13.0, httpx 0.28.1, fpdf2 2.8.8, python-docx 1.2.0, pymupdf, google-genai 2.22.0, sarvamai, google-api-python-client 2.200.0, google-auth-oauthlib 1.4.1, cryptography 50.0.1, alembic 1.19.1, psycopg (via URL scheme). Test-only: pytest 8.3.5 in `requirements-dev.txt` — correctly kept out of runtime reqs.
- **Client:** React 19.2, Vite 8.2 (rolldown manualChunks), TS ~6.0, Tailwind 4.3, @base-ui/react 1.8, @tanstack/react-query 5.102, axios 1.20, @supabase/supabase-js 2.116, lucide-react ^1.43 (pinned per decision), DM Sans via @fontsource-variable. `shadcn` CLI correctly in devDependencies.

## 5. Suggested fix order (when edits are authorized)

1. ~~**H-1 + H-2**~~ done 2026-10-10 (export integrity: latin-1 safety net + shape-validating `PUT` / export-side 422, with crash-regression tests).
2. ~~**H-3**~~ done 2026-10-11 (lazy per-workspace stale-job reaper + partial unique index + client watchdog, with reaper/race/ghost-drill tests).
3. ~~**M-1**~~ done 2026-10-18 (rate-limit key on verified `sub` stashed on `request.state`, not token hash; 5 regression tests).
4. ~~**M-6 + M-8 + M-9**~~ done 2026-10-19 (self-generating parser fixtures + deleted `datasets/`, README env table/install/Python version corrected, root `requirements.txt` removed — "CI-less manual verification" trust restored).
5. ~~**M-2**~~ done 2026-10-19 (Gmail `max_extracted_chars` reject → 413, Drive streamed with a hard byte ceiling, `max_aggregate_chars` budget on the Sarvam project PDF; 7 tests). **M-7** — deploy posture doc note (M-3 list projection done 2026-10-10).
6. ~~**M-5**~~ closed 2026-10-19 (verified: the 2026-10-01 rebrand already moved accent buttons to ink-on-coral `#151515`/`#FF5C3B` = 5.95:1, past AA; M-4 resolved by separation 2026-10-10).
7. ~~**M-7 + L-10**~~ done 2026-10-19 (new README Deploy section: single-worker posture + `ALLOWED_HOSTS`/`ENVIRONMENT`/`CORS_ORIGINS` production table; L-10 item 3 was already fixed by the rebrand's `--shell-chrome` token).
8. ~~**L-1, L-2, L-3, L-5**~~ done 2026-10-19 (Batch A+B: deleted the dead client modules + their two server routers/schemas/unused rate-limit settings, `git mv`'d `test_models.py` into `tests/`, completed the `aria-expanded` disclosure pair, added empty-content guards to txt/pdf parsers + 4 parametrized tests). ~~**L-4, L-6, L-7**~~ done 2026-10-19 (Batch C: end-sentinel `scrollIntoView` for mobile Q&A auto-scroll, `public_error_message()` sanitization + `logger.exception` for job failures, client Replace dialog for stored-source duplicates). ~~**L-8, L-9**~~ done 2026-10-19 (Batch D: `git rm --cached` + `.gitignore` for the skills tree, `GmailService.get_messages` batching browse to one HTTP round trip with a sequential fallback). **Nothing remaining — the audit is fully closed.**

## 6. Notes on process

- No file was modified by this audit (verified `git status` clean afterwards; the `datasets/` move used to prove M-6 was restored immediately).
- Severity reflects impact *within the documented single-instance deployment posture*; M-7 items upgrade if multi-worker deployment is ever adopted.
- Line numbers refer to `redesign/space @ a22b1ed`; they will drift after edits.
