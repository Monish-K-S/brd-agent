# BRD-Agent — Read-Only Audit Report

- **Date:** 2026-09-30
- **Branch inspected:** `redesign/space` @ `a22b1ed` (working tree clean; `client/DESIGN.md` user-modified diff was present earlier — untouched per project rule)
- **Scope:** full repo (FastAPI `server/`, React/Vite `client/`, docs, config, tests, deps)
- **Method:** static review + verified runs. Nothing in the codebase was changed to produce this report. All "verified" claims below were reproduced against the checked-out code (`server/.venv`, Python 3.11.15).

---

## 1. Executive summary

The project is in good shape overall: authn/authz is consistent, hardening layers (upload caps, magic sniffing, rate limits, Fernet, RLS, OAuth PKCE/state) are real and tested, and the frontend is clean (lint green, build green). The audit found **3 high**, **9 medium**, and **10 low/hygiene** issues. **M-3** has since been fixed (2026-10-10, commit `916a50b`) — 8 mediums remain open. **H-1** and **H-2** were fixed later the same day (uncommitted working tree at time of writing) — 1 high (H-3) remains open. The dominant theme:

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
| Fresh-clone test run (datasets/ hidden) | ❌ 3 failures — see **M-6** |

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

### 🔴 H-3 — `generation_jobs` have no timeout/reaper → workspace wedged after restart; also a create-vs-create race

- **Where:** `server/app/api/routes/brd.py:112` (`if job.status == "queued"` — only queued jobs ever get a background task), `server/app/services/generation_job_service.py` (no staleness handling anywhere), `GenerationJobRepository.get_active_by_workspace_id` (`status not in ("succeeded","failed")`)
- **Verified in code:** the pipeline runs in an in-process `BackgroundTasks` task. If the uvicorn process dies/restarts while a job is `queued`/`running`, the row is never terminalized. Every subsequent `POST /generate` finds that dead job "active", returns it with **status `running`**, and never starts work — while the frontend's reload-resume effect (`client/src/pages/WorkspacePage.tsx` ~line 633) adopts the ghost job and polls it every 2 s forever (no client-side timeout either). The workspace can never regenerate without manual DB surgery.
- **Race (same area):** two concurrent `POST /generate` can both pass the active-check (no unique partial index like `WHERE status IN ('queued','running')`), enqueueing two parallel pipelines; `save_brd` then double-writes (last commit wins, user edits silently lost).
- **Suggested fix:**
  1. On app startup (lifespan) — or in `get_brd_status_for_user` — reap jobs stuck in `queued/running` beyond a generous cap (e.g. > 15 min; Sarvam poll alone is ~2 min max, Gemini a bit more) → mark `failed` with `"Server restarted mid-run"`.
  2. Add a partial unique index enforcing one active job per workspace (migration), and treat `IntegrityError` as "adopt existing job" — closes the race.
  3. Optional: client-side watchdog — after N minutes of polling with no phase movement, surface "still running? Retry" instead of an eternal spinner.

---

### 🟠 M-1 — Rate limiting is keyed on the bearer token hash, so it's trivially bypassed by refreshing

- **Where:** `server/app/core/rate_limit.py:17` — `digest = sha256(token)` → `user:<digest>`
- **Verified:** Supabase access tokens rotate on every refresh (~hourly automatically, on demand via `refreshSession`), so the same user gets a **fresh counter per token**. The `5/hour` BRD-generate limit (the expensive LLM path) is defeatable by simply refreshing the session — or by the built-in 401-refresh-retry path in `client/src/api/client.ts`.
- **Fix:** resolve the user from the JWT `sub` claim in the key function (decode without verification *only* to read `sub` is unsafe for keying; better: the dependency already verifies — stash `user.id` on `request.state` in `get_current_user` and key on that, falling back to remote address).

### 🟠 M-2 — Gmail / Drive imports bypass the extraction-size caps (and Drive buffers the whole file in RAM)

