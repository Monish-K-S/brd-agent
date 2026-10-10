"""split google_connections per connector (gmail vs drive)

Revision ID: f7a1c9e4b206
Revises: 62d4ff311943
Create Date: 2026-10-10

Gmail and Drive previously shared one google_connections row
(provider="google", last-connect-wins), so disconnecting either killed
both and a Drive grant implicitly carried gmail.readonly. From here each
connector owns its row (provider "gmail" or "drive").

There are no real users yet, so the pre-split rows are wiped instead of
migrated — every connector simply reconnects once. The data wipe is
intentionally one-way; the downgrade only drops the check constraint.

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f7a1c9e4b206'
down_revision: Union[str, Sequence[str], None] = '62d4ff311943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Wipe shared rows and restrict provider to gmail/drive."""

    # Pre-split rows carry an ambiguous scope union and a single shared
    # grant; with no real users, drop them instead of guessing.
    op.execute("DELETE FROM public.google_connections")

    op.execute(
        """
        ALTER TABLE public.google_connections
        ADD CONSTRAINT ck_google_connections_provider
        CHECK (provider IN ('gmail', 'drive'))
        """
    )


def downgrade() -> None:
    """Drop the provider check (wiped rows are not restored)."""

    op.execute(
        "ALTER TABLE public.google_connections "
        "DROP CONSTRAINT IF EXISTS ck_google_connections_provider"
    )
