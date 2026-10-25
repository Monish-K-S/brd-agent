# Sourcify

Sourcify turns scattered project sources into structured project knowledge and a usable Business Requirements Document (BRD).

Create a workspace, add sources (uploaded documents, Gmail threads, Google Drive files), and generate a professional BRD you can view in the app and download as PDF or DOCX. Adding more sources later marks the BRD as outdated so you can regenerate it.

## What it does

- **Workspaces:** group all sources and BRDs for one project.
- **Sources:** upload `.txt`, `.pdf`, `.docx` files, import Gmail threads, and pick files from Google Drive.
- **AI pipeline:** source parsing → text extraction → project knowledge consolidation → BRD generation.
- **BRD viewer:** document-style view with executive summary, objectives, scope, stakeholders, requirements, assumptions, risks, and open questions.
- **Q&A:** ask questions about the BRD and get answers traced back to sources.
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
      api/            # Axios + endpoint wrappers (incl. drive)
      auth/           # AuthProvider, RequireAuth, auth-context, useAuth
      components/     # layout/TopBar, ui/*, brd/BRDViewer + BRDQAPanel,
                      # gmail/GmailSourceBrowser, drive/drivePicker,
                      # ErrorBoundary
      pages/          # Landing, Auth, Workspaces, Workspace, NotFound
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
      integrations/drive/  # Drive OAuth + Picker-token + file import
    alembic/          # DB migrations
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or plain `venv` + `pip`)
- Postgres database
- Supabase project with Google OAuth enabled
- API keys: Supabase, Google OAuth client, Sarvam, Gemini

## Run the backend

```bash
cd server
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt

cp .env.example .env
# Fill in the values in .env (see table below)

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

No `uv`? A standard virtualenv works too:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Backend runs at `http://localhost:8000`.

Health checks:

- `GET /health` — API status
- `GET /health/database` — database connectivity

### Backend environment variables (`server/.env`)

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | no | `development` / `production` (default `development`) |
| `FRONTEND_URL` | yes | Base URL of the SPA (`http://localhost:5173` locally); OAuth redirects target it |
| `SUPABASE_URL` | yes | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | yes | Supabase publishable (anon) key — used for JWKS-based JWT verification |
| `SUPABASE_SERVICE_ROLE_KEY` | no | Supabase service role key |
| `TOKEN_ENCRYPTION_KEY` | yes | Fernet key for stored OAuth tokens. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — the app fails fast at boot without it |
| `OAUTH_STATE_SECRET` | yes | Signs OAuth state JWTs; must differ from `GOOGLE_CLIENT_SECRET`. Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` — the app fails fast at boot without it |
| `DATABASE_URL` | yes | Postgres connection string (`postgresql+psycopg://user:password@host:5432/brd_agent`) |
| `SARVAM_API_KEY` | yes | Sarvam API key for text extraction |
| `GEMINI_API_KEY` | yes | Gemini API key for BRD generation |
| `GOOGLE_CLIENT_ID` | yes | Google OAuth client ID (shared by Gmail + Drive) |
| `GOOGLE_CLIENT_SECRET` | yes | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | yes | Gmail OAuth redirect URI (`.../integrations/gmail/callback`) |
| `GOOGLE_DRIVE_REDIRECT_URI` | yes | Drive OAuth redirect URI (`.../integrations/drive/callback`) |

`server/.env.example` also documents optional tuning knobs (upload caps, rate limits, generation-job timeout, CORS, `ALLOWED_HOSTS`) — copy it to `.env` and edit rather than starting from scratch.

### Upload limits

| Limit | Default | Setting |
|---|---|---|
| Files per request | 10 | `MAX_UPLOAD_FILES` |
| Bytes per file | 10 MB | `MAX_UPLOAD_BYTES` |
| PDF pages per file | 200 | `MAX_PDF_PAGES` |
| Extracted characters per file | 500,000 | `MAX_EXTRACTED_CHARS` |

