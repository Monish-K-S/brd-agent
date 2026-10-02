# Sourcify – Agent Guide

## Overview
- Product brand: **Sourcify** (renamed from BRD Agent 2026-10-01; repo path `brd-agent` and internal `brd*` identifiers stay). Frontend user-facing branding is Sourcify only.
- Backend: FastAPI (`server/`).
- Frontend: React + Vite + TS (`client/`).
- Core flow: **Create Workspace → Add Sources → Generate BRD → View/Download → Add More Sources → Regenerate**.

## Backend Context
- Supabase JWT auth (Bearer token).
- AI pipeline (extraction → knowledge → BRD) hidden from UI.
- Hardening in place: chunked upload caps (10MB/file, max 10 files, magic sniffing, 413 oversize, 500k extracted chars, 200 PDF pages), slowapi per-user rate limits + 429 `Retry-After`, safe export filenames, 401 refresh-then-redirect, Fernet fail-fast + lazy migrate, OAuth single-use verifier, CORS env+localhost, `SecurityHeadersMiddleware` (HSTS prod-only), `TrustedHostMiddleware`, JWKS `timeout=5`, `/health/database` prod gate, allowlisted `authorization_url`, Gmail `message_ids` regex audit, `app/core/audit.py` + `AuditMiddleware`, `validate_brd_data()` (11 sections → 413/422).
- Export builders (`server/app/ai/builders/`): `brd_document_builder.py` (fpdf2 2.8.8) and `brd_docx_builder.py` (python-docx 1.2.0), called only from `brd_service.py` (`export_brd_pdf_for_user` / `export_brd_docx_for_user`, fresh temp file per export — no caching). Signatures `(brd, output_path)` — do not change.
- Integrations (`server/app/integrations/`): Gmail + Drive share one Google OAuth client (`google_connections` row, `provider="google"`, last-connect-wins). Drive uses the narrow `drive.file` scope; Picker multiselect posts `drive_file_ids[1..10]` → existing `DocumentIngestionService` (pdf/docx/txt only, `vnd.google-apps.*` → 400).
- **PDF font constraint (latin-1):** fpdf2 core Helvetica supports U+0000–U+00FF only. `•` (U+2022) and `–`/`—` crash generation — the `_normalize_text` mappings exist for this reason (verified by a real crash 2026-09-18). PDF keeps `-` / `--` fallbacks; DOCX (Arial, full Unicode) keeps real `•` / `–`. Never add non-latin-1 literals to the PDF builder.
- **Documents list is content-deferred (M-3, 2026-10-02):** `GET /workspaces/{id}/documents` + the upload 201 return `StandardDocumentSummary` (no `content` — rows carry up to 500k chars each); repository uses `defer(StandardDocument.content)`. Per-document `GET /{document_id}` keeps full content. Internal pipeline consumers (QA, knowledge, extraction) keep `get_all_by_workspace_id`.
- **Restart the backend after any `server/` change.** Python imports builders at startup; a stale uvicorn process serves old code (no `--reload` assumed). Telltale: missing page folios in exports.
- Tests: `server/requirements-dev.txt` (pytest, installed into `server/.venv` via `uv pip install --python .venv/bin/python -r requirements-dev.txt` — the venv has no pip module). Run from `server/`: `.venv/bin/python -m pytest` (37 tests: parsers, models, export builders, generation jobs, dedup, document summaries). Keep test-only deps out of `requirements.txt`.

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
Done: frontend init, auth flow, protected routes, workspace CRUD, workspace shell, sources + Gmail import, generation integration, viewer, PDF + DOCX downloads, outdated detection + regeneration, empty/error states, per-id delete tracking, Dialog confirms (no `window.confirm`), `index.html` title (`BRD Agent`), `.env.example`, skeletons, API 401 handling, full MiniMax re-skin (Landing/Auth/Workspaces/Workspace), export typography polish + verification, response-time pass (WS1–WS4: dropped Inter/Geist webfonts ≈218KB, vendor `manualChunks`, BRD 5-min + workspaces 60-s stale, gmail-search 90-s gc, batched invalidates, memoized workspace grid), Google Drive connector (shared `google_connections` row, `drive.file` scope, Picker multiselect → existing ingestion), `generation_jobs` RLS (migration `62d4ff311943`), Editorial AI Workspace re-skin 2026‑09‑28 (warm canvas, coral in-app primaries, document-sheet viewer, source index rail), **Sourcify rebrand + identity redesign 2026-10-01** (cream/ink/coral-signal token system, Instrument Serif display + DM Sans UI, FieldBackdrop CSS backgrounds + grain, reveal/press/shell-cols motion, Wordmark brand component, sentence-case labels, coral disciplined to the transformation action, Vite-template assets purged, `index.html` title `Sourcify`).
Remaining: none committed — next is user-directed (product depth or hygiene gaps).

## Verification Commands
- Client: `npm run build` (must be green), preview `/ /auth /workspaces /workspaces/abc` → 200, `npm run lint` (must be clean — the 3 pre-existing errors from 2026-09-18 were fixed 2026-09-28: `buttonVariants` un-exported, auth split into `auth-context.ts` + `useAuth.ts`, BRDViewer draft sync moved to render phase).
- Server: pytest 8.3.5 in `server/.venv` — run `.venv/bin/python -m pytest` from `server/` (31 tests: parsers, models, export builders, generation jobs, dedup). Keep test-only deps out of `requirements.txt`.
- Diffs must stay confined to planned files; `client/DESIGN.md` shows as user-modified (spec updates) — never edit it unprompted.

## Development Principles
- Build small increments; test against backend each step.
- Keep dependencies minimal; add only when needed.
- Hide AI internals from users.
- Follow existing API contracts.
- Prioritize real bugs over speculative refactoring.
- Ensure accessibility (WCAG 2.1 AA) and responsive design.

## Known Gaps – Still Open
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

*Version 1.4 – 2026-10-01 (Sourcify identity)*
