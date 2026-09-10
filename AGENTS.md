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
- **Auth**: Supabase JS – Google, email/password, logout, persistent sessions.

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
2. **Auth** – `/login`, `/signup`.
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

*Version 1.0 – 2026‑09‑09*