# BRD‑Agent – Agent Guide

## Overview
- Backend: FastAPI (`server/`).
- Frontend: React + Vite + TS (`client/`).
- Core flow: **Create Workspace → Add Sources → Generate BRD → View/Download → Add More Sources → Regenerate**.

## Backend Context
- Supabase JWT auth (Bearer token).
- AI pipeline (extraction → knowledge → BRD) hidden from UI.
- Hardening in place: chunked upload caps (10MB/file, max 10 files, magic sniffing, 413 oversize, 500k extracted chars, 200 PDF pages), slowapi per-user rate limits + 429 `Retry-After`, safe export filenames, 401 refresh-then-redirect, Fernet fail-fast + lazy migrate, OAuth single-use verifier, CORS env+localhost, `SecurityHeadersMiddleware` (HSTS prod-only), `TrustedHostMiddleware`, JWKS `timeout=5`, `/health/database` prod gate, allowlisted `authorization_url`, Gmail `message_ids` regex audit, `app/core/audit.py` + `AuditMiddleware`, `validate_brd_data()` (11 sections → 413/422).
- Export builders (`server/app/ai/builders/`): `brd_document_builder.py` (fpdf2 2.8.8) and `brd_docx_builder.py` (python-docx 1.2.0), called only from `brd_service.py` (`export_brd_pdf_for_user` / `export_brd_docx_for_user`, fresh temp file per export — no caching). Signatures `(brd, output_path)` — do not change.
- **PDF font constraint (latin-1):** fpdf2 core Helvetica supports U+0000–U+00FF only. `•` (U+2022) and `–`/`—` crash generation — the `_normalize_text` mappings exist for this reason (verified by a real crash 2026-09-18). PDF keeps `-` / `--` fallbacks; DOCX (Arial, full Unicode) keeps real `•` / `–`. Never add non-latin-1 literals to the PDF builder.
- **Restart the backend after any `server/` change.** Python imports builders at startup; a stale uvicorn process serves old code (no `--reload` assumed). Telltale: missing page folios in exports.
- Tests: `server/requirements-dev.txt` (pytest, installed into `server/.venv` via `uv pip install --python .venv/bin/python -r requirements-dev.txt` — the venv has no pip module). Run from `server/`: `.venv/bin/python -m pytest` (10 tests: parser factory, format parsers over `datasets/`, model loading, export-builder regressions). Keep test-only deps out of `requirements.txt`.

## Frontend Stack (locked)
- **Core**: React, Vite, TypeScript.
- **UI**: Tailwind CSS, shadcn/ui.
- **Type**: DM Sans 600 via `@fontsource-variable/dm-sans` (locked — do not swap fonts).
- **Routing**: React Router.
- **State**: TanStack Query (API), React Context/AuthProvider (auth), `useState` (local).
- **HTTP**: Axios (configured with Supabase token).
- **Auth**: Supabase JS – Google-only (decision: no email/password), logout, persistent sessions.

## Design System (locked)
- `client/DESIGN.md` (MiniMax analysis) is the primary visual truth. `client/.agents/skills/frontend-design` + `ui-ux-pro-max` are supporting expertise only — never `--persist` them into the project.
- Tokens (`client/src/index.css`): `--color-canvas:#fff`, `--color-surface:#f7f8fa`, `--color-primary:#0a0a0a` (black pills), `--color-primary-deep:#222`, ink/charcoal/steel/stone/muted/hairlines, brand-coral/magenta/blue/purple accents. Flat shadows, 200ms transitions, smooth anchors motion-safe, global `cursor:pointer` on interactive elements.
- Redesign rule: **page-by-page, visual-only** — never alter routes, API shapes, status codes, query keys, mutation logic, or Supabase flows. Preserve all CTAs/labels unless explicitly asked. Done in order: Landing → Auth → Workspaces → Workspace.

## API Layout (`client/src/api/`)
```
client.ts      // Axios instance with auth header (401 refresh/retry/redirect)
workspaces.ts
sources.ts     // documents
brd.ts         // BRD + Q&A + exports (safeExportFilename)
gmail.ts
```
Use TanStack Query for queries & mutations.

## User Flow
1. **Landing** – `/` (single `Sign in` nav → `/auth`; hero CTAs → `/auth`; `#how-it-works` anchor).
2. **Auth** – `/auth` (Google-only, single page — decision: no `/login`, `/signup`, no email/password; minimal back-arrow → `/`).
3. **Workspaces** – `/workspaces` (search pill, Recent/A–Z sort tabs, count line, creation tile + header pill sharing one dialog, per-id delete tracking).
4. **Workspace** – `/workspaces/:id` with three regions:
   - **Sources** (left fixed 300px rail: upload with client pre-check, list, per-id delete, Gmail import modal).
   - **BRD** (center paper card: viewer, inline section editing, PDF + DOCX download with folios).
   - **Q&A** (right fixed 320px rail: optimistic send <16ms, error rollback restoring composer, auto-scroll, justified + hyphenated answers).

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
- Professional document‑style view: DM Sans 600 headings, hairline dividers, `data-table`, `text-input` inline edits, black pill save, stone meta (`Generated/Updated/Edited by you`).
- Reading text `text-justify` + `hyphens-auto lang=en`; paper width adapts to rails (`docMeasure` 720/880/1024px centered; print = white full-width).
- Exports mirror the viewer: justified body, 1.15 leading, gray PDF rules, page folios in both formats.

## Frontend Architecture (current)
```
client/src/
├─ api/ (client, workspaces, sources, brd, gmail)
├─ auth/ (AuthProvider, RequireAuth)
├─ components/
│  ├─ brd/ (BRDViewer, BRDQAPanel)
│  ├─ gmail/ (GmailSourceBrowser)
│  ├─ layout/ (TopBar)
│  └─ ui/ (button, dialog, dropdown-menu, input, label, skeleton, status)
├─ hooks/ (use-flash)
├─ pages/ (LandingPage, AuthPage, WorkspacesPage, WorkspacePage)
├─ App.tsx, main.tsx, index.css
```

## Implementation Status
Done: frontend init, auth flow, protected routes, workspace CRUD, workspace shell, sources + Gmail import, generation integration, viewer, PDF + DOCX downloads, outdated detection + regeneration, empty/error states, per-id delete tracking, Dialog confirms (no `window.confirm`), `index.html` title (`BRD Agent`), `.env.example`, skeletons, API 401 handling, full MiniMax re-skin (Landing/Auth/Workspaces/Workspace), export typography polish + verification, response-time pass (WS1–WS4: dropped Inter/Geist webfonts ≈218KB, vendor `manualChunks`, BRD 5-min + workspaces 60-s stale, gmail-search 90-s gc, batched invalidates, memoized workspace grid).
Remaining: none committed — next is user-directed (product depth or hygiene gaps).

## Verification Commands
- Client: `npm run build` (must be green), preview `/ /auth /workspaces /workspaces/abc` → 200, `npm run lint` (3 pre-existing errors as of 2026-09-18 — do not chase).
- Server: no pytest available; verify with targeted scripts (e.g. throwaway script in `/var/folders/.../opencode/`, never in repo) + `compileall`.
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

*Version 1.2 – 2026‑09‑18*