- **Where:** `server/app/integrations/gmail/mapper.py:108` (`_extract_content` — no `max_extracted_chars` cap); `server/app/integrations/drive/service.py:191` (`download_file` — full `.execute()` into memory **before** the size re-check in `import_service.py`); `server/app/ai/builders/project_document_builder.py` (no caps on aggregate content)
- **Verified asymmetry:** the upload path enforces 10 MB / 500k chars / 200 pages at the parser, but email bodies and Drive files enter `standard_documents` with no character ceiling (Drive trusts the metadata `size` field, then buffers everything). A 30 MB mail thread or a mis-declared Drive file flows straight into the Sarvam project-PDF (and its cost) without the caps the upload path guarantees. The docstring in `DriveImportService` even says "bytes enter the existing pipeline" — but the cap check happens per-document only inside `TxtParser/PdfParser/DocxParser`, which are never size-limited for the pre-buffered Drive blob the same way (file bytes already fully in RAM regardless of parse caps).
- **Fix:** cap Gmail-mapped content at `settings.max_extracted_chars` (reject or truncate+flag); stream Drive downloads with a hard byte ceiling (`MediaIoBaseDownload` with a max-bytes guard) instead of buffering.

### ✅ M-3 — `GET /workspaces/{id}/documents` returns full `content` for every source — FIXED 2026-10-10

- **Status:** fixed in commit `916a50b`. `StandardDocumentSummary` (no `content`) added in `server/app/schemas/standard_document.py`; GET list + upload 201 + upload dedup pre-check now use it, backed by `get_summaries_by_workspace_id()` with a deferred `content` column (`server/app/repositories/standard_document_repository.py:36`); per-document GET keeps full `StandardDocumentResponse`; client type in `client/src/api/documents.ts` dropped `content`. Locked by `server/tests/test_document_summaries.py` (6 tests). Verified: pytest 37 passed, `npm run build` + `npm run lint` green.
- **Original finding (for the record):**
- **Where:** `server/app/api/routes/standard_document.py:344` → `StandardDocumentResponse.content: str` (`app/schemas/standard_document.py:15`)
- **Verified:** each document carries up to 500k chars; the sources rail in `client/src/pages/WorkspacePage.tsx` renders only title/type/metadata/count — the content is never displayed. A 10-source workspace can ship multi-MB JSON on every mount and every post-upload/delete invalidation.
- **Fix:** add a list-projection endpoint (or `include_content=false` query param; repository-level deferred column) and use it from the client's `getDocuments`. Keep the per-document endpoint (also currently unused by the UI — see L-1) for full content.

### 🟠 M-4 — Disconnecting Drive silently kills Gmail (and connecting Drive grants `gmail.readonly`)

- **Where:** `server/app/integrations/drive/service.py` (`delete_connection`/`revoke_connection` delegate to the shared `google_connections` row; `DRIVE_SCOPES` includes `GMAIL_READONLY_SCOPE`)
- **Verified:** last-connect-wins sharing is documented in AGENTS.md, but the client disconnect dialog ("Disconnect Google Drive?") never says it also disconnects Gmail and revokes the shared grant — a real user-facing surprise. Conversely a Drive-only user ends up with Gmail read access they never asked for in the Drive flow.
- **Fix (UX-only, keeps single-row posture):** mention the shared connection in both disconnect dialogs and the connect confirm; optionally, on Drive connect for an existing Gmail connection, keep scopes as-is but surface the account email union in the Sources rail.

### 🟠 M-5 — Coral primary buttons fail WCAG AA contrast (stated project goal)

- **Where:** `client/src/index.css:43` tokens; `client/src/components/ui/button.tsx:21` (`accent` variant: `bg-accent-action text-white`, labels at `text-sm font-semibold`)
- **Computed (verified by formula):** `#FF5A36` on white = **3.10:1**; hover `#D94324` on white = **4.39:1**. AA needs **4.5:1** for normal text (`text-sm` is below the large-text exemption). Everything else in the system passes: ink-on-canvas 17.0:1, ink-on-surface 18.3:1, steel-on-surface 5.6:1, steel-on-canvas 5.2:1. Disabled state (hairline bg + muted text) is a disabled control, exempt.
- **Fix options:** darken the action token (any coral ≤ ≈ `#E8431A`-ish crosses 4.5 at small text — needs a quick pick to stay on-brand), or bump accent-button labels to the large-text threshold (≥ 18.66px bold — changes the visual), or add a darker text-on-coral pairing for the small sizes. AGENTS.md locks the accent *direction*, not the exact hex — flag as an explicit design decision either way.

