"""BYOK multi-clave: una por proveedor + is_active

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29

Pasa de "una clave BYOK por usuario" (índice único en user_id) a "una clave por
proveedor" (único en (user_id, provider)) y añade `is_active` para marcar cuál
se usa. Backfill: las claves existentes (≤1 por usuario) quedan activas.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_id deja de ser único (ahora se permite una fila por proveedor).
    op.drop_index("ix_user_api_keys_user_id", table_name="user_api_keys")
    op.create_index(
        "ix_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_user_api_keys_user_provider", "user_api_keys", ["user_id", "provider"]
    )
    op.add_column(
        "user_api_keys",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Cada usuario tenía como mucho una clave: déjala activa.
    op.execute("UPDATE user_api_keys SET is_active = true")


def downgrade() -> None:
    # Nota: si algún usuario tiene >1 clave, restaurar el índice único en user_id
    # fallará (es el coste de revertir multi-clave). Aceptable en desarrollo.
    op.drop_column("user_api_keys", "is_active")
    op.drop_constraint(
        "uq_user_api_keys_user_provider", "user_api_keys", type_="unique"
    )
    op.drop_index("ix_user_api_keys_user_id", table_name="user_api_keys")
    op.create_index(
        "ix_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=True
    )
