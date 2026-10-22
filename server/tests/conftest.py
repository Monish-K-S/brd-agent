"""Test environment bootstrap.

``Settings`` has ten required fields with no defaults, so importing
``app.main`` (or anything that constructs the settings singleton) fails on
a machine with no ``server/.env``. That made the suite quietly dependent
on a developer's local file: it passed locally and would fail in CI.

These are placeholder values, not credentials — nothing in the suite
reaches a real provider, database or OAuth endpoint. They are set
unconditionally rather than via ``setdefault`` so a developer's real
``.env`` cannot change what the tests exercise.
"""

import os

REQUIRED_PLACEHOLDERS = {
    "FRONTEND_URL": "http://localhost:5173",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "test-publishable-key",
    "GOOGLE_CLIENT_ID": "test-google-client-id",
    "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
    "GOOGLE_REDIRECT_URI": "http://localhost:8000/integrations/gmail/callback",
    "GOOGLE_DRIVE_REDIRECT_URI": (
        "http://localhost:8000/integrations/drive/callback"
    ),
    "TOKEN_ENCRYPTION_KEY": (
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    ),
    "OAUTH_STATE_SECRET": "test-oauth-state-secret",
    "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test",
}

# Set before any test module imports app code, because the settings
# singleton is built at import time.
os.environ.update(REQUIRED_PLACEHOLDERS)

os.environ.setdefault("ENVIRONMENT", "development")

# Keep the evaluation harness from writing into the repository during
# tests; individual tests opt in with an explicit directory.
os.environ.setdefault("EVAL_ON_GENERATION", "false")
