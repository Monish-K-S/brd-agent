# Sourcify – Agent Guide

## Overview
- Product brand: **Sourcify** (renamed from BRD Agent 2026-10-01; repo path `brd-agent` and internal `brd*` identifiers stay). Frontend user-facing branding is Sourcify only.
- Backend: FastAPI (`server/`).
- Frontend: React + Vite + TS (`client/`).
- Core flow: **Create Workspace → Add Sources → Generate BRD → View/Download → Add More Sources → Regenerate**.

## Backend Context
- Supabase JWT auth (Bearer token).
- AI pipeline (extraction → knowledge → BRD) hidden from UI.
- Hardening in place: chunked upload caps (10MB/file, max 10 files, magic sniffing, 413 oversize, 500k extracted chars, 200 PDF pages), **import caps (M-2)** — Gmail bodies rejected past `max_extracted_chars` → 413, Drive downloads streamed via `MediaIoBaseDownload` with a hard byte ceiling (never fully buffered), and `max_aggregate_chars` bounds the total content in the Sarvam project PDF (tail truncated + marker, dropped docs stay unextracted), slowapi per-user rate limits (keyed on verified JWT `sub` stashed on `request.state` by `get_current_user`, never on the rotatable token hash) + 429 `Retry-After`, safe export filenames, 401 refresh-then-redirect, Fernet fail-fast + lazy migrate, OAuth single-use verifier, CORS env+localhost, `SecurityHeadersMiddleware` (HSTS prod-only), `TrustedHostMiddleware`, JWKS `timeout=5`, `/health/database` prod gate, allowlisted `authorization_url`, Gmail `message_ids` regex audit, `app/core/audit.py` + `AuditMiddleware`, `validate_brd_data()` (11 sections → 413/422).
- Export builders (`server/app/ai/builders/`): `brd_document_builder.py` (fpdf2 2.8.8) and `brd_docx_builder.py` (python-docx 1.2.0), called only from `brd_service.py` (`export_brd_pdf_for_user` / `export_brd_docx_for_user`, fresh temp file per export — no caching). Signatures `(brd, output_path)` — do not change.
- Integrations (`server/app/integrations/`): Gmail + Drive each own their `google_connections` row (`provider` `"gmail"`/`"drive"`, migration `f7a1c9e4b206`, shared `GoogleOAuthStore`). Gmail grants `gmail.readonly`-only, Drive grants `drive.file`-only; disconnect/connect per connector never touches the other. Dead grants surface `GoogleReconnectRequiredError` → 409 `reconnect_required` (never 401 — reserved for Supabase refresh) with a client Reconnect CTA. Picker multiselect posts `drive_file_ids[1..10]` → existing `DocumentIngestionService` (pdf/docx/txt only, `vnd.google-apps.*` → 400).
- **PDF font constraint (latin-1):** fpdf2 core Helvetica supports U+0000–U+00FF only. `•` (U+2022) and `–`/`—` crash generation — the `_normalize_text` mappings exist for this reason (verified by a real crash 2026-09-18). PDF keeps `-` / `--` fallbacks; DOCX (Arial, full Unicode) keeps real `•` / `–`. Never add non-latin-1 literals to the PDF builder.
- **Documents list is content-deferred (M-3, 2026-10-02):** `GET /workspaces/{id}/documents` + the upload 201 return `StandardDocumentSummary` (no `content` — rows carry up to 500k chars each); repository uses `defer(StandardDocument.content)`. Per-document `GET /{document_id}` keeps full content. Internal pipeline consumers (QA, knowledge, extraction) keep `get_all_by_workspace_id`.
- **Restart the backend after any `server/` change.** Python imports builders at startup; a stale uvicorn process serves old code (no `--reload` assumed). Telltale: missing page folios in exports.
- Tests: `server/requirements-dev.txt` (pytest, installed into `server/.venv` via `uv pip install --python .venv/bin/python -r requirements-dev.txt` — the venv has no pip module). Run from `server/`: `.venv/bin/python -m pytest` (109 tests: parsers, models, export builders, generation jobs + stale-reaper/race/ghost-drill + error sanitization, dedup, document summaries, BRD shape, unicode crash, google connections, rate-limit keying, import size caps, empty-content guards, gmail browse batching). Parser tests are **self-generating** — they build tiny txt/pdf/docx fixtures at test time via pymupdf + python-docx; there is no `datasets/` dependency and no fixture files in git. Keep test-only deps out of `requirements.txt`.

