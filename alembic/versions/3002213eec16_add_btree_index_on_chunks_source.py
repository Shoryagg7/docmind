"""add btree index on chunks source

Revision ID: 3002213eec16
Revises: 4b925de70d4b
Create Date: 2026-08-30 01:13:25.222888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3002213eec16'
down_revision: Union[str, Sequence[str], None] = '4b925de70d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("chunks_source_idx", "chunks", ["source"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("chunks_source_idx", table_name="chunks")
