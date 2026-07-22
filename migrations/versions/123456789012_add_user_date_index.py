"""Add user_date index for stats

Revision ID: 123456789012  # <-- Замени эти цифры на те, что ты поставил в имени файла!
Revises: abcdef123456      # <-- Сюда вставь ID предыдущей миграции (из имени последнего файла до этого)
Create Date: 2026-07-21 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
# ВАЖНО: Эти две строки должны совпадать с заголовком выше!
revision = '123456789012' 
down_revision = '4d42203b19fd'
branch_labels = None
depends_on = None


def upgrade():
    # Создаём индекс вручную
    op.create_index('idx_solves_user_date', 'solves', ['user_id', 'created_date'])


def downgrade():
    # Удаляем индекс при откате
    op.drop_index('idx_solves_user_date', table_name='solves')
