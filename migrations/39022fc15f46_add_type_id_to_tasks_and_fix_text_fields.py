"""Add type_id to tasks and fix text fields

Revision ID: 39022fc15f46
Revises: 123456789012
Create Date: 2026-07-24 13:03:07.154362

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '39022fc15f46'
down_revision = '123456789012'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Получаем ID типа 'text' (мы его уже вставили вручную, он точно есть)
    res = conn.execute(text("SELECT id FROM task_types WHERE name = 'text'"))
    text_type_id = res.scalar()
    if not text_type_id:
        text_type_id = 1  # Фоллбэк
    
    print(f"Using type_id: {text_type_id}")

    # 2. Добавляем колонку type_id (если её ещё нет)
    # Для SQLite это безопасно, если колонка уже есть - будет ошибка, но мы её обработаем ниже, 
    # но лучше пусть будет чистая миграция.
    try:
        op.add_column('tasks', sa.Column('type_id', sa.Integer(), nullable=True))
    except Exception:
        # Если колонка уже есть (например, ты добавлял её вручную), просто пропускаем создание
        pass

    # 3. Заполняем существующие задачи значением по умолчанию
    conn.execute(text(f"UPDATE tasks SET type_id = {text_type_id} WHERE type_id IS NULL"))

    # 4. Делаем колонку NOT NULL (обязательно через batch_alter_table для SQLite)
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column('type_id', existing_type=sa.Integer(), nullable=False)

    # 5. Меняем тип answer на Text
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column(
            'answer', 
            existing_type=sa.String(), 
            type_=sa.Text(), 
            existing_nullable=True
        )

    # 6. Меняем тип content на Text
    with op.batch_alter_table('solves') as batch_op:
        batch_op.alter_column(
            'content', 
            existing_type=sa.String(), 
            type_=sa.Text(), 
            existing_nullable=True
        )

def downgrade():
    with op.batch_alter_table('solves') as batch_op:
        batch_op.alter_column('content', existing_type=sa.Text(), type_=sa.String(), existing_nullable=True)
    
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column('answer', existing_type=sa.Text(), type_=sa.String(), existing_nullable=True)
        batch_op.drop_column('type_id')