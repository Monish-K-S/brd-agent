# BRD-Agent — agent notes

- Backend only (`server/`); `client/` is empty placeholder.
- AI pipeline: `app/ai/` pure Python (no FastAPI); Sarvam extracts, Gemini synthesizes.
- Env: copy `server/.env.example` → `server/.env`; `.env` is already gitignored.
- Migrations: `cd server && alembic upgrade head` (2 revisions exist).
- Start: `cd server && uvicorn app.main:app --reload`
- Test commands: `python -m pytest tests/`, `python test_models.py`
- Dead code removed: `app/services/__init__.py` (old WorkspaceService); live one is `workspace_service.py`.

---

## Frontend Implementation Roadmap (React + Vite)

### Confirmed Stack
- React 18 + Vite + TypeScript
- Tailwind CSS + Headless UI
- React Router v6
- @tanstack/react-query (data fetching)
- Zustand (lightweight UI state)
- react-hook-form + Yup (forms & validation)
- axios + Bearer-token interceptor (HTTP)
- `@supabase/supabase-js` — **client-side auth** (login/register/session/auto-refresh)
- react-dropzone (file upload)
- react-markdown (BRD viewer)
- jsPDF (client-side PDF export of BRD)
- Vitest + Testing Library + Playwright (testing)
- ESLint + Prettier (lint/format)
- Auth: Supabase session in `localStorage`; axios attaches `Authorization: Bearer <access_token>` (Supabase SDK handles token refresh)
- Deployment: static build → Vercel/Netlify **or** Docker (nginx)

### Repository Structure (target)
```
brd-agent/
├── client/                     ← new SPA
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── api/
│   │   │   ├── axios.ts          ← axios instance + Bearer interceptor (reads Supabase session)
│   │   │   ├── workspaces.ts
│   │   │   ├── documents.ts
│   │   │   ├── knowledge.ts
│   │   │   └── brd.ts
│   │   ├── auth/
│   │   │   ├── AuthProvider.tsx  ← Context wrapping Supabase session
│   │   │   ├── useAuth.ts
│   │   │   └── RequireAuth.tsx   ← protected route wrapper
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Topbar.tsx
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Toast.tsx
│   │   │   │   └── Spinner.tsx
│   │   │   ├── workspace/
│   │   │   │   ├── WorkspaceCard.tsx
│   │   │   │   ├── CreateWorkspaceModal.tsx
│   │   │   │   └── DeleteWorkspaceButton.tsx
│   │   │   ├── documents/
│   │   │   │   ├── DropzoneUploader.tsx
│   │   │   │   ├── ExtractionLoading.tsx   ← loading state (synchronous AI call)
│   │   │   │   └── ExtractionResult.tsx
│   │   │   ├── knowledge/
│   │   │   │   ├── KnowledgeViewer.tsx     ← read-only render of knowledge_data
│   │   │   │   └── ConsolidateButton.tsx   ← triggers POST .../project-knowledge/consolidate
│   │   │   └── brd/
│   │   │       ├── GenerateBRDButton.tsx
│   │   │       ├── BRDStatusBanner.tsx     ← warns when regeneration_required
│   │   │       ├── BRDViewer.tsx
│   │   │       └── DownloadMenu.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── WorkspaceList.tsx
│   │   │   ├── WorkspaceDetail.tsx        ← tabs: Documents / Knowledge / BRD
│   │   │   ├── Profile.tsx
│   │   │   └── NotFound.tsx
│   │   ├── hooks/
│   │   │   ├── useWorkspaces.ts
│   │   │   ├── useDocuments.ts
│   │   │   ├── useKnowledge.ts
│   │   │   └── useBRD.ts
│   │   ├── schemas/              ← Yup validation
│   │   │   ├── workspace.ts
│   │   │   └── auth.ts
│   │   ├── store/                ← Zustand stores
│   │   │   └── uiStore.ts        ← sidebar toggle, theme, etc.
│   │   ├── lib/
│   │   │   ├── queryClient.ts
│   │   │   ├── supabase.ts       ← Supabase client (URL + anon key from env)
│   │   │   └── env.ts
│   │   ├── styles/
│   │   │   └── tailwind.css
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── router.tsx
│   ├── tests/
│   │   ├── setup.ts
│   │   ├── components/
│   │   └── pages/
│   ├── .env.example
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── index.html
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── README.md
└── server/                       ← existing backend (unchanged)
```

