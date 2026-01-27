"""Add category and nationality to social_accounts

Revision ID: a1b2c3d4e5f6
Revises: e153d985cf12
Create Date: 2026-01-25 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e153d985cf12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add category column
    op.add_column('social_accounts', sa.Column('category', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_social_accounts_category'), 'social_accounts', ['category'], unique=False)
    
    # Add nationality column
    op.add_column('social_accounts', sa.Column('nationality', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_social_accounts_nationality'), 'social_accounts', ['nationality'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove nationality column
    op.drop_index(op.f('ix_social_accounts_nationality'), table_name='social_accounts')
    op.drop_column('social_accounts', 'nationality')
    
    # Remove category column
    op.drop_index(op.f('ix_social_accounts_category'), table_name='social_accounts')
    op.drop_column('social_accounts', 'category')
