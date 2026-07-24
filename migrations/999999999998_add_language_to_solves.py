"""Add language column to solves table manually

Revision ID: 999999999999
Revises: 123456789012  # <-- ТВОЙ ТЕКУЩИЙ ХЕШ (из лога downgrade)
Create Date: 2023-10-27 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '999999999990'          # <-- Должно совпадать с именем файла (без .py)
down_revision = '123456789012'    # <-- ТВОЙ ТЕКУЩИЙ ХЕШ

def upgrade():
    op.add_column(
        'solves', 
        sa.Column('language', sa.String(length=20), nullable=False, server_default='python')
    )
    op.alter_column('solves', 'language', existing_type=sa.String(length=20), nullable=True)

def downgrade():
    op.drop_column('solves', 'language')
