# BRD‑Agent – Agent Guide

## Overview
- Backend: FastAPI (`server/`).
- Frontend: React + Vite + TS (`client/`).
- Core flow: **Create Workspace → Add Sources → Generate BRD → View/Download → Add More Sources → Regenerate**.

## Backend Context
- Supabase JWT auth (Bearer token).
- AI pipeline (extraction → knowledge → BRD) hidden from UI.
- No need to modify backend unless API contracts break.

## Frontend Stack (locked)
- **Core**: React, Vite, TypeScript.
- **UI**: Tailwind CSS, shadcn/ui.
- **Routing**: React Router.
- **State**: TanStack Query (API), React Context/AuthProvider (auth), `useState` (local).
- **HTTP**: Axios (configured with Supabase token).
- **Auth**: Supabase JS – Google-only (decision: no email/password), logout, persistent sessions.

## API Layout (`client/src/api/`)
```
client.ts   // Axios instance with auth header
workspaces.ts
sources.ts
brd.ts
```
Use TanStack Query for queries & mutations.

## User Flow
1. **Landing** – `/` (Get Started / Sign In).
2. **Auth** – `/auth` (Google-only, single page — decision: no `/login`, `/signup`, no email/password).
3. **Workspaces** – `/workspaces` (list, create, delete, open).
4. **Workspace** – `/workspaces/:id` with three panels:
   - **Sources** (upload, list, delete).
   - **BRD** (view, download PDF).
   - *Assistant* (future).

## Workspace States
- `EMPTY` – no sources.
- `SOURCES_READY` – sources present, no BRD.
- `GENERATING` – BRD generation in progress.
- `BRD_READY` – BRD displayed, can download.
- `BRD_OUTDATED` – new sources added after BRD.
- `ERROR` – show retry UI.

## BRD Generation & Regeneration
- User triggers **Generate BRD** (or **Regenerate** when outdated).
- Backend handles extraction & AI; UI only shows progress and results.
- No version history or diff UI in Phase 1.

## BRD Viewer
- Professional document‑style view.
- Download PDF button (implementation added after viewer works).

## Frontend Architecture (initial)
```
client/src/
├─ api/
├─ auth/ (AuthProvider, RequireAuth)
├─ components/ (layout, ui)
├─ pages/ (Landing, Login, Signup, Workspaces, Workspace)
├─ App.tsx, main.tsx, index.css
```
Create sub‑folders only when code grows.

## Implementation Order
1. Init frontend & install stack.
2. Auth flow.
3. Protected routes.
4. Workspace list & creation.
5. Workspace shell/layout.
6. Sources panel & upload.
7. BRD generation integration.
8. BRD viewer.
9. PDF download.
10. Detect outdated BRD & regeneration.
11. End‑to‑end test & fix.

## Development Principles
- Build small increments; test against backend each step.
- Keep dependencies minimal; add only when needed.
- Hide AI internals from users.
- Follow existing API contracts.
- Prioritize real bugs over speculative refactoring.
- Ensure accessibility (WCAG 2.1 AA) and responsive design.

## Known Gaps – Fix Later (added 2026-09-10 from `client/` review)

### Critical
1. **No BRD viewer** – `api/brd.ts#getBRD` exists but `pages/WorkspacePage.tsx` never calls it. `BRD_READY` state only renders "BRD is up to date." text. Need `useQuery(["brd", id])` + document-style viewer rendering `brd_data`.
2. **No PDF download** – no download button in UI; backend has no `/brd/download` endpoint (`server/app/api/routes/brd.py` only has `generate`, `status`, `get`). Decide: `window.print()` CSS vs new backend route, then add button after viewer works.
3. **Generate guard too narrow** – `WorkspacePage.tsx#handleGenerateBRD` returns early on `!brdStatus?.has_new_sources`. Must allow `has_new_sources || regeneration_required`. Also: disable Generate/Regenerate button while `generationStep !== "idle"` (prevent double LLM run), and invalidate `["brd", id]` + `["brd-status", id]` after success (currently only `brd-status`).
4. **Workspace states not fully mapped** – `EMPTY` / `SOURCES_READY` / `ERROR` lack explicit empty-state guidance + retry UI. Add: no-sources prompt to upload, sources-ready prompt to generate, error retry for status/documents/BRD queries.

### Medium / Polish
- **Routing**: no `*` 404 route; authed users still see generic `/` landing instead of redirect to `/workspaces`; landing has duplicate Get Started / Sign In buttons both → `/auth`.
- **Delete UX**: `deleteMutation.isPending` disables all rows. Track pending per-id in `WorkspacesPage.tsx` and `WorkspacePage.tsx`.
- **Confirm dialogs**: `window.confirm` used for delete. Replace with shadcn `Dialog`/`AlertDialog`.
- **Upload input a11y**: file `<label>`-as-button wrapper in `WorkspacePage.tsx` is not keyboard-operable. Use `htmlFor` + real `Button`; add client-side size/count validation before upload.
- **API client hardening** (`api/client.ts`): no fallback/warning when `VITE_API_URL` missing (falls back to same-origin confusingly); no 401/expired-token handling.
- **Deps cleanup**: `cn` npm package used instead of local `@/lib/utils`; `shadcn` CLI listed as runtime dep — remove; verify `lucide-react` version.
- **Hygiene**: `index.html` title still `client`; add `.env.example`; add error boundaries + loading skeletons; dedupe landing buttons.

*Version 1.1 – 2026‑09‑10*