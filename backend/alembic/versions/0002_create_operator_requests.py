"""create operator_requests

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.create_table(
        "operator_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticket_id", sa.Integer, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thread_id", sa.String(64), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_operator_requests_status", "operator_requests", ["status"])
    op.create_index("ix_operator_requests_ticket_id", "operator_requests", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_operator_requests_ticket_id", table_name="operator_requests")
    op.drop_index("ix_operator_requests_status", table_name="operator_requests")
    op.drop_table("operator_requests")