## Frontend Stack (locked)
- **Core**: React, Vite, TypeScript.
- **UI**: Tailwind CSS, shadcn/ui.
- **Type**: DM Sans via `@fontsource-variable/dm-sans` (UI/body, locked) + Instrument Serif via `@fontsource/instrument-serif` (`font-display` token: wordmark, hero/display headings, page titles, BRD masthead, section numerals — display only, never body/UI).
- **Routing**: React Router.
- **State**: TanStack Query (API), React Context/AuthProvider (auth), `useState` (local).
- **HTTP**: Axios (configured with Supabase token).
- **Auth**: Supabase JS – Google-only (decision: no email/password), logout, persistent sessions.

## Design System (locked)
- `client/DESIGN.md` (the old Uber-inspired reference) has been removed from the repo by the user; the rules below are the source of truth. `client/.agents/skills/frontend-design` + `ui-ux-pro-max` are supporting expertise only — never `--persist` them into the project.
- Direction: **"Sourcify — warm editorial document software"** (shipped 2026-10-01): cream canvas `--color-canvas:#F5F1E8`, warm-white surfaces `--color-surface:#FFFDF8`, soft `#EEEAE1`/`#E7E1D5`, ink `#151515`, body `#4A463D`, steel `#6D6A63` (4.79:1 on cream), stone `#85817A`, hairline `#DDD8CD`, `edge:#8A8478` (3.3:1) for control outlines. One accent: signal coral `--color-signal:#FF5C3B` (+ `signal-text:#C43A17` for coral text on cream, `signal-soft:#FFF0EB`, `signal-deep:#E0431F`). Semantic (AA on cream): success `#1F7A4C`, warning `#96601B`, error `#B42318`, info `#2A5DA8`.
- Accent rule (2026-10-01): **coral is a signal, not structure**. Only: the transformation action (`accent` button variant = Generate/Regenerate), status dots (outdated=warning, ready=ink, generating=pulsing coral), selected-state left rules (Gmail rows), progress spinners, small brand markers (wordmark dot, finale rule, favicon dot), `::selection`. Filled coral takes **black** labels (white-on-coral fails AA); primary buttons are otherwise black. Never coral for body text — use `signal-text`.
- Background system: `components/brand/FieldBackdrop.tsx` = fixed, aria-hidden CSS layers (warm radial washes + masked dot grid + paper folds + ~4.5% inline-SVG grain). Intensities: `strong` (landing) / `expressive` (404) / `atmospheric` (workspaces) / `soft` (auth) / `restrained` (workspace chrome — rails/document sit on solid surfaces; never texture behind reading text). Canvas base lives on `html` so it paints under the `-z-10` backdrop; page `<main>`s must not re-assert `bg-canvas` over it.
- Motion system (CSS-only, no libraries): tokens `--ease-out-soft`/`--ease-spring`, `--dur-1/2/3`; utilities `reveal` (+ `--reveal-delay`), `reveal-view` (scroll-driven, behind `@supports (animation-timeline: view())`), `press` (translate-y on :active), `drift-a/b` (landing fragments), `shell-cols` (rail grid transition), staggered BRD section mount via `[data-brd-document] > section` CSS. `tw-animate-css` drives dialog/dropdown enter-exit. Global reduced-motion kill-switch neutralises all of it.
- Surface language: thin hairlines, explicit radius ladder (4/6/8/10/14/18 + full pills — the old `calc(var(--radius)*n)` multiplier chain is gone), flat everything (`shadow-paper` only on the BRD sheet; `shadow-level-1` hovers; `shadow-level-2` overlays), **sentence-case labels** (uppercase + `tracking-[0.08em]` purged 2026-10-01), hairline-divided index rows for sources.
- Redesign rule: **page-by-page, visual-only** — never alter routes, API shapes, status codes, query keys, mutation logic, or Supabase flows. Preserve all CTAs/labels unless explicitly asked. Executed 2026-10-01 (Sourcify rebrand): tokens → primitives → Landing → Auth → 404 → Workspaces → Workspace shell → Sources → Viewer → Q&A → states.

## API Layout (`client/src/api/`)
```
client.ts      // Axios instance with auth header (401 refresh/retry/redirect)
workspaces.ts
sources.ts     // documents
brd.ts         // BRD + Q&A + exports (safeExportFilename)
gmail.ts
drive.ts       // Drive OAuth status, picker token, file import
```
Use TanStack Query for queries & mutations.