### 🟠 M-6 — Parser tests fail on a fresh clone: they depend on gitignored `datasets/`

- **Verified:** moved `datasets/` aside → `3 failed, 28 passed` (`server/tests/test_parsers.py` — txt/pdf/docx end-to-end cases). `.gitignore:2` ignores `datasets/`, so these fixtures exist only on this machine while the test docstring says "checked-in sample datasets". AGENTS.md's "31 tests green" is only true locally. Any CI on a fresh checkout is red.
- **Fix:** either un-ignore + commit small synthetic fixtures (regenerate tiny txt/pdf/docx into `tests/fixtures/`), or `pytest.mark.skipif` on missing datasets with a loud reason.

### 🟠 M-7 — Single-instance assumptions beyond the documented PKCE note

- **Where:** in-memory slowapi storage (`core/rate_limit.py`), two in-memory OAuth verifier dicts (`integrations/gmail/router.py`, `integrations/drive/router.py` — the PKCE one is commented), in-process `BackgroundTasks` pipeline (`api/routes/brd.py` + `generation_job_service.run_generation_job`).
- **Verified:** all fine on one uvicorn process (the current posture). Under N workers/replicas: rate buckets split per worker, a connect initiated on worker A fails its callback on worker B (`Invalid or expired OAuth state`), and long generations are invisible/killable by restarts (compounds **H-3**).
- **Fix:** document "single worker only" in README deploy section *now*; longer-term move verifiers to Redis/DB and the pipeline to a queue, or pin `--workers 1` with horizontal scale deferred.

### 🟠 M-8 — README setup instructions are wrong/broken as written

- **Verified three mismatches:**
  1. `README.md:98` env table lists `SUPABASE_ANON_KEY`, but `app/core/config.py:22` requires `SUPABASE_PUBLISHABLE_KEY` (`.env.example` is correct) → copy-pasting README gives a boot validation error.
  2. `README.md:76` says `pip install -r requirements.txt` — the documented venv has **no pip module** (AGENTS.md: uv only: `uv pip install --python .venv/bin/python -r requirements.txt`).
  3. `README.md:65` "Python 3.12+" but the shipped venv is **3.11.15** (works fine — so just pick one and align).
- **Fix:** correct the table, switch install command to the uv form, align the Python version note.

### 🟠 M-9 — Stale root `requirements.txt` is an install trap

