# BRD-Agent — agent notes

- Backend only (`server/`); `frontend/` is empty placeholder.
- AI pipeline: `app/ai/` pure Python (no FastAPI); Sarvam extracts, Gemini synthesizes.
- Env: copy `server/.env.example` → `server/.env`; `.env` is already gitignored.
- Migrations: `cd server && alembic upgrade head` (2 revisions exist).
- Start: `cd server && uvicorn app.main:app --reload`
- Test commands: `python -m pytest tests/`, `python test_models.py`
- Dead code removed: `app/services/__init__.py` (old WorkspaceService); live one is `workspace_service.py`.