## User Flow
1. **Landing** – `/` (single `Sign in` nav → `/auth`; hero CTAs → `/auth`; `#how-it-works` anchor).
2. **Auth** – `/auth` (Google-only, single page — decision: no `/login`, `/signup`, no email/password; minimal back-arrow → `/`).
3. **Workspaces** – `/workspaces` (search pill, Recent/A–Z sort tabs, count line, creation tile + header pill sharing one dialog, per-id delete tracking).
4. **Workspace** – `/workspaces/:id` with three regions:
   - **Sources** (left fixed 300px rail: `SOURCES + ADD` index — Files / Gmail / Google Drive groups with live counts, hairline-divided rows, upload with client pre-check, per-id delete, Gmail browser dialog, Drive Picker via `drivePicker.ts` + `VITE_GOOGLE_PICKER_API_KEY`/`VITE_GOOGLE_APP_ID`).
   - **BRD** (center column over restrained field: utility bar `workspace name · ● status · From N sources → Export`, hairline rule; the document title itself lives in the viewer masthead (D1, 2026-10-01); inline section editing with black Save pill; sentence-case progress steps `Reading sources ··· Ns`; PDF + DOCX download with folios).
   - **Q&A** (right fixed 320px rail: soft user bubbles, justified full-width assistant paragraphs, hairline `Sources` rows with type, black Ask pill, pulsing coral Thinking dots; optimistic send <16ms, error rollback restoring composer, auto-scroll).

## Workspace States
- `EMPTY` – no-sources prompt to upload.
- `SOURCES_READY` – sources-ready prompt to generate.
- `GENERATING` – progress UI; Generate/Regenerate disabled while `generationStep !== "idle"` (no double LLM run).
- `BRD_READY` – viewer + downloads; skip-aware extraction (`regeneration_required` / `has_new_sources` both honored).
- `BRD_OUTDATED` – banner + Regenerate.
- `ERROR` – retry UI for status/documents/BRD queries.

## BRD Generation & Regeneration
- User triggers **Generate BRD** (or **Regenerate** when outdated).
- Backend handles extraction & AI; UI only shows progress and results.
- Success invalidates `["brd", id]` + `["brd-status", id]`.
- No version history or diff UI in Phase 1.

## BRD Viewer (`components/brd/BRDViewer.tsx`)
- Professional document-style view: warm-white page (`rounded-lg`, `shadow-paper`, borderless) on cream, serif masthead (`project_name`) under a `Business Requirements Document` eyebrow, serif coral `01–11` numerals above DM Sans 600 section titles, sentence-case subsection labels, hairline section rules, flat `border-y` stakeholder table, black pill save, stone meta (`Generated/Updated/Edited by you`).
- Reading text `text-justify` + `hyphens-auto lang=en`; paper width adapts to rails (`docMeasure` 720/880/1024px centered; print = white full-width).
- Exports mirror the viewer: justified body, 1.15 leading, gray PDF rules, page folios in both formats.

## Frontend Architecture (current)
```
client/src/
├─ api/ (client, workspaces, sources, brd, gmail, drive)
├─ auth/ (AuthProvider, RequireAuth, auth-context, useAuth)
├─ components/
│  ├─ brd/ (BRDViewer, BRDQAPanel)
│  ├─ drive/ (drivePicker.ts — Google Picker helper, no JSX)
│  ├─ gmail/ (GmailSourceBrowser)
│  ├─ layout/ (TopBar)
│  └─ ui/ (button, dialog, dropdown-menu, input, label, skeleton, status, use-flash)
├─ pages/ (LandingPage, AuthPage, WorkspacesPage, WorkspacePage, NotFoundPage)
├─ components/ErrorBoundary.tsx
├─ App.tsx, main.tsx, index.css
```

## Implementation Status
Done: frontend init, auth flow, protected routes, workspace CRUD, workspace shell, sources + Gmail import, generation integration, viewer, PDF + DOCX downloads, outdated detection + regeneration, empty/error states, per-id delete tracking, Dialog confirms (no `window.confirm`), `index.html` title (`BRD Agent`), `.env.example`, skeletons, API 401 handling, full MiniMax re-skin (Landing/Auth/Workspaces/Workspace), export typography polish + verification, response-time pass (WS1–WS4: dropped Inter/Geist webfonts ≈218KB, vendor `manualChunks`, BRD 5-min + workspaces 60-s stale, gmail-search 90-s gc, batched invalidates, memoized workspace grid), Google Drive connector (per-connector `google_connections` rows since 2026-10-10, `drive.file`-only scope, Picker multiselect → existing ingestion, 409 reconnect CTA), `generation_jobs` RLS (migration `62d4ff311943`), Editorial AI Workspace re-skin 2026‑09‑28 (warm canvas, coral in-app primaries, document-sheet viewer, source index rail), **Sourcify rebrand + identity redesign 2026-10-01** (cream/ink/coral-signal token system, Instrument Serif display + DM Sans UI, FieldBackdrop CSS backgrounds + grain, reveal/press/shell-cols motion, Wordmark brand component, sentence-case labels, coral disciplined to the transformation action, Vite-template assets purged, `index.html` title `Sourcify`).
Remaining: none committed — next is user-directed (product depth or hygiene gaps).