- **Verified:** `requirements.txt` (repo root) is a subset of `server/requirements.txt` missing every integration dep: `google-api-python-client`, `google-auth-oauthlib`, `google-api-core`, `slowapi`, `requests-oauthlib`, `httplib2`, `uritemplate`, `protobuf`, etc. Nothing references it (README's `cd server; pip install -r requirements.txt` resolves to `server/requirements.txt`), but a contributor installing from the root file gets an app that crashes at import. Either delete it or make it a pointer comment (AGENTS.md/docs edit — flagged here since we changed nothing).

---

### 🟡 L-1 — Dead API surface: client + server
`client/src/api/extractions.ts` and `client/src/api/projectKnowledge.ts` are imported nowhere (verified repo-wide grep); the matching server routes (`POST /workspaces/{id}/extractions`, `POST /workspaces/{id}/project-knowledge/consolidate`) remain exposed (rate-limited, authenticated) although the pipeline now owns those steps internally via `generation_jobs`. Harmless today; drift risk later. Consider deleting the client modules (and either hiding the routes with `include_in_schema=False` or keeping them deliberately for ops).

### 🟡 L-2 — `server/test_models.py` sits outside the `tests/` package
Corrected during final re-check: it **is** collected and passing (`test_models.py::test_models_and_relationships_load`, one model/relationship smoke test that `tests/` does not duplicate). Not dead code — only a layout inconsistency: it's the sole test file living at the server root instead of `tests/`. Optional: move it to `tests/test_models.py` for a single test home.

### 🟡 L-3 — `aria-expanded` static values
`client/src/pages/WorkspacePage.tsx:1107` and `client/src/components/brd/BRDQAPanel.tsx:130` hardcode `aria-expanded="true"` on the *collapse* buttons, and the collapsed-state *expand* buttons carry no `aria-expanded` at all. Screen readers get a constant "expanded" signal. One-line fix each.

### 🟡 L-4 — Mobile Q&A auto-scroll can't work below `md`
`BRDQAPanel` (`:90` aside, `md:h-[calc(100vh-65px)]`, `flex min-h-0 flex-col`) only gets a height constraint from `md:` up; on phones the whole page scrolls, so `scrollRef.current?.scrollTo(...)` on the unbounded `flex-1 overflow-y-auto` div is a no-op — new answers don't scroll into view on mobile. Fix with a `max-h-[...]`/dvh mobile variant or `scrollIntoView` on the last message node (visual-only, allowed by the redesign rule).

### 🟡 L-5 — Empty/scanned sources pass silently
Only `docx_parser` raises "No readable text found". A 0-byte `.txt` or an image-only PDF (0 extracted chars) is stored and marked extractable; the Sarvam project-PDF then carries an empty section and the BRD silently lacks that source. Add the same empty-content guard to txt/pdf parsers (or at ingestion-service level).

### 🟡 L-6 — Raw provider exception strings reach the client and audit
`generation_job_service._fail_job(str(exc))` stores library/SDK messages (`google-genai`, `sarvamai`) that are returned verbatim in `GET /brd/status` and rendered at `client/src/pages/WorkspacePage.tsx:1631` (`generationServerError ?? "Try again."`). Small internal-detail leak + scary UX. Map known errors to friendly text; keep the raw in logs only.

### 🟡 L-7 — Dedup can false-positive
Upload dedup key is `(file_name, extension, size_bytes)` (`standard_document.py:upload_file_key`). A genuinely *edited* file that coincidentally matches name+ext+byte-size is a hard 409 with no user override. Rare but user-hostile; a "replace anyway" flow (delete+re-add) or content-hash with allow-override flag would settle it.

### 🟡 L-8 — Design-skill vendor tree is committed against the project rule
AGENTS.md: skills are "supporting expertise only — never `--persist` them into the project" — yet `client/.agents/skills/**` (75 tracked files incl. `ui-ux-pro-max` data CSVs) is in git (verified `git ls-files`). Either the rule or the tree should change (add to `.gitignore` + `git rm --cached`, or amend AGENTS.md to accept vendoring).

### 🟡 L-9 — Gmail browse is N+1 sequential Google API calls
`recent_gmail_messages` / `search_gmail_messages` do `messages.list` then a `messages.get` **per result** (up to 20), each rebuilding the client. Worst-case latency ≈ 20 RTTs at 30/min. Batch with `batchExecute` or fetch `format=metadata` in one pass.

### 🟡 L-10 — Small deploy-posture notes
- `allowed_hosts` defaults to `["*"]` and `server/.env` doesn't set `ALLOWED_HOSTS` → `TrustedHostMiddleware` is a no-op as configured; set it in prod `.env`.
- No CSP on API responses (fine for API-only backend; noted for completeness).
- `calc(100vh-65px)` (WorkspacePage:1077, BRDQAPanel:90) hardcodes the TopBar height — a future header tweak silently breaks the rails' scroll area.

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
2. **H-3** — startup/status stale-job reaper + one-active-job partial unique index (migration) + optional client watchdog.
3. **M-1** — rate-limit key on verified user id (`request.state`), not token hash.
4. **M-6 + M-8 + M-9** — fresh-clone green tests, README truth, kill/redirect the root requirements file (this restores "CI-less manual verification" trust).
5. **M-2 / M-7** — pipeline caps + deploy posture doc note (M-3 list projection done 2026-10-10).
6. **M-4 / M-5** — design-decision items (disconnect-dialog copy; coral contrast token pick).
7. **L-1…L-10** — batch hygiene pass (all small; keep diffs per AGENTS.md conventions, restart backend after `server/` changes).

## 6. Notes on process

- No file was modified by this audit (verified `git status` clean afterwards; the `datasets/` move used to prove M-6 was restored immediately).
- Severity reflects impact *within the documented single-instance deployment posture*; M-7 items upgrade if multi-worker deployment is ever adopted.
- Line numbers refer to `redesign/space @ a22b1ed`; they will drift after edits.
