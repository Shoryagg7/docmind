"""create chunks table

Revision ID: 398fbec4f808
Revises: 
Create Date: 2026-08-29 21:07:16.671603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '398fbec4f808'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
