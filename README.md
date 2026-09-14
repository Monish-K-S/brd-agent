# BRD Agent

BRD Agent turns scattered project sources into a structured Business Requirements Document (BRD).

Create a workspace, add sources (documents, text files, Gmail threads), and generate a professional BRD you can view in the app and download as PDF or DOCX. Adding more sources later marks the BRD as outdated so you can regenerate it.

## What it does

- **Workspaces:** group all sources and BRDs for one project.
- **Sources:** upload `.txt`, `.pdf`, `.docx` files and import Gmail threads.
- **AI pipeline:** source parsing → text extraction → project knowledge consolidation → BRD generation.
- **BRD viewer:** document-style view with executive summary, objectives, scope, stakeholders, requirements, assumptions, risks, and open questions.
- **Export:** one-click download as PDF or DOCX.
- **Auth:** Google-only sign-in via Supabase.

## Tech stack

**Backend (`server/`):**

- FastAPI + SQLAlchemy + Alembic + Postgres
- Supabase Auth (JWT verification)
- Gemini for BRD generation, Sarvam for extraction
- Parsers: PyMuPDF, python-docx
- Builders: fpdf2 (PDF), python-docx (DOCX)

**Frontend (`client/`):**

- React + Vite + TypeScript
- Tailwind CSS + shadcn/ui
- React Router, TanStack Query, Axios
- Supabase JS for auth

## Repository layout

```text
brd-agent/
  client/   # React + Vite + TS app
    src/
      api/            # Axios + endpoint wrappers
      auth/           # AuthProvider, RequireAuth
      components/     # layout, ui, brd/BRDViewer
      pages/          # Landing, Auth, Workspaces, Workspace
      lib/            # Supabase client
  server/   # FastAPI API
    app/
      api/routes/     # auth, workspace, standard_document,
                      # document_extraction, project_knowledge, brd
      services/       # business logic
      repositories/   # DB access
      db/models/      # SQLAlchemy models
      schemas/        # Pydantic schemas
      ai/             # parsers, extractors, consolidators,
                      # generators, builders, mappers
      integrations/gmail/  # Gmail OAuth + import
    alembic/          # DB migrations
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+ and venv
- Postgres database
- Supabase project with Google OAuth enabled
- API keys: Supabase, Google OAuth client, Sarvam, Gemini

## Run the backend

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in the values in .env (see table below)

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.

Health checks:

- `GET /health` — API status
- `GET /health/database` — database connectivity

### Backend environment variables (`server/.env`)

| Variable | Description |
|---|---|
| `ENVIRONMENT` | `development` / `production` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `DATABASE_URL` | Postgres connection string |
| `SARVAM_API_KEY` | Sarvam API key for extraction |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI |

## Run the frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

Create `client/.env.local`:

```bash
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=http://localhost:8000
```

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Same Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Same Supabase anon key |
| `VITE_API_URL` | Backend base URL |

Other commands:

```bash
npm run build    # type-check + production build
npm run preview  # preview production build
npm run lint     # eslint
```

## User flow

1. Open `/` landing page, click Get Started / Sign In.
2. Sign in on `/auth` with Google.
3. Create a workspace on `/workspaces`.
4. Open `/workspaces/:id`:
   - Upload sources in the Sources panel.
   - Click Generate BRD.
   - View the BRD in the document viewer.
   - Download PDF or DOCX.
   - Add more sources and click Regenerate when prompted.

## API overview

All workspace routes require a Supabase JWT `Authorization: Bearer <token>` header.

- `POST /workspaces` / `GET /workspaces` — create and list workspaces
- `GET /workspaces/{id}` / `DELETE /workspaces/{id}` — workspace detail
- `POST /workspaces/{id}/documents` / `GET /workspaces/{id}/documents` — upload and list sources
- `POST /workspaces/{id}/extract` — extract text from new sources
- `POST /workspaces/{id}/knowledge/consolidate` — build project knowledge
- `POST /workspaces/{id}/brd/generate` — generate BRD
- `GET /workspaces/{id}/brd` — fetch BRD JSON
- `GET /workspaces/{id}/brd/status` — `has_brd`, `has_sources`, `has_new_sources`, `regeneration_required`
- `GET /workspaces/{id}/brd/export/pdf` — download PDF
- `GET /workspaces/{id}/brd/export/docx` — download DOCX
- `GET /integrations/gmail/*` — Gmail OAuth and import
