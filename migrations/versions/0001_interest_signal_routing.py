"""Add interest-signal routing columns

Adds the columns that back the "route by what the person actually chooses,
not by raw score" fix:
  - question_bank.is_interest_signal, question_bank.option_tags
  - results.category_signal_breakdown

Uses `IF NOT EXISTS` so this is safe to run against:
  - an already-deployed database that predates this change (the real target)
  - a brand-new database where create_all() already added these columns
    (running this migration again is then a harmless no-op)

Revision ID: 0001
Revises:
Create Date: 2026-09-08

"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE question_bank ADD COLUMN IF NOT EXISTS is_interest_signal BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE question_bank ADD COLUMN IF NOT EXISTS option_tags JSON")
    op.execute("ALTER TABLE results ADD COLUMN IF NOT EXISTS category_signal_breakdown JSON")
    # Backfill: existing rows get the safe default explicitly, in case the
    # column existed already without one (e.g. added by hand at some point).
    op.execute("UPDATE question_bank SET is_interest_signal = FALSE WHERE is_interest_signal IS NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE question_bank DROP COLUMN IF EXISTS is_interest_signal")
    op.execute("ALTER TABLE question_bank DROP COLUMN IF EXISTS option_tags")
    op.execute("ALTER TABLE results DROP COLUMN IF EXISTS category_signal_breakdown")