### File-Level Tasks

#### Phase 0 – Bootstrap
- [ ] Init Vite + React + TS in `client/` (`npm create vite@latest client -- --template react-ts`)
- [ ] Install all stack dependencies
- [ ] Configure Tailwind (`tailwind.config.js`, `postcss.config.js`, `src/styles/tailwind.css`)
- [ ] Create `.env.example` with `VITE_API_URL=http://localhost:8000`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [ ] Set Vite proxy `/api → http://localhost:8000` in `vite.config.ts`
- [ ] Configure ESLint + Prettier (Airbnb + TS rules)
- [ ] Enable strict TypeScript (`tsconfig.json`)

#### Phase 1 – Core Infrastructure
- [ ] Supabase client setup → `src/lib/supabase.ts` (URL + anon key from `import.meta.env`)
- [ ] Axios instance with Bearer-token interceptor (reads Supabase session) → `src/api/axios.ts`
- [ ] React Query client → `src/lib/queryClient.ts`
- [ ] Auth context wrapping Supabase session (login/logout/refresh handled by SDK) → `src/auth/AuthProvider.tsx`
- [ ] `useAuth` hook exposing Supabase session/user → `src/auth/useAuth.ts`
- [ ] Protected route wrapper → `src/auth/RequireAuth.tsx`
- [ ] Global error boundary + toast provider → `src/components/ui/Toast.tsx`
- [ ] Routing skeleton → `src/router.tsx`, `src/main.tsx`
- [ ] Layout shell (sidebar + topbar) → `src/components/layout/*`
- [ ] UI primitives (Button, Input, Modal, Spinner) → `src/components/ui/*`
- [ ] Zustand UI store → `src/store/uiStore.ts`
- [ ] Env: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` in `client/.env.example`

#### Phase 2 – Auth Pages
- [ ] Yup schemas → `src/schemas/auth.ts`
- [ ] Login page → `src/pages/Login.tsx` (calls `supabase.auth.signInWithPassword`)
- [ ] Register page → `src/pages/Register.tsx` (calls `supabase.auth.signUp`)
- [ ] Logout button in Topbar → `src/components/layout/Topbar.tsx` (calls `supabase.auth.signOut`)
- [ ] Note: no backend auth endpoints to consume — Supabase SDK is the source of truth

#### Phase 3 – Workspaces
- [ ] Yup schema → `src/schemas/workspace.ts`
- [ ] API functions → `src/api/workspaces.ts`
- [ ] React Query hooks → `src/hooks/useWorkspaces.ts`
- [ ] Workspace list page → `src/pages/WorkspaceList.tsx`
- [ ] Workspace card → `src/components/workspace/WorkspaceCard.tsx`
- [ ] Create modal → `src/components/workspace/CreateWorkspaceModal.tsx`
- [ ] Delete button → `src/components/workspace/DeleteWorkspaceButton.tsx`
- [ ] Detail page with tabs (Documents / Knowledge / BRD) → `src/pages/WorkspaceDetail.tsx`

#### Phase 4 – Document Upload & Extraction (per-workspace)
- [ ] API functions (multipart upload to `/workspaces/{id}/documents/upload`, field `files`, types `.txt/.pdf/.docx`) → `src/api/documents.ts`
- [ ] Hooks → `src/hooks/useDocuments.ts`
- [ ] Dropzone component → `src/components/documents/DropzoneUploader.tsx`
- [ ] Loading UI for synchronous `POST .../extractions` (long-running AI call, no polling) → `src/components/documents/ExtractionLoading.tsx`
- [ ] Result viewer (renders `document_knowledge`) → `src/components/documents/ExtractionResult.tsx`

#### Phase 5 – Project Knowledge (read-only)
- [ ] API functions (`GET .../project-knowledge`, `POST .../project-knowledge/consolidate`) → `src/api/knowledge.ts`
- [ ] Hooks → `src/hooks/useKnowledge.ts`
- [ ] Read-only viewer of `knowledge_data` JSON → `src/components/knowledge/KnowledgeViewer.tsx`
- [ ] Consolidate button → `src/components/knowledge/ConsolidateButton.tsx`
- [ ] Integrate Knowledge tab into `WorkspaceDetail.tsx`

#### Phase 6 – BRD Generation
- [ ] API functions (`POST .../brd/generate` returns full BRD; `GET .../brd`, `GET .../brd/status`) → `src/api/brd.ts`
- [ ] Hooks → `src/hooks/useBRD.ts`
- [ ] Generate button → `src/components/brd/GenerateBRDButton.tsx`
- [ ] Regeneration banner when `regeneration_required` → `src/components/brd/BRDStatusBanner.tsx`
- [ ] Markdown viewer → `src/components/brd/BRDViewer.tsx`
- [ ] Download menu (PDF via `jsPDF`, client-side) → `src/components/brd/DownloadMenu.tsx`
- [ ] Integrate BRD tab into `WorkspaceDetail.tsx`

#### Phase 7 – Testing
- [ ] Vitest config → `client/vitest.config.ts`
- [ ] Setup file → `tests/setup.ts`
- [ ] Unit tests for components & hooks → `tests/components/*`, `tests/pages/*`
- [ ] Mock API with MSW (dev only) → `src/api/msw/handlers.ts`
- [ ] Playwright e2e → `tests/e2e/*.spec.ts`

#### Phase 8 – CI / Deployment
- [ ] GitHub Actions: lint + test + build → `.github/workflows/client-ci.yml`
- [ ] Dockerfile (nginx) → `client/Dockerfile`
- [ ] Build script → `package.json` (`"build": "vite build"`)
- [ ] Client README quick-start → `client/README.md`

### Verified Backend Contract (locked in)
| Concern | Decision / Contract |
|---------|--------------------|
| **Auth** | **Supabase client-side** (`@supabase/supabase-js`). Backend has no login/refresh/register routes — only `GET /auth/me`. Supabase SDK owns session + token refresh; axios attaches `Authorization: Bearer <access_token>` |
| **Token transport** | **Bearer JWT** (`HTTPBearer`). No httpOnly cookie. JWT validated against Supabase JWKS (RS256/ES256) |
| **Document upload** | `POST /workspaces/{id}/documents/upload` — multipart field `files` (list), `.txt/.pdf/.docx` only, returns `StandardDocumentResponse[]` |
| **Document list / get / delete** | `GET /workspaces/{id}/documents`, `GET/DELETE /workspaces/{id}/documents/{doc_id}` |
| **Extraction** | `POST /workspaces/{id}/extractions` — **synchronous**, returns `DocumentExtractionResponse` (no polling). Long AI call → UI loading state |
| **Project knowledge** | **Read-only** for now. `GET /workspaces/{id}/project-knowledge`, `POST .../project-knowledge/consolidate`. No CRUD endpoints for individual items |
| **BRD** | `POST /workspaces/{id}/brd/generate` returns full BRD. `GET .../brd` fetches it. `GET .../brd/status` → `{has_brd, has_new_sources, regeneration_required}` for banner |
| **Workspaces** | `GET/POST /workspaces`, `GET/DELETE /workspaces/{id}`. **No update endpoint** — drop any rename/edit UI |
| **CORS** | Backend allows `http://localhost:3000`. Dev must use **Vite proxy** (default Vite port 5173) so browser sees same-origin. Add prod origin to backend before deploy |

### Pipeline Flow
`Upload docs` → `Extract` (sync) → `Consolidate project knowledge` → `Generate BRD`. WorkspaceDetail tabs reflect each step: **Documents → Knowledge → BRD**.

### Timeline (solo dev)
| Week | Milestone |
|------|-----------|
| 1 | Phases 0‑2 (bootstrap, infra, Supabase auth) |
| 2 | Phase 3‑4 (workspaces + document upload + extraction) |
| 3 | Phase 5‑6 (knowledge viewer + BRD generation) |
| 4 | Phase 7‑8 (testing + CI/deploy) |
| 5 | Polish + docs |

