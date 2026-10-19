"""add tickets.access_token

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column("tickets", sa.Column("access_token", sa.String(64)))
    op.create_index("ix_tickets_access_token", "tickets", ["access_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tickets_access_token", table_name="tickets")
    op.drop_column("tickets", "access_token")
