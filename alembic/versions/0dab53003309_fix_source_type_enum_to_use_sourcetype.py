"""Fix source_type enum to use SourceType

Revision ID: 0dab53003309
Revises: 7522285c6df6
Create Date: 2026-09-13 20:17:47.601659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0dab53003309'
down_revision: Union[str, Sequence[str], None] = '7522285c6df6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the new enum type first
    source_type_enum = postgresql.ENUM('FILESYSTEM', 'API', 'DATABASE', 'WEBHOOK', name='sourcetype')
    source_type_enum.create(op.get_bind())
    
    # Alter column to use new enum
    op.execute("ALTER TABLE documents ALTER COLUMN source_type TYPE sourcetype USING source_type::text::sourcetype")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate old enum
    document_status_enum = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED', name='documentstatus')
    document_status_enum.create(op.get_bind())
    
    # Alter column back
    op.execute("ALTER TABLE documents ALTER COLUMN source_type TYPE documentstatus USING source_type::text::documentstatus")
    
    # Drop new enum
    op.execute("DROP TYPE IF EXISTS sourcetype")