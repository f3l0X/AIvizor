"""training_attempts table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("sample", postgresql.JSONB(), nullable=False),
        sa.Column("user_answer", postgresql.JSONB(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_training_attempts_created_at", "training_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_training_attempts_created_at", table_name="training_attempts")
    op.drop_table("training_attempts")
