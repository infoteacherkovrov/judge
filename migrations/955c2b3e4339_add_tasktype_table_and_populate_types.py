"""Add TaskType table and populate types

Revision ID: 955c2b3e4339
Revises: 123456789012
Create Date: 2026-07-24 10:50:54.990687

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '955c2b3e4339'
down_revision = '123456789012'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Создаем таблицу task_types
    op.create_table(
        'task_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 2. Вставляем начальные данные (типы задач)
    conn = op.get_bind()
    
    # Вставляем типы. Если они уже есть (например, при повторном запуске), ignore error or check exists
    try:
        conn.execute(text("INSERT INTO task_types (name, description) VALUES ('text', 'Текстовый ответ (сравнение строк)')"))
        conn.execute(text("INSERT INTO task_types (name, description) VALUES ('code', 'Код (проверка через компилятор)')"))
    except Exception:
        # Игнорируем ошибку, если данные уже существуют (для идемпотентности)
        pass
    
    # Получаем ID типа 'text'. В SQLite автоинкремент обычно начинается с 1.
    # Но лучше получить явно, чтобы не гадать.
    result = conn.execute(text("SELECT id FROM task_types WHERE name = 'text'"))
    text_type_id = result.scalar()
    
    if text_type_id is None:
        # Если вдруг не нашли (редкий кейс), берем 1
        text_type_id = 1

    # 3. Добавляем колонку type_id в таблицу tasks
    # ВАЖНО: В SQLite мы НЕ используем server_default при создании, если планируем сразу обновлять старые данные.
    # Мы создаем колонку как NOT NULL, но сначала разрешаем NULL, заполняем, потом ставим NOT NULL.
    op.add_column('tasks', sa.Column('type_id', sa.Integer(), nullable=True))

    # 4. Заполняем существующие задачи значением по умолчанию (тип 'text')
    # Это заменяет необходимость в server_default и избегает проблем с ALTER COLUMN
    conn.execute(text(f"UPDATE tasks SET type_id = {text_type_id} WHERE type_id IS NULL"))

    # 5. Теперь, когда все строки имеют значение, делаем колонку NOT NULL
    # Для SQLite это делается через batch_alter_table (копирование таблицы)
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column('type_id', existing_type=sa.Integer(), nullable=False)

    # 6. Меняем тип полей answer (в Task) и content (в Solve) на Text()
    # Используем batch_alter_table, так как меняем тип данных
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column(
            'answer', 
            existing_type=sa.String(), # Или sa.VARCHAR(), Alembic сам подставит текущий тип
            type_=sa.Text(), 
            existing_nullable=True
        )

    with op.batch_alter_table('solves') as batch_op:
        batch_op.alter_column(
            'content', 
            existing_type=sa.String(), 
            type_=sa.Text(), 
            existing_nullable=True
        )
        
        # Удаляем старый индекс, если он мешает (опционально, зависит от твоей схемы)
        # batch_op.drop_index('idx_solves_user_date') 


def downgrade():
    """Откат изменений"""
    with op.batch_alter_table('solves') as batch_op:
        batch_op.alter_column('content', existing_type=sa.Text(), type_=sa.String(), existing_nullable=True)

    with op.batch_alter_table('tasks') as batch_op:
        batch_op.alter_column('answer', existing_type=sa.Text(), type_=sa.String(), existing_nullable=True)
        batch_op.drop_column('type_id')

    op.drop_table('task_types')