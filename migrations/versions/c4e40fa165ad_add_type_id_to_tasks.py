"""Add type_id to tasks table

Revision ID: c4e40fa165ad
Revises: abcdef123456
Create Date: 2026-07-24 17:00:41.385072
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4e40fa165ad'
down_revision = 'abcdef123456'
branch_labels = None
depends_on = None

def upgrade():
    # Добавляем колонку. server_default='1' заполнит старые задачи значением 1.
    # Это ЕДИНСТВЕННАЯ операция, которую умеет делать SQLite при ALTER TABLE.
    op.add_column('tasks', sa.Column('type_id', sa.Integer(), nullable=False, server_default='1'))
    
    # ВАЖНО: Мы НЕ делаем op.alter_column для удаления дефолта.
    # SQLite не поддерживает синтаксис ALTER COLUMN ... DROP DEFAULT.
    # Для новых задач мы будем задавать type_id явно в коде, так что дефолт нам не мешает.

def downgrade():
    # Просто удаляем колонку при откате
    op.drop_column('tasks', 'type_id')
