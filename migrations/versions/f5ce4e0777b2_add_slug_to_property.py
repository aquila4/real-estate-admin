"""Add slug column to Property safely

Revision ID: f5ce4e0777b2
Revises: 2a6428d8a0e8
Create Date: 2025-10-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5ce4e0777b2'
down_revision = '2a6428d8a0e8'
branch_labels = None
depends_on = None

def upgrade():
    # Step 1: Add 'slug' column as nullable
    op.add_column('property', sa.Column('slug', sa.String(length=250), nullable=True))

    # Step 2: Populate existing rows with a default slug using the id
    op.execute("UPDATE property SET slug = 'property-' || id")

    # Step 3: Alter the column to be NOT NULL
    op.alter_column('property', 'slug', nullable=False)

def downgrade():
    # Remove the slug column if rolling back
    op.drop_column('property', 'slug')
