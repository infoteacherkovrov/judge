from app import create_app, db
from models import TaskType, Task

app = create_app()

with app.app_context():
    # 1. Создаем типы, если их нет
    text_type = TaskType.query.filter_by(name='text').first()
    code_type = TaskType.query.filter_by(name='code').first()

    if not text_type:
        text_type = TaskType(name='text', description='Текстовый ответ (сравнение строк)')
        db.session.add(text_type)
        print("Создан тип: text")

    if not code_type:
        code_type = TaskType(name='code', description='Код (проверка через компилятор)')
        db.session.add(code_type)
        print("Создан тип: code")
    
    db.session.commit()

    # 2. Присваиваем типы старым задачам
    # Логика: Если в поле answer лежит короткий ответ -> считаем это текстовой задачей.
    # Если ты раньше хранил где-то флаг, используй его. 
    # Здесь я делаю эвристику: если длина answer > 50 символов ИЛИ если в названии есть слово "код", считаем это code.
    # Тебе лучше заменить эту логику на реальную проверку твоих старых данных!
    
    updated_count = 0
    for task in Task.query.all():
        # ЗАМЕНИТЬ ЭТУ ЛОГИКУ НА СВОЮ!
        # Например, если у тебя была колонка is_code_task, бери её.
        # Сейчас я ставлю по умолчанию 'text', а ты сам пройдись и поменяй нужные на 'code' в админке или вручную.
        
        if task.type_id is None:
            # Допустим, все старые задачи по умолчанию текстовые, кроме тех, где ты явно скажешь
            task.type_id = text_type.id 
            updated_count += 1
            
    db.session.commit()
    print(f"Обновлено {updated_count} задач (присвоены типы по умолчанию).")
    print("Теперь зайди в админку и вручную проставь тип 'code' для задач, где нужен компилятор.")
