"""add hnsw index on chunks embedding

Revision ID: 4b925de70d4b
Revises: 398fbec4f808
Create Date: 2026-08-29 21:28:02.250093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b925de70d4b'
down_revision: Union[str, Sequence[str], None] = '398fbec4f808'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX chunks_embedding_hnsw_idx "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS chunks_embedding_hnsw_idx")
