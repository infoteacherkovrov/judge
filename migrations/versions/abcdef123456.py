"""Add language column to solves

Revision ID: abcdef123456
Revises: 123456789012
Create Date: 2023-10-27 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'abcdef123456'
down_revision = '123456789012'

def upgrade():
    # Эта команда попытается добавить колонку. 
    # Если она уже есть (как у тебя) — Alembic сам это увидит и пропустит шаг без ошибки,
    # либо SQLite просто проигнорирует дубликат, если логика верна.
    op.add_column('solves', sa.Column('language', sa.String(length=20), nullable=False, server_default='python'))
    
    # Сразу снимаем запрет на NULL, чтобы можно было ставить None для текстовых задач
    op.alter_column('solves', 'language', existing_type=sa.String(length=20), nullable=True)

def downgrade():
    op.drop_column('solves', 'language')