Parsing happens **inside** the upload request, so a very large batch is slower to respond. Measured worst case (10 × 200-page PDFs) is about **3.3 s** of parsing — the cap that actually binds for text-dense PDFs is `MAX_EXTRACTED_CHARS`, not the page count. For large uploads the file transfer itself, not parsing, is what dominates the request.

Every upload logs `brd-agent.upload: upload: N file(s), B bytes, parse Xs, total Ys`, and each file logs `brd-agent.ingestion: parsed .pdf in Xs -> N document(s), M chars`, so a slow upload can be diagnosed from the log without guessing.

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
VITE_GOOGLE_PICKER_API_KEY=...
VITE_GOOGLE_APP_ID=...
```

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Same Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Same Supabase anon key |
| `VITE_API_URL` | Backend base URL |
| `VITE_GOOGLE_PICKER_API_KEY` | Browser API key restricted to the Google Picker API (Drive file chooser) |
| `VITE_GOOGLE_APP_ID` | Numeric Google Cloud project number for the Picker |

Other commands:

```bash
npm run build    # type-check + production build
npm run preview  # preview production build
npm run lint     # eslint
npm test         # vitest, jsdom (46 tests)
npm run test:watch
```

## User flow

1. Open `/` landing page, click Sign in or Create your first BRD (see How it works on the page).
2. Sign in on `/auth` with Google.
3. Create a workspace on `/workspaces`.
4. Open `/workspaces/:id`:
   - Upload sources in the Sources panel, import Gmail threads, or choose files from Google Drive.
   - Click Generate BRD.
   - View the BRD in the document viewer.
   - Ask questions about the BRD in the Q&A panel.
   - Download PDF or DOCX.
   - Add more sources and click Regenerate when prompted.

## API overview

All workspace routes require a Supabase JWT `Authorization: Bearer <token>` header.

- `POST /workspaces` / `GET /workspaces` — create and list workspaces
- `GET /workspaces/{id}` / `DELETE /workspaces/{id}` — workspace detail
- `POST /workspaces/{id}/documents` / `GET /workspaces/{id}/documents` — upload and list sources
- `POST /workspaces/{id}/brd/generate` — generate BRD (202 + background job)
- `GET /workspaces/{id}/brd` — fetch BRD JSON
- `PUT /workspaces/{id}/brd` — save inline section edits
- `POST /workspaces/{id}/brd/ask` — Q&A over the BRD + sources
- `GET /workspaces/{id}/brd/status` — `has_brd`, `has_sources`, `has_new_sources`, `regeneration_required`
- `GET /workspaces/{id}/brd/export/pdf` — download PDF
- `GET /workspaces/{id}/brd/export/docx` — download DOCX
- `GET /integrations/gmail/*` — Gmail OAuth and import
- `GET /integrations/drive/connect|callback|status|picker-token`, `DELETE /integrations/drive`, `POST /workspaces/{id}/files/import` — Drive OAuth (shared Google client, `drive.file` scope) and Picker file import
- `GET /evals/generations`, `/evals/scenarios`, `/evals/runs`, `/evals/runs/{id}`, `/evals/runs/{id}/report.html`, `POST /evals/run` — **development only**; evaluation records, benchmark catalogue, runs and reports (see below)

## Evaluation harness

The pipeline can be scored, not just run. Two independent layers, and they
answer different questions:

| | Automatic (every generation) | Benchmark (on demand) |
|---|---|---|
| Needs an answer key | No — the extracted knowledge *is* the reference | Yes (`expected.json`) |
| Runs on | Any real workspace | 4 curated scenarios |
| Cost | **zero extra API calls** | 1 Sarvam job per scenario |

### Automatic — every successful generation

`GenerationJobService` scores the BRD it just produced and writes one JSON
record under `server/app/evals/generations/` (pruned to the last 50).
Nothing is re-extracted and no provider is called again.

| Metric | Question |
|---|---|
| `retention` | Did every extracted requirement survive into the BRD? |
| `groundedness` | Is every BRD line traceable to the extracted knowledge? |
| `structure` | Are all 11 sections present and valid? |
| `duplication` | Does the document repeat itself? |
| `latency` | What did each pipeline phase cost? |

Read them at `GET /evals/generations` (or `ls server/app/evals/generations`), or open the **Evaluation** page from a workspace.
Both this and the route are **disabled in production** (`ENVIRONMENT=production`
or `EVAL_ON_GENERATION=false`), and a scoring failure can never fail a
generation.

### Benchmark — the accuracy number

```bash
cd server

.venv/bin/python -m app.evals.run --list
.venv/bin/python -m app.evals.run --scenario smoke          # 1 Sarvam job
.venv/bin/python -m app.evals.run --scenario all            # 4 Sarvam jobs
.venv/bin/python -m app.evals.run --scenario all --replay   # free: reuse cached extraction
.venv/bin/python -m app.evals.run --compare A/results.json B/results.json
```

The same runs are available from the dev-only `/evals` page: pick
scenarios, run in **replay** mode (free, the default) or **live** (one Sarvam
job per scenario, behind an explicit confirmation), watch progress, then open
the report. Only one run may be in flight at a time — a second request gets
**409** rather than starting a duplicate batch.

Each run writes `results.json`, `report.md` and a **self-contained**
`report.html` (opens from disk, no network) under
`server/app/evals/reports/<run-id>/`.

Scenarios are three different products at three documentation depths, so the
run doubles as a scaling study — latency grows with the source material while
recall holds:

| Level | Scenario | Documents | Facts |
|---|---|---|---|
| small | `library-rooms` | 1 | 8 |
| medium | `clinic-booking` | 3 | 18 |
| large | `helpdesk-migration` | 6 | 28 |

`--replay` reuses a cached extraction keyed on the fixture bytes, so
comparison runs are free of Sarvam cost and run on identical input.

**What it does not measure:** semantic correctness, or whether the BRD reads
well. Fact recall is substring ground truth — a correct paraphrase that uses
none of the listed phrasings scores as a miss — and groundedness is a lexical
heuristic that flags suspects rather than proving a hallucination. Repeats
matter: Gemini is nondeterministic, so a single run is not a distribution.

## Deploy

The backend is a **single-process** application. Run exactly one worker:

```bash
uvicorn app.main:app --port 8000
```

Do not pass `--workers N` or run several replicas. Three pieces of state live
in process memory rather than a shared store, so horizontal scaling would
silently misbehave:

- **Rate-limit buckets** (slowapi in-memory storage) — limits would be counted
  per worker instead of globally, so a user gets N× the intended quota.
- **OAuth state / PKCE verifier storage** — a connect started on one process
  fails its callback on another (`Invalid or expired OAuth state`).
- **BRD generation** runs as an in-process `BackgroundTasks` task, so a restart
  terminates any in-flight run. Orphaned jobs are auto-failed after
  `GENERATION_JOB_TIMEOUT_MINUTES`, so a workspace can never be wedged — but
  the user has to regenerate.

Scaling to N workers means moving rate limits, OAuth verifiers, and the
generation pipeline onto shared infrastructure (Redis or the database). Until
then, pin `--workers 1` and scale vertically.

### Production settings

| Setting | Why it matters |
|---|---|
| `ALLOWED_HOSTS` | Defaults to `["*"]` when unset, which makes `TrustedHostMiddleware` a **no-op**. Set your real hostname(s), otherwise Host-header spoofing is unmitigated. |
| `ENVIRONMENT=production` | Enables HSTS and gates `/health/database` behind `EXPOSE_DB_HEALTH`. |
| `CORS_ORIGINS` | Defaults to `http://localhost:5173`; set your real frontend origin(s). |

Security headers for the SPA (CSP, HSTS, `X-Frame-Options`) are configured at
the static host (`vercel.json` / `netlify.toml`), not in this repo — the API is
JSON-only and sets its own headers server-side via `SecurityHeadersMiddleware`.