## Verification Commands
- Client: `npm run build` (must be green), preview `/ /auth /workspaces /workspaces/abc` → 200, `npm run lint` (must be clean — the 3 pre-existing errors from 2026-09-18 were fixed 2026-09-28: `buttonVariants` un-exported, auth split into `auth-context.ts` + `useAuth.ts`, BRDViewer draft sync moved to render phase).
- Server: pytest 8.3.5 in `server/.venv` — run `.venv/bin/python -m pytest` from `server/` (109 tests: parsers, models, export builders, generation jobs, dedup, document summaries, BRD shape, google connections, rate limits, import size caps, empty-content guards, gmail browse batching). Parser tests need no external data — fixtures are generated at test time. Keep test-only deps out of `requirements.txt`.
- Diffs must stay confined to planned files; `client/DESIGN.md` shows as user-modified (spec updates) — never edit it unprompted.

## Development Principles
- Build small increments; test against backend each step.
- Keep dependencies minimal; add only when needed.
- Hide AI internals from users.
- Follow existing API contracts.
- Prioritize real bugs over speculative refactoring.
- Ensure accessibility (WCAG 2.1 AA) and responsive design.

## Known Gaps – Still Open
- **`ISSUES.md` audit: fully closed 2026-10-19** — all 22 findings (3 high, 9 medium, 10 low) fixed across batches (H-1…H-3, M-1…M-9, L-1…L-10 — see the dated Closed entries below). No open findings remain.
- **Polish**: none committed — next is user-directed (product depth or hygiene).
- **Docs (stale, for future completion)**:
  - `client/DESIGN.md` shows as user-modified (spec updates) — never edit unprompted (existing rule, restated for continuity).

## Closed 2026‑09‑18 (test tooling + deps)
- pytest 8.3.5 in `server/.venv` (via `requirements-dev.txt`, uv-installed — no pip in venv); `tests/test_parser_factory.py` + `tests/test_parsers.py` + `test_models.py` converted from print-scripts to collected tests (dataset paths file-relative); new `tests/test_export_builders.py` (latin-1 crash regression, folios, DOCX justify/PAGE, empty states) — 10 passed. No CI in repo: run `.venv/bin/python -m pytest` from `server/` manually.
- `shadcn` CLI moved to `devDependencies` (runtime tree −252 packages, vendor chunks byte-identical). Deliberate keeps: `cn` npm package stays (local `@/lib/utils` would add `clsx`+`tailwind-merge` for zero gain); `lucide-react` stays pinned at `^1.43.0`.

## Closed 2026‑09‑18 (robustness pass)
- `*` 404 route → `pages/NotFoundPage.tsx` (MiniMax-matched, smart home CTA per auth state).
- Landing stays viewable when signed in; auth-entry CTAs (`Sign in`, both `Create your first BRD`) route to `/workspaces` when authed, `/auth` otherwise (`LandingPage.tsx` `entry`). `AuthPage.tsx` already forwards authed visitors onward.
- `components/ErrorBoundary.tsx` wraps route tree + `WorkspacePage` route; themed fallback with retry.
- Upload input is a real `Button` driving a hidden input via ref (`WorkspacePage.tsx`).
- `RequireAuth` loading state is a minimal centered spinner (`role=status`).
- `VITE_API_URL` was already guarded (`api/client.ts` warns + throws) — gap entry was stale, no change needed.

