# Sourcify — Client

React + Vite + TypeScript single-page app for Sourcify: workspaces, source management (uploads, Gmail, Google Drive), an 11-section BRD viewer with inline editing, workspace Q&A, and PDF/DOCX export.

## Stack

- React 19 + Vite + TypeScript, React Router, TanStack Query, Axios
- Tailwind CSS v4 (`src/index.css` `@theme` tokens) + shadcn/Base UI primitives
- DM Sans via `@fontsource-variable/dm-sans` (UI/body) + Instrument Serif via `@fontsource/instrument-serif` (`font-display` — brand/display surfaces only)
- Supabase JS for Google-only auth (`src/lib/supabase.ts`)

## Scripts

```bash
npm install
npm run dev      # local dev server
npm run build    # type-check + production build (must be green)
npm run preview  # preview the production build
npm run lint     # eslint (must be clean)
```

## Environment (`client/.env.local`, see `.env.example`)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (`http://localhost:8000`) |
| `VITE_SUPABASE_URL` | Same Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Same Supabase anon key |
| `VITE_GOOGLE_PICKER_API_KEY` | Browser key restricted to the Google Picker API |
| `VITE_GOOGLE_APP_ID` | Numeric Google Cloud project number |

## Structure

```text
src/
  api/            # endpoint wrappers: client, workspaces, sources, brd, gmail, drive
  auth/           # AuthProvider, RequireAuth, auth-context, useAuth
  components/
    brd/          # BRDViewer (11-section document + inline editing), BRDQAPanel (Q&A)
    drive/        # drivePicker.ts — Google Picker helper (no JSX)
    gmail/        # GmailSourceBrowser (search + multiselect import dialog)
    layout/       # TopBar (slot shell)
    ui/           # button, dialog, dropdown-menu, input, label, skeleton, status, use-flash
    ErrorBoundary.tsx
  pages/          # LandingPage, AuthPage, WorkspacesPage, WorkspacePage, NotFoundPage
  lib/            # Supabase client
  App.tsx / main.tsx / index.css
```

## Design

Warm "Editorial AI Workspace" system defined in `src/index.css`: off-white canvas `#F7F7F4`, white surfaces, ink `#151515`, one coral accent `#FF5A36` for in-app primary actions (Generate, Add, Ask, Save) — black pills stay on landing CTAs. `client/DESIGN.md` (MiniMax analysis) is reference only; never edit it unprompted.

Redesigns here are **visual-only**: never alter routes, API shapes, status codes, query keys, mutation logic, or Supabase flows. See the root `AGENTS.md` for the full agent guide.
