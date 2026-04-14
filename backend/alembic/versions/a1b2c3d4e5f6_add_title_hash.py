"""add title_hash to articles

Revision ID: a1b2c3d4e5f6
Revises: e6079f42ed05
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e6079f42ed05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('articles', sa.Column('title_hash', sa.String(64), nullable=True))
    op.create_index('ix_articles_title_hash', 'articles', ['title_hash'])


def downgrade() -> None:
    op.drop_index('ix_articles_title_hash', table_name='articles')
    op.drop_column('articles', 'title_hash')