## Closed 2026-10-01 (Sourcify rebrand + identity)
- Frontend-only rebrand `BRD Agent` → `Sourcify`: `index.html` (title/description/og/theme-color `#F5F1E8`), landing/auth/404/workspaces/workspace chrome, footers, `favicon.svg` (ink tile + document rules + `#ff5c3b` dot), new `components/brand/Wordmark.tsx` (serif lockup + coral source mark, `tone`/`size` props) and `FieldBackdrop.tsx`. Internal identifiers untouched (`brd*` routes/files, `server` `app_name`, `Business Requirements Document` as the document-type eyebrow inside the viewer masthead).
- `index.css` rewritten: cream/warm-white/signal palette + contrast-corrected text ladder, explicit radius ladder (old `calc(var(--radius)*n)` chain gone), fluid clamp display sizes, `--font-display`, `--shell-chrome: 3.5625rem` (TopBar + both `calc(100vh-65px)` sites unified), field/grain/reveal/reveal-view/press/drift/shell-cols utilities, `shadow-paper`, coral `::selection`, `:focus-visible` ink outline. Dead tokens deleted (`brand-magenta/blue/blue-deep/blue-200/purple`, `success-bg/text`, `radius-card/tile`, `accent-action/soft/deep`, `charcoal/slate/ink-strong/input-border`, `hairline-soft`, `surface-soft`). `text-muted` call sites → `text-faint` (the shadcn `--accent` inline mapping owns `text-muted`).
- Primitives: `CoralDot` → `SignalDot`; `Eyebrow` sentence-case, `dot` prop dropped; unused `StatusBadge`/`badgeTones` deleted; button variants re-specified (black primaries, `accent` = filled coral + ink label used only for Generate/Regenerate, `subtle` = soft fill, `destructive` = outlined error-text pill, `press` motion); dialog/dropdown off-token hexes (`#efefef`, `#5e5e5e`, `bg-white`, `shadow-[...]`) tokenized; TopBar 56px `--shell-chrome` + `contained` prop; input/skeleton retoned.
- Pages visual-only per the standing redesign rule: Landing fully recomposed (hero + abstract scatter→align fragment study replacing the invented filenames/status, section list from real `ALLOWED_SECTIONS`, ink promo band with coral rule), Auth card-on-cream, Workspaces flat hairline index with hover lift, Workspace shell utility-bar header (D1: the duplicate page H2 → viewer owns the title), sources rail sentence-case group labels + compact rows + hover-reveal delete, viewer document sheet (`shadow-paper`, serif numerals/masthead, `text-body` 1.75 leading, `hyphens-auto`, hover-reveal Edit pills, section mount stagger), Q&A compact header/flat rows/`source_type` on trace rows/pulsing-coral Thinking. All routes, API shapes, query keys, mutation logic, generation job tracking, autosave, upload validation, OAuth/Picker untouched; zero `server/` diff.
- Added `@fontsource/instrument-serif` (static 400 normal + italic, latin subsets ≈43KB woff2 — deliberate, display-only exception to the 2026-09-18 font diet). Deleted unused Vite-template assets (`public/icons.svg`, `src/assets/*`).
- Verified: `npm run build` green, `npm run lint` clean, preview routes `/ /auth /workspaces /workspaces/abc` 200, CSS-utility emission spot-checked in `dist`.

## Closed 2026‑09‑28 (editorial re-skin)
- "Editorial AI Workspace": warm tokens (`canvas #F7F7F4`, `surface #FFFFFF`, ink `#151515`, hairline `#DEDED9`, accent `#FF5A36` + soft `#FFF0EB`), new `accent` button variant (in-app primaries coral; landing black pills kept), page-by-page visual-only pass Workspace → Viewer → Sources → Q&A → Workspaces → Landing → Auth/404. Query keys, routes, labels, logic untouched; build green, lint clean.
- `generation_jobs` RLS: migration `62d4ff311943` (`user_id = auth.uid()` select/insert/update/delete `TO authenticated`, reversible downgrade), applied to Supabase; backend role bypasses RLS (same posture as the other 7 tables), so no app-code changes.
- Google Drive connector shipped (see Implementation Status); `client/.env.example` documents `VITE_GOOGLE_PICKER_API_KEY` / `VITE_GOOGLE_APP_ID`.

## Closed 2026-10-11 (H-3 stale-job reaper + create race)
- `generation_jobs` ghost fix: `GenerationJobService.reap_stale_jobs()` terminalizes `queued`/`running` rows untouched longer than `generation_job_timeout_minutes` (15, new setting in `app/core/config.py` + `server/.env.example`) with `"Server restarted mid-run — please regenerate."`; invoked lazily per workspace at the top of `create_job_for_user` and `BRDService.get_brd_status_for_user` (local import — job service imports `BRDService` at module level), so a restart can never wedge a workspace again.
- Create-vs-create race closed at the DB level: migration `b8c9d0e1f2a3` (partial unique index one-active-job-per-workspace + upgrade-time cleanup of superseded duplicate actives, reversible downgrade), applied to Supabase; `create_job_for_user` treats `IntegrityError` as adopt-existing (one retry) instead of 409ing; index mirrored in model `__table_args__`.
- Client watchdog: progress card shows "Taking longer than usual" + outline Retry pill after 20 min with no phase movement; Retry ends local tracking and reuses the guarded generate handler (`retry` flag) for a fresh run. Generate/Regenerate call sites wrapped as `() => void handleGenerateBRD()` (new optional param broke direct `onClick` passing).
- Verified: 70 passed (9 new: stale queued/running reap, fresh untouched, no-timestamp skip, multi-drain, naive-datetime UTC, reap-before-check, IntegrityError adopt, real-SQLite ghost drill), `npm run build` green, `npm run lint` clean, migration upgrade→downgrade→upgrade on Supabase, partial index confirmed in `pg_indexes`, backend restarted.

