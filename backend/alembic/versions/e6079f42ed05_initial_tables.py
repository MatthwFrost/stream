"""initial tables

Revision ID: e6079f42ed05
Revises:
Create Date: 2026-04-10 12:10:28.100364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6079f42ed05'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("author", sa.Text, nullable=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("is_paywalled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("raw_tags", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("matched_tags", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("keywords", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("config", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("authority_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("poll_interval", sa.Integer, nullable=False, server_default=sa.text("60")),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sources")
    op.drop_table("tags")
    op.drop_table("articles")
