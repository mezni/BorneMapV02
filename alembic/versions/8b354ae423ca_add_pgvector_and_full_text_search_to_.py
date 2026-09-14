"""Add pgvector and full-text search to chunks

Revision ID: 8b354ae423ca
Revises: 7d79bf3baf94
Create Date: 2026-09-14 08:40:28.150689

"""
from typing import Sequence, Union

from alembic import op

revision: str = '8b354ae423ca'
down_revision: Union[str, Sequence[str], None] = '7d79bf3baf94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VECTOR_DIMENSIONS = 1536
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 64
FULLTEXT_LANGUAGE = "english"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        ALTER TABLE chunks
        ALTER COLUMN embedding TYPE vector({VECTOR_DIMENSIONS})
        USING CASE
            WHEN embedding IS NULL
              OR jsonb_typeof(embedding) <> 'array'
              OR jsonb_array_length(embedding) = 0
            THEN NULL
            ELSE embedding::text::vector
        END
        """
    )
    op.execute(
        f"""
        CREATE INDEX ix_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION})
        """
    )
    op.execute(
        f"""
        ALTER TABLE chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('{FULLTEXT_LANGUAGE}', content)) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_chunks_search_vector_gin ON chunks USING gin (search_vector)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_chunks_search_vector_gin")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS search_vector")
    op.execute(
        """
        ALTER TABLE chunks
        ALTER COLUMN embedding TYPE jsonb
        USING CASE
            WHEN embedding IS NULL THEN NULL
            ELSE embedding::text::jsonb
        END
        """
    )
    op.execute("DROP EXTENSION IF EXISTS vector")