## Closed 2026-10-19 (M-5 + M-7 + L-10: deploy posture + contrast close-out)
- **M-5 (verified, no code):** the audit's failing combo was the pre-rebrand `bg-accent-action text-white`. The 2026-10-01 Sourcify rebrand had already changed the accent button to ink-on-coral (`bg-signal text-ink`, `button.tsx:21`; `#151515` on `#ff5c3b` = **5.95:1**, past AA 4.5:1 — hover `#e0431f` is darker still). Recomputed and closed.
- **M-7 + L-10 (README + `.env.example` only):** new **Deploy** section in `README.md` — single-process posture (`uvicorn app.main:app`, no `--workers N`/replicas) naming the three in-memory surfaces (slowapi rate buckets → N× quota under scaling, OAuth state/PKCE verifier mismatch → `Invalid or expired OAuth state`, in-process `BackgroundTasks` generation killed by restart) plus the migration path (Redis/DB, else pin `--workers 1`). Includes a `Production settings` table for `ALLOWED_HOSTS` (empty → `["*"]` → `TrustedHostMiddleware` no-op), `ENVIRONMENT`, `CORS_ORIGINS`, and a note that SPA headers belong at the static host. Matching warning added above `ALLOWED_HOSTS=` in `server/.env.example`.
- **L-10 item 3 was already fixed** by the rebrand — `--shell-chrome: 3.5625rem` (`index.css:88`) drives `TopBar.tsx:14`, `WorkspacePage.tsx:1144`, `BRDQAPanel.tsx:89`; the hardcoded `calc(100vh-65px)` is gone. Verified by grep.
- Docs-only pass: no code diff, no backend restart. **All 3 highs and all 9 mediums from the audit are now closed** — 9 lows (L-1…L-9) remain.

