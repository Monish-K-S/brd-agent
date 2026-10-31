# Sourcify

[![Live demo](https://img.shields.io/badge/live_demo-sourcify.pages.dev-FF5C3B?style=flat-square)](https://sourcify.pages.dev)
[![CI](https://github.com/Monish-K-S/brd-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Monish-K-S/brd-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-151515?style=flat-square)](LICENSE)

**Sourcify turns scattered project sources into a structured Business Requirements Document.**

Create a workspace, add sources — uploaded documents, Gmail threads, Google Drive files — and
generate a professional BRD you can read in the app, edit inline, download as PDF or DOCX, and
question with answers traced back to the sources that produced them. Add more sources later and the
document is marked outdated, so you can regenerate it.

**[Try the live demo →](https://sourcify.pages.dev)**

> The demo runs on free tiers. The API sleeps after 15 minutes idle, so the first
> request after a quiet spell takes about a minute to wake. Everything after that is normal.

![Sourcify workspace: sources rail, BRD viewer and Q&A panel](docs/screenshots/03-workspace.png)

## At a glance

| | |
|---|---|
| **Tests** | 291 backend (pytest) + 46 frontend (Vitest), both gating CI |
| **API** | 27 routes in production, 34 with the dev-only evaluation harness mounted |
| **Pipeline** | ~34 s end to end for a fresh-source generation (measured locally; the spend is API-bound, not CPU-bound) |
| **Generation** | 22.8 s → 14.4 s after the dedup + reasoning-budget pass (−37%) |
| **Sources** | PDF · DOCX · TXT · Gmail · Google Drive |
| **Exports** | PDF (fpdf2) and DOCX (python-docx), both folio-numbered |

## What it does

- **Workspaces** — one place per project, holding every source and its BRD.
- **Sources** — upload `.pdf`, `.docx` and `.txt` files, import Gmail threads, or pick files from
  Google Drive. Upload caps are enforced server-side (10 files, 10 MB each).
- **AI pipeline** — parse → extract → consolidate into project knowledge → generate the BRD.
- **BRD viewer** — an 11-section document (executive summary, project overview, business
  objectives, scope, stakeholders, business/functional/non-functional requirements, assumptions
  and constraints, risks and decisions, open questions) rendered like a real document, editable
  section by section.
- **Q&A** — ask questions about the BRD; every answer cites the source rows it used.
- **Exports** — one click to PDF or DOCX, typography matching the viewer.
- **Auth** — Google-only sign-in through Supabase. Gmail and Drive are separate, least-privilege
  grants (`gmail.readonly` and `drive.file`), so connecting one never touches the other.

### The flow

1. Sign in with Google on `/auth`.
2. Create a workspace on `/workspaces`.
3. Add sources — upload files, import Gmail threads, or pick Drive documents.
4. Generate the BRD and read it in the viewer.
5. Edit sections, ask questions, export, then add more sources and regenerate when prompted.

## Screenshots

The workspace view is the image at the top of this README; the rest of the product:

**Landing** — what the product does, in one screen.

![Landing page](docs/screenshots/01-landing.png)

**Workspaces** — every project in one index.

![Workspaces](docs/screenshots/02-workspaces.png)

**BRD viewer** — 11 sections, edited in place and saved with the black pill.

![BRD viewer](docs/screenshots/04-brd-viewer.png)

**Q&A** — answers cite the source rows they came from.

![Q&A panel](docs/screenshots/05-qa.png)

**Export** — the same document as a folio-numbered PDF.

![Exported PDF](docs/screenshots/06-export.png)

## How it works

```mermaid
flowchart LR
  A["Upload · Gmail · Drive"] --> B["Parsers<br/>PyMuPDF · python-docx · TXT"]
  B --> C["Sarvam<br/>structured extraction"]
  C --> D["Knowledge consolidation<br/>dedup + merge"]
  D --> E["Gemini<br/>BRD generation"]
  E --> F["BRD viewer<br/>inline editing"]
  E --> G["PDF / DOCX export"]
  F --> H["Q&A<br/>source-traced answers"]

  classDef stage fill:#FFFDF8,stroke:#DDD8CD,color:#151515,stroke-width:1px
  classDef accent fill:#FFF0EB,stroke:#FF5C3B,color:#C43A17,stroke-width:1.25px
  class A,B,C,D,F,G,H stage
  class E accent
```

Two decisions worth knowing about, because both were measured rather than assumed:

- **Dedup is not cosmetic.** The consolidator removes byte-identical items before generation —
  they were 52–60% of a workspace's items — because the prompt forbids merging genuinely distinct
  requirements, so the model was spending reasoning tokens reconciling exact repeats. Removing
  them alone did not speed things up; it made the reasoning pass affordable.
- **Generation is one call with a fixed thinking budget** (`GEMINI_THINKING_BUDGET`, default
  2048), with an explicit 2-attempt retry and a 120 s timeout. Newer reasoning-tuned models
  measured 3–20× slower on this constrained restructuring task, so the win came from cleaning the
  input, not from swapping models.

## Architecture

Where each piece runs, and what talks to what:

![Sourcify runtime architecture: a React SPA on Cloudflare Pages calls a single-process FastAPI service on Render, which owns PostgreSQL access in Supabase and calls Sarvam, Gemini and the Google APIs](docs/architecture.svg)

The coral chip is the only stateful path: generation runs as a `BackgroundTasks` job inside the
API process, which is why a restart mid-run has to be recovered rather than resumed. The
[Deploy](#deploy) section explains what that rules out.

## Tech stack

**Backend (`server/`):**

- FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL
- Supabase Auth (JWKS-verified JWTs)
- Gemini for BRD generation, Sarvam for structured extraction
- Parsers: PyMuPDF, python-docx; builders: fpdf2 (PDF), python-docx (DOCX)
- Google APIs for Gmail import and Drive file picking
- slowapi rate limiting, Fernet-encrypted OAuth tokens, `SecurityHeadersMiddleware`

**Frontend (`client/`):**

- React 19 + Vite + TypeScript
- Tailwind CSS v4 + shadcn/ui
- TanStack Query, React Router, Axios
- Supabase JS for auth
- Vitest + Testing Library, ESLint

## Run locally

**Prerequisites:** Node.js 20+, Python 3.11+ with [uv](https://docs.astral.sh/uv/) (or a plain
`venv` + `pip`), a PostgreSQL database, a Supabase project with Google OAuth enabled, and Sarvam
and Gemini API keys.

### Backend

```bash
cd server
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt

cp .env.example .env
# Fill in the values (see the table below)

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

The API runs at `http://localhost:8000`.

Health checks:

- `GET /health` — API status
- `GET /health/database` — database connectivity (gated behind `EXPOSE_DB_HEALTH` in production)

### Frontend

```bash
cd client
npm install
npm run dev
```

The app runs at `http://localhost:5173`. Create `client/.env.local`:

```bash
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_PICKER_API_KEY=...
VITE_GOOGLE_APP_ID=...
```

Other commands:

```bash
npm run build    # type-check + production build
npm run preview  # preview the production build
npm run lint     # eslint
npm test         # vitest + jsdom (46 tests)
npm run test:watch
```

## Configuration

### Backend (`server/.env`)

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

`server/.env.example` also documents the optional tuning knobs (upload caps, rate limits,
generation-job timeout, CORS, `ALLOWED_HOSTS`, Gemini budget and model) — copy it to `.env` and
edit rather than starting from scratch.

### Frontend (`client/.env.local`)

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Same Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Same Supabase anon key |
| `VITE_API_URL` | Backend base URL |
| `VITE_GOOGLE_PICKER_API_KEY` | Browser API key restricted to the Google Picker API (Drive file chooser) |
| `VITE_GOOGLE_APP_ID` | Numeric Google Cloud project number for the Picker |

`VITE_*` values are inlined at **build** time, so changing one requires a rebuild — not a restart.

### Google Picker setup

The Drive file chooser needs three console settings, and each fails with an error that does not
name it:

| Setting | Where | If it is missing |
|---|---|---|
| `https://<your-origin>/*` in **HTTP referrers** | Credentials → the browser API key | *"The API developer key is invalid"* dialog |
| **Google Picker API** enabled | APIs & Services → Library | the same dialog as above |
| `https://<your-origin>` in **Authorized JavaScript origins** | Credentials → the OAuth client | `origin_mismatch` |

Two pairs that are easy to conflate:

- **JavaScript origins** vs **redirect URIs** are different fields on the same client. The redirect
  URIs handle the OAuth callback; the origins handle the Picker's own origin check.
- A wildcard `*.pages.dev` does **not** match `pages.dev` — it covers subdomains only, so a
  Cloudflare Pages project needs its exact hostname listed.

`VITE_GOOGLE_APP_ID` must be the **project number** of the project that owns both the key and the
OAuth client. A cross-project app ID is the worst case of the four: the Picker opens, shows an
empty or partial file list, and reports nothing.

### Upload limits

| Limit | Default | Setting |
|---|---|---|
| Files per request | 10 | `MAX_UPLOAD_FILES` |
| Bytes per file | 10 MB | `MAX_UPLOAD_BYTES` |
| PDF pages per file | 200 | `MAX_PDF_PAGES` |
| Extracted characters per file | 500,000 | `MAX_EXTRACTED_CHARS` |

Parsing happens **inside** the upload request, so a very large batch is slower to respond.
Measured worst case (10 × 200-page PDFs) is about **3.3 s** of parsing — the cap that actually
binds for text-dense PDFs is `MAX_EXTRACTED_CHARS`, not the page count. For large uploads the file
transfer itself, not parsing, is what dominates the request.

Every upload logs `brd-agent.upload: upload: N file(s), B bytes, parse Xs, total Ys`, and each file
logs `brd-agent.ingestion: parsed .pdf in Xs -> N document(s), M chars`, so a slow upload can be
diagnosed from the log without guessing.

## API overview

All workspace routes require a Supabase JWT `Authorization: Bearer <token>` header.

- `POST /workspaces` / `GET /workspaces` — create and list workspaces
- `GET /workspaces/{id}` / `DELETE /workspaces/{id}` — workspace detail
- `POST /workspaces/{id}/documents` / `GET /workspaces/{id}/documents` — upload and list sources
- `GET /workspaces/{id}/documents/{document_id}` — one source, including its extracted content
- `POST /workspaces/{id}/brd/generate` — generate BRD (202 + background job)
- `GET /workspaces/{id}/brd` — fetch BRD JSON
- `PUT /workspaces/{id}/brd` — save inline section edits
- `POST /workspaces/{id}/brd/ask` — Q&A over the BRD + sources
- `GET /workspaces/{id}/brd/status` — `has_brd`, `has_sources`, `has_new_sources`, `regeneration_required`
- `GET /workspaces/{id}/brd/export/pdf` — download PDF
- `GET /workspaces/{id}/brd/export/docx` — download DOCX
- `GET /integrations/gmail/*` — Gmail OAuth and import
- `GET /integrations/drive/connect|callback|status|picker-token`, `DELETE /integrations/drive`,
  `POST /workspaces/{id}/files/import` — Drive OAuth (shared Google client, `drive.file` scope) and
  Picker file import
- `GET /evals/generations`, `/evals/scenarios`, `/evals/runs`, `/evals/runs/{id}`,
  `/evals/runs/{id}/report.html`, `POST /evals/run` — **development only**; evaluation records,
  benchmark catalogue, runs and reports (see below)

## Evaluation harness

The pipeline can be scored, not just run. Two independent layers, answering different questions:

| | Automatic (every generation) | Benchmark (on demand) |
|---|---|---|
| Needs an answer key | No — the extracted knowledge *is* the reference | Yes (`expected.json`) |
| Runs on | Any real workspace | 3 curated scenarios |
| Cost | **zero extra API calls** | 1 Sarvam job per scenario |

### Automatic — every successful generation

`GenerationJobService` scores the BRD it just produced and writes one JSON record under
`server/app/evals/generations/` (pruned to the last 50). Nothing is re-extracted and no provider is
called again.

| Metric | Question |
|---|---|
| `retention` | Did every extracted requirement survive into the BRD? |
| `groundedness` | Is every BRD line traceable to the extracted knowledge? |
| `structure` | Are all 11 sections present and valid? |
| `duplication` | Does the document repeat itself? |
| `latency` | What did each pipeline phase cost? |

Read them at `GET /evals/generations` (or `ls server/app/evals/generations`), or open the
**Evaluation** page from a workspace. Both the recorder and the routes are **disabled in
production** (`ENVIRONMENT=production` or `EVAL_ON_GENERATION=false`), and a scoring failure can
never fail a generation.

### Benchmark — the accuracy number

```bash
cd server

.venv/bin/python -m app.evals.run --list
.venv/bin/python -m app.evals.run --scenario library-rooms      # 1 Sarvam job
.venv/bin/python -m app.evals.run --scenario all                # 3 Sarvam jobs
.venv/bin/python -m app.evals.run --scenario all --replay       # free: reuse cached extraction
.venv/bin/python -m app.evals.run --compare A/results.json B/results.json
```

Also useful: `--repeats N` (a latency median needs repeats), `--thinking-budget` and `--model`
(A/B a single change), `--no-dedupe` (the dedup A/B).

The same runs are available from the dev-only `/evals` page: pick scenarios, run in **replay** mode
(free, the default) or **live** (one Sarvam job per scenario, behind an explicit confirmation),
watch progress, then open the report. Only one run may be in flight at a time — a second request
gets **409** rather than starting a duplicate batch.

Each run writes `results.json`, `report.md` and a **self-contained** `report.html` (opens from
disk, no network) under `server/app/evals/reports/<run-id>/`.

Scenarios are three different products at three documentation depths, so the run doubles as a
scaling study — latency grows with the source material while recall holds:

| Level | Scenario | Documents | Facts |
|---|---|---|---|
| small | `library-rooms` | 1 | 8 |
| medium | `clinic-booking` | 3 | 18 |
| large | `helpdesk-migration` | 6 | 28 |

`--replay` reuses a cached extraction keyed on the fixture bytes, so comparison runs are free of
Sarvam cost and run on identical input.

**What it does not measure:** semantic correctness, or whether the BRD reads well. Fact recall is
substring ground truth — a correct paraphrase that uses none of the listed phrasings scores as a
miss — and groundedness is a lexical heuristic that flags suspects rather than proving a
hallucination. Repeats matter: Gemini is nondeterministic, so a single run is not a distribution.

## Deploy

The backend is a **single-process** application. Run exactly one worker:

```bash
uvicorn app.main:app --port 8000
```

Do not pass `--workers N` or run several replicas. Three pieces of state live in process memory
rather than a shared store, so horizontal scaling would silently misbehave:

- **Rate-limit buckets** (slowapi in-memory storage) — limits would be counted per worker instead
  of globally, so a user gets N× the intended quota.
- **OAuth state / PKCE verifier storage** — a connect started on one process fails its callback on
  another (`Invalid or expired OAuth state`).
- **BRD generation** runs as an in-process `BackgroundTasks` task, so a restart terminates any
  in-flight run. Orphaned jobs are auto-failed after `GENERATION_JOB_TIMEOUT_MINUTES`, so a
  workspace can never be wedged — but the user has to regenerate.

Scaling to N workers means moving rate limits, OAuth verifiers, and the generation pipeline onto
shared infrastructure (Redis or the database). Until then, pin `--workers 1` and scale vertically.

### Production settings

| Setting | Why it matters |
|---|---|
| `ALLOWED_HOSTS` | Defaults to `["*"]` when unset, which makes `TrustedHostMiddleware` a **no-op**. Set your real hostname(s), otherwise Host-header spoofing is unmitigated. |
| `ENVIRONMENT=production` | Enables HSTS, unmounts `/evals` and its evaluation records, and gates `/health/database` behind `EXPOSE_DB_HEALTH`. |
| `CORS_ORIGINS` | Defaults to `http://localhost:5173`; set your real frontend origin(s). |

Security headers for the SPA (CSP, HSTS, `X-Frame-Options`) are configured at the static host
(`vercel.json` / `netlify.toml`), not in this repo — the API is JSON-only and sets its own headers
server-side via `SecurityHeadersMiddleware`.

### Current deployment

A free-tier deployment, sized for a demo rather than production:

| Piece | Where |
|---|---|
| SPA | Cloudflare Pages — root `client`, build `npm run build`, output `dist` |
| API | Render — root `server`, region Singapore |
| Database | Supabase `ap-south-1`, via the Supavisor pooler |
| CI | `.github/workflows/ci.yml` — server `pytest`, client lint/test/build |

Render start command (the proxy flags are mandatory — Render terminates TLS and forwards
`X-Forwarded-For`, and without them headerless OAuth callbacks key rate limiting on Render's proxy
IP instead of the client's):

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

Five settings that fail in ways which do not name their cause:

| Symptom | Cause | Fix |
|---|---|---|
| Every request returns **400 Invalid host header** | `ALLOWED_HOSTS` does not match the real host | Set it to the exact hostname; `TrustedHostMiddleware` turns a mismatch into a 400 before any route runs |
| `ModuleNotFoundError: psycopg2` on boot | `DATABASE_URL` uses a bare `postgresql://` scheme | Keep `postgresql+psycopg://` — only psycopg 3 is installed |
| Boot hangs / fails to reach the database | Direct host `db.<ref>.supabase.co` is IPv6-only | Use the Supavisor pooler URL (`postgres.<ref>@aws-0-<region>.pooler.supabase.com`) |
| Build fails on a package with no wheel | Host defaults to a newer Python than the pins were resolved against | Set `PYTHON_VERSION=3.11.9` |
| Deployed app calls `localhost:8000` | `VITE_*` values are inlined at **build** time, not read at runtime | Set them before the first build, then rebuild |

Free-tier behaviour worth knowing: a Render free instance sleeps after 15 minutes without traffic
and takes about a minute to wake, so ping `/health` every 10 minutes with any uptime monitor during
a demo window — and **turn the monitor off afterwards**. The allowance is 750 instance hours per
month and it counts *awake* hours, not pings, so a 5- and a 10-minute interval cost exactly the
same. A monitor left running across a full calendar month is roughly 744 of those 750 hours, and
exceeding the allowance suspends the service until the next month. There is also no persistent
disk — exports are written to temp files and evaluation records are disabled because
`ENVIRONMENT=production` (which also unmounts `/evals` and enables HSTS).

## Repository layout

```text
brd-agent/
  client/   # React 19 + Vite + TypeScript app
    public/
    src/
      api/            # Axios instance + endpoint wrappers
                      # (workspaces, sources, brd, gmail, drive, evals)
      auth/           # AuthProvider, RequireAuth, useAuth
      components/
        brand/        # Wordmark, FieldBackdrop
        brd/          # BRDViewer, BRDQAPanel
        drive/        # Google Picker helper (no JSX)
        gmail/        # Gmail source browser
        layout/       # TopBar
        ui/           # button, dialog, dropdown, input, label, skeleton, status
      lib/            # supabase client, files, errors, generation, layout, uploadDedup
      pages/          # Landing, Auth, Workspaces, Workspace, Evals, NotFound
      test/           # Vitest setup + shared helpers
      types/          # shared TypeScript types
  server/   # FastAPI API
    app/
      api/routes/     # auth, workspace, standard_document, brd
      services/       # business logic
      repositories/   # DB access
      db/models/      # SQLAlchemy models
      schemas/        # Pydantic schemas
      ai/             # parsers, extractors, consolidators, generators, builders, mappers
      evals/          # metrics, benchmark runner, reports, dev-only routes
      integrations/
        gmail/        # OAuth + thread import
        drive/        # OAuth + Picker token + streamed file import
    alembic/          # DB migrations
    tests/            # pytest suite (291 tests)
```

## License

MIT — see [LICENSE](LICENSE).