## Closed 2026-10-19 (M-2: import size caps)
- **Gmail:** `GmailImportService.import_messages` rejects any message whose extracted body exceeds `settings.max_extracted_chars` (`ValueError` → new `"too large" → 413` branch added to Gmail's import handler, which previously mapped every `ValueError` to 400). Cap sits in the orchestration service so `GmailEmailMapper` stays a pure transformer.
- **Drive:** `DriveService.download_file` streams with `MediaIoBaseDownload` into a bounded `io.BytesIO`, raising once `buffer.tell()` passes `settings.max_upload_bytes` — an oversized/mis-declared file is no longer fully buffered before rejection. "File too large" wording deliberately matches the router's existing `"too large" → 413` mapping (no router change). Added a `max_bytes` param for testability; the declared-size pre-check and post-download length check both stay.
- **Aggregate:** new `max_aggregate_chars` (default 1,000,000, in `config.py` + `.env.example`). `DocumentExtractionService._fit_to_aggregate_budget` truncates the boundary-crossing doc with `[Content truncated to fit the extraction budget.]` and drops the rest — which now stay `is_extracted = False` and are excluded from `link_source_documents` (previously *every* row was marked extracted regardless, which would have silently lost dropped docs forever).
- New `server/tests/test_import_caps.py` (7 tests). Verified: **93 passed**, no client diff. **Restart the backend** — `download_file` and the import services changed at runtime. Note: the streamed Drive path deserves a real Drive smoke test on an actual import, since the unit tests stub the Google client.

## Closed 2026-10-18 (M-1 rate-limit keying)
- Rate limits now follow the **verified user**, not a rotatable bearer token: `get_current_user` (`server/app/auth/dependencies.py`) takes `request: Request` and stashes the post-verification JWT `sub` on `request.state.user_id`; `rate_limit_key` (`server/app/core/rate_limit.py`) returns `user:<sub>` when present, else remote address (headerless OAuth callbacks — unchanged). The `sha256(token)` key was deleted — refresh-to-reset is gone, and an unverified `sub` is never keyed on (no forged-token bucket-aiming DoS). Ordering verified against installed slowapi: decorated routes are checked in the endpoint wrapper, after `Depends(get_current_user)` resolves. New `server/tests/test_rate_limit.py` (5 tests incl. the rotated-token regression); pytest 75 passed. No API/status changes, no migration, server-only diff — restart the backend.

## Closed 2026-10-19 (M-6 + M-8 + M-9: fresh-clone trust)
- **M-6:** deleted the untracked gitignored `datasets/` folder (also dropped its dead `.gitignore` entry) and rewrote `server/tests/test_parsers.py` to be self-generating — a session-scoped fixture builds a `.txt` (direct write), `.pdf` (`pymupdf` `new_page`/`insert_text`/`save`) and `.docx` (`python-docx` `Document`/`add_paragraph`) into a `tmp_path_factory` dir, so nothing binary is committed and no external data is needed. Assertions were strengthened while rewriting: real round-trips (`source_type`, `title`, marker string in `content`, `metadata`, PDF `page_count`) replaced `len >= 1` + non-empty; added missing-file ×3, wrong-extension ×3, `max_extracted_chars` + `max_pdf_pages` caps via `monkeypatch.setattr(settings, ...)`, empty-DOCX rejection, and transcript detection (attendees/duration + speaker-turn normalization — previously untested). 3 tests → 14.
- **M-8:** README now matches `config.py` — `SUPABASE_ANON_KEY` → `SUPABASE_PUBLISHABLE_KEY` (frontend `VITE_SUPABASE_ANON_KEY` is correct and unchanged), added the four missing required vars (`FRONTEND_URL`, `TOKEN_ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `GEMINI_API_KEY`) with generate-one-liners and a `Required` column, uv-primary install with a venv/pip alternative, "Python 3.12+" → "3.11+". Also dropped the two dead routes from the API overview per **L-1** (docs-only — the routes are still exposed).
- **M-9:** `git rm requirements.txt` (root). Verified unreferenced — no Dockerfile/CI/Makefile/Procfile, README already starts with `cd server`. Rejected a comments-only pointer file: `pip install -r` would then succeed while installing nothing.
- Verified: **86 passed** (75 → 86), suite green with `datasets/` absent, no `datasets` refs left in code, no client/server runtime diff — docs + tests + dead files only, so **no backend restart needed**.

## Closed 2026-10-19 (L-1 + L-2 + L-3 + L-5: hygiene batch A+B)
- **L-1 (dead API surface deleted, not hidden):** removed `client/src/api/extractions.ts` + `projectKnowledge.ts` (zero imports), and on the server the routers `document_extraction.py` / `project_knowledge.py`, their response schemas `app/schemas/{document_extraction,project_knowledge}.py`, the two `main.py` imports + `include_router` lines, and the settings only they used (`rate_limit_extract`/`rate_limit_consolidate` + the matching `RATE_LIMIT_*` lines in `.env.example`). The pipeline calls `DocumentExtractionService`/`ProjectKnowledgeService` **directly** (never the URLs) and no test hit them, so nothing else changed: DB tables, RLS, repositories, and services all untouched. Verified: app boots, OpenAPI = **27 paths** with no `extractions`/`project-knowledge`, remaining grep hits are only the DB/AI models.
- **L-2:** `git mv server/test_models.py server/tests/test_models.py` — `tests/__init__.py` already existed, so `app.*` imports resolve unchanged; `server/` root now has zero stray `.py` files.
- **L-3:** added `aria-expanded="false"` to the two expand buttons (`Show sources` + `Show Q&A` in `WorkspacePage.tsx`). The collapse buttons' `aria-expanded="true"` was left as-is **on purpose** — they are conditionally rendered only while their panel is open, so `true` is the live state; the real gap was the missing `false`. Raw `<button>`s with hand-written classes, so no `button.tsx` `aria-expanded:` variant is affected (no styling change).
- **L-5:** empty-content guard added to `txt_parser` (after `read_text`, before the char cap — catches 0-byte *and* whitespace-only) and `pdf_parser` (after joining pages — catches image-only/scans), both raising `ValueError("No readable text found in: …")`. Both parser-hosting routes already map `ValueError` → 400, so no router change. `test_docx_empty_raises` generalized to parametrized `test_empty_content_raises` (4 fixtures: `empty_txt_path`, `blank_txt_path`, `image_only_pdf_path`, `empty_docx_path`).
- Verified: **96 passed** (93 → 96), `npm run lint` clean, `npm run build` green, diff confined to the planned files. **Restart the backend** — `main.py`, `config.py`, and both parsers changed at runtime. Audit state: all 3 highs + all 9 mediums closed; **5 lows remain (L-4, L-6, L-7, L-8, L-9)**.

## Closed 2026-10-19 (L-4 + L-6 + L-7: batch C)
- **L-4 (mobile Q&A auto-scroll):** `BRDQAPanel.tsx` — the dead `scrollRef.current?.scrollTo(...)` (a no-op below `md`, where the panel has no height bound) is replaced by a 1px `aria-hidden` **end sentinel** + `endRef.current?.scrollIntoView({ block: "nearest" })`. One mechanism serves both breakpoints (page scrolls on phones, inner container on desktop); omitting `behavior` lets `html`'s motion-safe `scroll-behavior: smooth` decide, so reduced-motion is honored with no JS branch. `scrollRef` deleted (unused). Rejected the `max-h-` alternative: it would impose an inner scrollbar on the phone layout.
- **L-6 (provider errors sanitized):** `generation_job_service.py` — the single leak site (`except: _fail_job(str(exc))`) now calls new module-level `public_error_message(exc)` (regex keyword/type mapping with word-boundary status codes so an id containing `429` can't misfire: quota→busy, safety→blocked, timeout/connect→unreachable, key/auth→misconfigured, else generic) and `logger.exception(...)` under new `brd-agent.generation` logger. **`str(exc)` never persists or returns.** Two corrections recorded in ISSUES.md: the *audit* half of the finding was wrong (`AuditMiddleware` logs only method/path/status/latency), and there was **no server-side logging of job failures at all** — so this fix *adds* logging rather than merely moving text. The other four `_fail_job` sites + reaper already passed fixed strings; client untouched.
- **L-7 (dedup escape hatch):** `WorkspacePage.tsx` only — `findDuplicateUpload` now returns a discriminated `DuplicateMatch`; in-batch repeats stay a hard error, matches against a **stored** source open a `Replace this source?` Dialog (black `default` variant — coral stays reserved for Generate/Regenerate). Confirm chains `deleteMutation.mutateAsync(id)` → **in `.then()`** → `uploadMutation.mutate(files)`, sequential because the server re-checks the triple against committed rows (a parallel upload would race the delete → 409); delete failure keeps the dialog open with an inline `StateAlert`. Bonus: upload errors now show `errorDetail()` (the 409 `detail` string) instead of the generic text. No API change, no migration — server 409 untouched. Content-hash + `?replace=true` alternatives rejected (migration/new false positives; API contract change).
- Verified: **105 passed** (96 → 105; +9: 6-case parametrized mapping, id-`429` guard, two `execute_job` drills incl. `caplog` raw-in-logs), `npm run lint` clean, `npm run build` green, diff confined to 3 code files + 1 test file + docs. **Restart the backend** (job service changed at runtime). Audit state: **2 lows remain (L-8, L-9)**.

## Closed 2026-10-19 (L-8 + L-9: batch D — audit fully closed)
- **L-8 (skills tree untracked):** `git rm -r --cached client/.agents client/skills-lock.json` (76 paths — files **kept on disk** for local agent use) + root `.gitignore` entries under a comment quoting the rule. The *tree* was changed rather than the rule, per the entry's own options. Verified beforehand that nothing in the product reads those paths (zero refs from app code/config; the only `.agents` hits were inside `server/.venv`'s Google discovery cache), so no build change was needed; after: `git ls-files` → 0, dirs still on disk. `client/skills-lock.json` went with it — it's part of the installed-skills set, not app config. AGENTS.md's "never `--persist`" line now matches reality; no rule edit.
- **L-9 (Gmail browse batched):** new `GmailService.get_messages(user_id, message_ids)` — credentials + discovery client built **once**, every `messages.get(format="full")` rides one `new_batch_http_request` → **2 calls total** instead of 1+N HTTP plus 2(N+1) setup (worst case was 21 RTTs + 42 setups for a 20-result search). Results re-emitted in **input order** (collected by `request_id`); a failed sub-response is raised after the batch → routes already map it to 400 (no status/shape change). `batch.execute()` failure falls back to sequential GETs **on the same built client** — batch trouble degrades to slower, not broken. Both routes (`recent`, `search`) now do one call + a mapper pass instead of a duplicated per-id loop. **`get_message()` untouched** — `import_service.py:53` and `test_import_caps.py` depend on it.
- **Tests:** new `tests/test_gmail_browse.py` (4, faked Google client via `monkeypatch.setattr("googleapiclient.discovery.build", ...)`, which resolves at call time because the service imports `build` inside the method): one build/credential-read for 20 ids + order preserved, batch-failure fallback, sub-response failure propagation (400 parity), empty-list no-op. 105 → **109 passed**; `npm run lint` clean; `npm run build` green; app boots (27 OpenAPI paths, both browse routes present).
- **Restart the backend** — `gmail/service.py` + `gmail/router.py` changed at runtime. **The `ISSUES.md` audit is now 100% closed: 3 highs + 9 mediums + 10 lows, zero open.**

*Version 1.4 – 2026-10-01 (Sourcify identity)*
