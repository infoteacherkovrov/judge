from flask import render_template, flash, redirect, url_for, abort,session
from app import app,db
from app.forms import CodeForm, LoginForm, RegistrationForm, AdminRoleForm, CreateTask, EditTask, DeleteForm, SolutionForm, CreateTopic, UploadImageForm
from flask_login import current_user, login_user,logout_user
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.models import User, Role, Task, Solve, Topic,TestCase
from flask_login import login_required
from flask import request,jsonify
from urllib.parse import urlsplit
from datetime import datetime, timezone,timedelta 
from app.forms import EditProfileForm

from flask_login import login_required
from sqlalchemy import select,case
from flask import abort,send_file
from functools import wraps

from sqlalchemy.orm import selectinload
from sqlalchemy import func, select
from werkzeug.utils import secure_filename
import os
import uuid
from flask import render_template
import requests
import re

import zipfile
import io
import logging



UPLOAD_FOLDER = 'app/static/images/'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # опционально: лимит 16 МБ
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Создаём логгер специально для этого файла
logger = logging.getLogger(__name__)

# Если вдруг уровень не установлен (для тестов/локально)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()  # Пока пусть пишет в консоль (для теста)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Эталонные ответы
TEST_CASES = {
    "2 3": "5",
    "10 20": "30",
    "15 -20": "-5"
}

@app.route('/check', methods=['GET', 'POST'])
def check():
    form = CodeForm()
    results = []
    COMPILER_MAP = {
        'python3': 'python-3.14',
        'cpp': 'g++-15',          # Скорее всего так, но надо проверить
        'java': 'jdk-17'             # Скорее всего так
    }

    if form.validate_on_submit():
        # 1. БЕРЁМ КОД ОТ ПОЛЬЗОВАТЕЛЯ
        # form.code — это поле из твоей формы (TextAreaField)
        # .data — это именно текст, который там написан
        user_code = form.code.data 
        
        lang = form.language.data
        num=0
        for test_name, expected_output in TEST_CASES.items():
            num+=1
            # 2. ГЕНЕРИРУЕМ ВХОДНЫЕ ДАННЫЕ ДЛЯ ЭТОГО ТЕСТА
            # Например, из "test_1_2_3" делаем "1 2 3"
            input_data = test_name
            
            # --- ЗДЕСЬ НАЧИНАЕТСЯ РЕАЛЬНЫЙ ЗАПРОС К API ---
           
            
            api_url = "https://api.onlinecompiler.io/api/run-code-sync/"
            compiler_name = COMPILER_MAP.get(form.language.data, 'python-3.14')

            payload = {
                "compiler": compiler_name,  # Фиксированный компилятор
                "code": user_code,         # <-- ВОТ ОТКУДА БЕРЁТСЯ CODE
                "input": input_data        # <-- ВОТ ОТКУДА БЕРЁТСЯ INPUT
            }
              
            headers = {
                "Authorization": f"{app.config['API_KEY']}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                else:
                    # Если API вернул ошибку (401, 429 и т.д.)
                    data = {"status": "error", "output": "", "error": f"API Error: {response.status_code}"}
                    
            except Exception as e:
                # Если отвалился интернет или таймаут
                data = {"status": "error", "output": "", "error": str(e)}
            # ------------------------------------------------

            # Дальше твоя старая логика сравнения:
            got_output = (data.get('output') or '').strip()
            status = "OK" if data.get('status') == 'success' and got_output == expected_output else "FAIL"
            
            results.append({
                "test": num,
                "input": input_data,
                "expected": expected_output,
                "got": got_output or 'Нет вывода',
                "error": data.get('error'),
                "status": status
            })

    return render_template('check.html', form=form, results=results)

          
@app.route('/summernote_upload', methods=['POST'])
def summernote_upload():
    logger.info("🚀 Загрузка началась (CSRF временно отключен)")
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        upload_folder = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(upload_folder, exist_ok=True)
        
        file.save(os.path.join(upload_folder, unique_filename))
        image_url = f'/static/images/{unique_filename}'
        
        logger.info(f"✅ УСПЕХ: {image_url}")
        return jsonify({'url': image_url})
    except Exception as e:
        logger.info(f"❌ Ошибка: {e}")
        return jsonify({'error': str(e)}), 500
    
    
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Проверяем, существует ли роль и равна ли она 'admin'
        if not current_user.role or current_user.role.rolename != 'admin':
            return abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@app.route('/index')
@login_required
def index():
    
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template("index.html", title='Home Page', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    roles = Role.query.all()
    form.role_id.choices = [(role.id, role.rolename) for role in roles]
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role_id=1) #role_id=form.role_id.data
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    # 1. Находим пользователя
    stmt_user = select(User).where(User.username == username)
    user = db.first_or_404(stmt_user)

    # --- Твоя старая логика (Уникальные задачи) ---
    stmt2 = (
        select(func.count(func.distinct(Solve.task_id)))
        .join(User, Solve.user_id == User.id)
        .where(User.username == username)
        .where(Solve.accept == True)
    )
    unique_solved_count = db.session.scalar(stmt2) or 0

    # --- Твоя старая логика (Пагинация решений) ---
    stmt = (
        select(Solve)
        .join(User, Solve.user_id == User.id)
        .where(User.username == username)
        .order_by(Solve.created_date.desc())
        .options(
            selectinload(Solve.solver),
            selectinload(Solve.task)
        )
    )

    status_filter = request.args.get('status')
    page = request.args.get('page', 1, type=int)

    if status_filter == 'accepted':
        stmt = stmt.where(Solve.accept == True)
    elif status_filter == 'rejected':
        stmt = stmt.where(Solve.accept == False)

    pagination = db.paginate(stmt, page=page, per_page=10, error_out=False)

    count_accepted_stmt = (
        select(func.count()).select_from(Solve).join(User, Solve.user_id == User.id)
        .where(Solve.accept == True, User.username == username)
    )
    count_rejected_stmt = (
        select(func.count()).select_from(Solve).join(User, Solve.user_id == User.id)
        .where(Solve.accept == False, User.username == username)
    )

    total_accepted = db.session.scalar(count_accepted_stmt) or 0
    total_rejected = db.session.scalar(count_rejected_stmt) or 0

    next_url = url_for('user', username=username, page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('user', username=username, page=pagination.prev_num) if pagination.has_prev else None
    
    is_admin = getattr(current_user, 'is_admin', False)
    
    # Заглушка для постов, если их нет в цикле (чтобы шаблон не упал)
    posts = [] 
    # Если у тебя где-то выше в старом коде была логика загрузки posts - оставь её. 
    # Если нет - эта заглушка защитит от ошибки в шаблоне.

    # --- НОВАЯ ЛОГИКА: Статистика для графика ---
    period = request.args.get('period', 'all')
    end_date = datetime.now(timezone.utc)
    start_date = None

    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)

    query = db.session.query(Solve).filter(Solve.user_id == user.id)
    if start_date:
        query = query.filter(Solve.created_date >= start_date)

    all_solves = query.all()

    chart_overall = {
        "total_attempts": 0,
        "total_correct": 0,
        "unique_solved": 0,
        "success_rate_percent": 0.0,
        "mastery_rate_percent": 0.0
    }
    chart_daily = []

    if not all_solves:
        pass
    else:
        total_attempts = len(all_solves)
        total_accepted = sum(1 for s in all_solves if s.accept)
        
        # Уникальные задачи, которые были РЕШЕНЫ
        unique_solved_tasks = len({s.task_id for s in all_solves if s.accept})
        
        # Все уникальные задачи, к которым пользователь прикасался (и верно, и неверно)
        touched_tasks = len({s.task_id for s in all_solves})
        
        # 1. Точность: сколько попыток были успешными
        success_rate = round(100.0 * total_accepted / total_attempts, 1) if total_attempts > 0 else 0.0
        
        # 2. Освоение: сколько уникальных задач закрыто из тех, что пробовал
        mastery_rate = round(100.0 * unique_solved_tasks / touched_tasks, 1) if touched_tasks > 0 else 0.0

        chart_overall = {
            "total_attempts": total_attempts,
            "total_correct": total_accepted,
            "unique_solved": unique_solved_tasks,
            "success_rate_percent": success_rate,
            "mastery_rate_percent": mastery_rate
        }

        # Группировка по дням для графика
        daily_stats = {}
        for solve in all_solves:
            day_key = solve.created_date.date()
            
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    "unique_correct_ids": set(),   # ID решённых задач
                    "wrong_attempts": 0             # Количество ошибок
                }
            
            if solve.accept:
                daily_stats[day_key]["unique_correct_ids"].add(solve.task_id)
            else:
                daily_stats[day_key]["wrong_attempts"] += 1

        sorted_days = sorted(daily_stats.items(), key=lambda x: x[0])

        chart_daily = [
            {
                "day": day.isoformat(),
                "unique_solved": len(data["unique_correct_ids"]),
                "wrong_attempts": data["wrong_attempts"]
            }
            for day, data in sorted_days
        ]

    # Передаем в шаблон не только данные, но и текущий выбранный период
    return render_template(
        'user.html',
        user=user,
        posts=posts,
        pagination=pagination,
        is_admin=is_admin,
        current_status=status_filter,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        solved_tasks=unique_solved_count,
        next_url=next_url,
        prev_url=prev_url,
        chart_daily=chart_daily,
        chart_overall=chart_overall,
        current_period=period
    )


# ==========================================
# 2. НОВЫЙ РОУТ (API для графика)
# Возвращает JSON данные для Chart.js
# ==========================================
@app.route('/api/user/stats', methods=['GET'])
@login_required  # Защита API тоже нужна!
def user_stats():
    user_id = request.args.get('user_id', type=int)
    days = request.args.get('days', default=30, type=int)

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    # Проверка прав: можно смотреть статистику только своего профиля или админу
    try:
        if current_user.id != user_id and not getattr(current_user, 'is_admin', False):
            return jsonify({"error": "Forbidden"}), 403
    except AttributeError:
        pass  # На случай тестов без логина

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    with db.session.begin():
        # --- Общая статистика ---
        overall_row = (
            db.session.query(
                func.count(Solve.id).label("total_attempts"),
                func.sum(sa.cast(Solve.accept, db.Integer)).label("total_correct"),
            )
            .filter(Solve.user_id == user_id)
            .filter(Solve.created_date.between(start_date, end_date))
            .one_or_none()
        )

        if not overall_row:
            overall = {"total_attempts": 0, "total_correct": 0, "success_rate_percent": 0.0}
        else:
            total_attempts = overall_row.total_attempts or 0
            total_correct = overall_row.total_correct or 0
            success_rate = (
                round(100.0 * total_correct / total_attempts, 1)
                if total_attempts > 0 else 0.0
            )
            overall = {
                "total_attempts": total_attempts,
                "total_correct": total_correct,
                "success_rate_percent": success_rate,
            }

        # --- Ежедневная статистика (для графика) ---
        rows = (
            db.session.query(
                func.date(Solve.created_date).label("day"),
                func.count(Solve.id).label("total_solved"),
                func.sum(sa.cast(Solve.accept, db.Integer)).label("correct_solved"),
            )
            .filter(Solve.user_id == user_id)
            .filter(Solve.created_date.between(start_date, end_date))
            .group_by(func.date(Solve.created_date))
            .order_by(func.date(Solve.created_date))
            .all()
        )

        daily = [
            {
                "day": row.day.isoformat(),
                "total_solved": row.total_solved or 0,
                "correct_solved": row.correct_solved or 0,
            }
            for row in rows
        ]

    return jsonify({
        "daily": daily,
        "overall": overall,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    })
    
@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)
    
@app.route('/view_users', methods=['GET'])
@login_required
def view_users():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
    users = db.session.scalars(sa.select(User)).all()
    
    # 1. Подзапрос: считаем только успешные решения по каждому user_id
    subq = (
        select(
            Solve.user_id,
            func.count(func.distinct(Solve.task_id)).label('solved_count')
        )
        .where(Solve.accept == True)
        .group_by(Solve.user_id)
        .subquery()  # Делаем его виртуальной таблицей
    )

    # 2. Основной запрос: берем всех пользователей и приклеиваем статистику
    stmt = (
        select(
            User.id,
            User.username,
            User.email,
            User.last_seen,
            User.about_me,
            # Если статистики нет (новичок), coalesce вернет 0 вместо NULL
            func.coalesce(subq.c.solved_count, 0).label('solved_count')
        )
        .outerjoin(subq, User.id == subq.c.user_id)  # LEFT JOIN
        # 🔥 ВОТ ЗДЕСЬ БЫЛА ОШИБКА: НЕЛЬЗЯ использовать func.col('name')
        # ПРАВИЛЬНО: просто передаем строку 'solved_count' или subq.c.solved_count
        .order_by(subq.c.solved_count.desc(), User.username.asc())
    )

    results = db.session.execute(stmt).all()

    rating_data = [
        {'id': r.id, 'username': r.username, 'solved_count': r.solved_count,'email':r.email,'last_seen':r.last_seen,'about_me':r.about_me}
        for r in results
    ]

          
    return render_template('view_users.html', users=users,rating=rating_data)


'''
@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    # Получаем всех пользователей и все роли (для выпадающих списков)
    users = User.query.all()
    roles = Role.query.all()

    # Создаем одну форму, но мы будем заполнять её choices динамически для каждой строки в шаблоне
    # Или лучше: создадим форму для каждого пользователя в шаблоне. 
    # Самый чистый вариант — передать roles в шаблон и строить формы там.
    
    # Но чтобы форма валидировалась, нам нужна одна форма на POST-запрос.
    form = AdminRoleForm()
    
    # Заполняем варианты выбора ролей для формы (они будут одинаковыми для всех)
    form.new_role_id.choices = [(r.id, r.rolename) for r in roles]

    if form.validate_on_submit():
        user = User.query.get(form.user_id.data)
        if user:
            user.role_id = form.new_role_id.data
            db.session.commit()
            flash(f'Роль пользователя {user.username} изменена на {Role.query.get(form.new_role_id.data).rolename}', 'success')
        else:
            flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_users'))

    return render_template('admin_users.html', users=users, roles=roles, form=form)
'''

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
    
    users = User.query.all()
    roles = Role.query.all()
    form = AdminRoleForm()
    
    # Заполняем choices для валидации (обязательно!)
    form.new_role_id.choices = [(r.id, r.rolename) for r in roles]

    if form.validate_on_submit():
        logger.info("--- ОТЛАДКА: Форма прошла валидацию ---")
        logger.info(f"Получен user_id: {form.user_id.data} (тип: {type(form.user_id.data)})")
        logger.info(f"Получен new_role_id: {form.new_role_id.data} (тип: {type(form.new_role_id.data)})")

        user = User.query.get(form.user_id.data)
        
        if user:
            old_role_name = user.role.rolename if user.role else "None"
            user.role_id = form.new_role_id.data
            db.session.commit()
            logger.info(f"✅ УСПЕХ: Роль пользователя {user.username} изменена с '{old_role_name}' на '{Role.query.get(form.new_role_id.data).rolename}'")
            flash(f'Роль пользователя {user.username} успешно изменена', 'success')
        else:
            logger.info("❌ ОШИБКА: Пользователь не найден!")
            flash('Пользователь не найден', 'danger')
            
        return redirect(url_for('admin_users'))
    else:
        # Если валидация НЕ прошла, выводим ошибки в консоль
        if request.method == 'POST':
            logger.info("--- ОТЛАДКА: Валидация НЕ пройдена ---")
            logger.info(f"Ошибки формы: {form.errors}")
            # Это критически важно: если тут есть ошибки, код до commit не доходит!

    return render_template('admin_users.html', users=users, roles=roles, form=form)


def normalize_summernote_images(html_content):
    if not html_content:
        return html_content

    logger.info(f"🛠️ Функция вызвана. Длина контента: {len(html_content)}")

    # Ищем src, где внутри есть static/images. 
    # Этот паттерн ловит и http://..., и /static/..., и static/...
    # (.+?) захватывает всё до static/, а (static/[^"\']+) захватывает сам путь к файлу
    pattern = r'src=["\'](.+?)(static/[^"\']+)["\']'
    
    def replacer(match):
        prefix = match.group(1)      # Всё, что было ДО static/ (например, "http://127.0.0.1:5000/")
        path_part = match.group(2)  # Сам путь: "static/images/23.jpg"
        
        logger.info(f"🔍 Нашли картинку: префикс='{prefix}', путь='{path_part}'")

        # Очищаем путь, убираем "static/" в начале, чтобы получить просто "images/23.jpg"
        filename = path_part.replace('static/', '')
        
        if not filename:
            logger.info("❌ Ошибка: имя файла пустое!")
            return match.group(0)

        try:
            # Генерируем ПРАВИЛЬНЫЙ путь через url_for. 
            # Flask сам решит, как правильно отдать файл (даже если ты потом поменяешь домен)
            correct_url = url_for('static', filename=filename)
            logger.info(f"✅ Превратили '{prefix}{path_part}' в '{correct_url}'")
            return f'src="{correct_url}"'
        except Exception as e:
            logger.info(f"💥 Ошибка генерации URL: {e}")
            return match.group(0)

    new_html = re.sub(pattern, replacer, html_content)
    
    if new_html == html_content:
        logger.info("📭 Ничего не найдено. Возможно, картинки нет или формат другой.")
    else:
        logger.info("✨ Замена выполнена успешно!")
        
    return new_html

@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
    
    # Если пользователь нажал кнопку "Добавить тест", увеличиваем количество полей
    add_test = request.args.get('add_test', type=int)
    if add_test:
        # Создаем форму с большим количеством записей
        form = CreateTask()
        # Хак: принудительно увеличиваем min_entries через внутренний механизм или просто создаем форму заново
        # Но проще: в классе формы сделать динамическое min_entries, но FlaskForm не любит менять его на лету.
        # Поэтому сделаем так: передадим extra_fields в конструктор, если нужно.
        pass 
    
    form = CreateTask()
    if form.validate_on_submit():
        
        logger.info("--- ОТЛАДКА: Форма прошла валидацию ---")
        logger.info(f"Получен title: {form.title.data} (тип: {type(form.title.data)})")
        logger.info(f"Получен content: {form.content.data} (тип: {type(form.content.data)})")
       
       
        #newtask = Task(title=form.title.data, content=form.content.data, answer=form.answer.data)
        #newtask.created_date = datetime.now(timezone.utc)
        #newtask.user_id=current_user.id
        newtask = Task(
            title=form.title.data,
            content=form.content.data,
            answer=form.answer.data,
            type_id=form.type_id.data,          # <-- ЭТА СТРОКА КРИТИЧЕСКИ ВАЖНА!
            created_date=datetime.now(timezone.utc),
            user_id=current_user.id
        )
        db.session.add(newtask)
        db.session.flush() # Получаем ID задачи сразу

        current_order = 1  # Наш собственный счётчик для идеальной нумерации (1, 2, 3...)

        for test_data in form.tests.data:
            # 1. Достаём данные. .get() вернёт None, если ключа нет.
            raw_input = test_data.get('input_data')
            raw_output = test_data.get('expected_output')

            # 2. Приводим к строке и убираем лишние пробелы/переносы по краям
            input_val = str(raw_input).strip() if raw_input is not None else ''
            output_val = str(raw_output).strip() if raw_output is not None else ''

            # 🔥 ГЛАВНАЯ ЗАЩИТА: Если input_val пустой ('', ' ', '\n', None) — пропускаем тест!
            if not input_val:
                continue

            # 3. Только если тест валидный — создаём объект
            new_test = TestCase(
                task_id=newtask.id,
                order_index=current_order,      # Плотная нумерация: 1, 2, 3...
                input_data=input_val,
                expected_output=output_val,
                is_sample=bool(test_data.get('is_sample', False))
            )
            db.session.add(new_test)
            current_order += 1

        db.session.commit()
        flash('Задача и тесты созданы!', 'success')
        return redirect(url_for('tasks_list'))

    return render_template('create_task.html', title='Create task', form=form)
'''
        
        selected_topic = form.topic.data
        if selected_topic:
            newtask.topic_id = selected_topic.id
            # Также можно присвоить саму связь, SQLAlchemy сам поймет:
            # newtask.topic = selected_topic 
        else:
            # Если тема не выбрана, оставляем None (так как у нас nullable=True)
            newtask.topic_id = None
        
        db.session.add(newtask)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('view_tasks'))
   
    return render_template('create_task.html', title='Create task',
                           form=form)'''
    
@app.route('/create_topic', methods=['GET', 'POST'])
@admin_required
def create_topic():
    form = CreateTopic()
    if form.validate_on_submit():
        
        logger.info("--- ОТЛАДКА: Форма прошла валидацию ---")
        logger.info(f"Получен topic: {form.topic.data} (тип: {type(form.topic.data)})")
               
        newtopic = Topic(topic=form.topic.data)
        db.session.add(newtopic)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('tasks_list'))
    '''elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me'''
    return render_template('create_topic.html', title='Create topic', form=form)

@app.route('/view_tasks', methods=['GET'])
@login_required
def view_tasks():
    
    
    # --- 1. Сначала узнаём, какие задачи УЖЕ РЕШЕНЫ ТЕКУЩИМ ПОЛЬЗОВАТЕЛЕМ ---
    # Делаем один запрос: все ID задач, где пользователь получил accept=True
    stmt = (
    select(Solve.task_id)
    .where(Solve.user_id == current_user.id)
    .where(Solve.accept == True)
    .distinct()
    )

    result = db.session.execute(stmt)
    solved_task_ids = {row for row in result.scalars()}  # Или .all(), если так привычнее
    
    # --- 2. Тепрь узнаём, какие задачи РЕШАЛ ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ---
        # Делаем один запрос: все ID задач, где пользователь получил accept=True
    stmt = (
        select(Solve.task_id)
        .where(Solve.user_id == current_user.id)
        .distinct()
        )
    
    result = db.session.execute(stmt)
    sended_task_ids = {row for row in result.scalars()}  # Или .all(), если так привычнее
         
        
    
    topics = Topic.query.all()
    selected_topic_id = request.args.get('topic_id', type=int)
    query = Task.query.options(so.joinedload(Task.topic))
    if selected_topic_id:
         query = query.filter(Task.topic_id == selected_topic_id)
   
    query = query.order_by(Task.created_date.desc())
    page = request.args.get('page', 1, type=int)  
    
    
      
   
    #per_page = request.args.get('per_page', 10, type=int)
  
    pagination = db.paginate(query,page=page, per_page=10, error_out=False)
    
    next_url = url_for('view_tasks', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('view_tasks', page=pagination.prev_num) if pagination.has_prev else None
    
    form = DeleteForm()
    return render_template('view_tasks.html', sended_task_ids=sended_task_ids, solved_task_ids=solved_task_ids, form=form,is_admin=is_admin(), next_url=next_url,
                           prev_url=prev_url,pagination=pagination, topics=topics, selected_topic_id=selected_topic_id, max_per_page=50)


@app.route('/tasks_list', methods=['GET'])
@login_required
def tasks_list():
    
    
    # --- 1. Сначала узнаём, какие задачи УЖЕ РЕШЕНЫ ТЕКУЩИМ ПОЛЬЗОВАТЕЛЕМ ---
    # Делаем один запрос: все ID задач, где пользователь получил accept=True
    stmt = (
    select(Solve.task_id)
    .where(Solve.user_id == current_user.id)
    .where(Solve.accept == True)
    .distinct()
    )

    result = db.session.execute(stmt)
    solved_task_ids = {row for row in result.scalars()}  # Или .all(), если так привычнее
    
    # --- 2. Тепрь узнаём, какие задачи РЕШАЛ ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ---
        # Делаем один запрос: все ID задач, где пользователь получил accept=True
    stmt = (
        select(Solve.task_id)
        .where(Solve.user_id == current_user.id)
        .distinct()
        )
    
    result = db.session.execute(stmt)
    sended_task_ids = {row for row in result.scalars()}  # Или .all(), если так привычнее
    
    topics = Topic.query.all()
    selected_topic_id = request.args.get('topic_id', type=int)
    query = Task.query.options(so.joinedload(Task.topic))
    if selected_topic_id:
        query = query.filter(Task.topic_id == selected_topic_id)
       
    query = query.order_by(Task.created_date.desc())
    page = request.args.get('page', 1, type=int)         
    # Фильтрация по теме (если выбрана)
    
    pagination = db.paginate(query, page=page, per_page=10, error_out=False)

    next_url = url_for('tasks_list', page=pagination.next_num, topic_id=selected_topic_id) if pagination.has_next else None
    prev_url = url_for('tasks_list', page=pagination.prev_num, topic_id=selected_topic_id) if pagination.has_prev else None

    topics = Topic.query.all()
    form = DeleteForm()
    
    tasks = pagination.items
    if not tasks:
        return render_template(
                'tasks_list.html',
                sended_task_ids=sended_task_ids,
                solved_task_ids=solved_task_ids,
                form=form,
                is_admin=is_admin(),
                next_url=next_url,
                prev_url=prev_url,
                pagination=pagination,
                tasks=[],
                topics=topics,
                selected_topic_id=selected_topic_id,
                max_per_page=50)

    # Получаем ID задач на текущей странице
    task_ids = [t.id for t in tasks]

    # 2. ОДНИМ запросом получаем статистику для этих 10 задач
    # Нам нужно: task_id, count(distinct user_id) as attempts, count(distinct user_id where accept=True) as solved
    stats_stmt = (
        select(
            Solve.task_id,
            func.count(Solve.user_id.distinct()).label('attempts'),
            func.sum(case((Solve.accept == True, 1), else_=0)).label('solved_count_logic') 
            # Выше sum(case) считает количество посылок, но нам нужно количество УНИКАЛЬНЫХ пользователей, решивших задачу.
            # Поэтому лучше сделать два отдельных подзапроса или хитрый count.
        )
        .where(Solve.task_id.in_(task_ids))
        .group_by(Solve.task_id)
    )
    
    # Исправленная логика для solved: нам нужно количество уникальных user_id, у которых accept=True
    # Делаем это через отдельный запрос для ясности, либо комбинируем. 
    # Давай сделаем максимально просто и эффективно: два отдельных запроса к БД для этой пачки ID.
    
    # Запрос 1: Кто пытался (уникальные user_id)
    attempts_data = db.session.execute(
        select(Solve.task_id, func.count(Solve.user_id.distinct()).label('count'))
        .where(Solve.task_id.in_(task_ids))
        .group_by(Solve.task_id)
    ).all()
    
    # Запрос 2: Кто решил (уникальные user_id с accept=True)
    solved_data = db.session.execute(
        select(Solve.task_id, func.count(Solve.user_id.distinct()).label('count'))
        .where(Solve.task_id.in_(task_ids))
        .where(Solve.accept == True)
        .group_by(Solve.task_id)
    ).all()

    # Превращаем результаты в словари для быстрого доступа: {task_id: count}
    attempts_map = {row.task_id: row.count for row in attempts_data}
    solved_map = {row.task_id: row.count for row in solved_data}

    # Добавляем статистику прямо в объекты задач (это безопасно, так как это временный контекст шаблона)
    for task in tasks:
        task.unique_attempts = attempts_map.get(task.id, 0)
        task.unique_solved = solved_map.get(task.id, 0)





    return render_template(
        'tasks_list.html',
        sended_task_ids=sended_task_ids,
        solved_task_ids=solved_task_ids,
        form=form,
        is_admin=is_admin(),
        next_url=next_url,
        prev_url=prev_url,
        pagination=pagination,
        tasks=tasks,
        topics=topics,
        selected_topic_id=selected_topic_id,
        max_per_page=50
    )

@app.route('/task2/<id>', methods=['GET','POST'])
@login_required
def task2(id):
    task2 = db.session.get(Task, id)
    if not task2:
        return abort(404)
    form = SolutionForm()
    if form.validate_on_submit():
        
        
        newans = Solve(content=form.answer.data)
        
        logger.info("--- ОТЛАДКА: Форма прошла валидацию ---")
        
        if task2.task_type.name == 'code':
            # Если задача на код -> берем то, что выбрал пользователь
            newans.language = form.language.data 
        else:
            # Если текстовая задача -> ставим None (пусто) или метку 'text'
            newans.language = None  # Или 'text', если колонка String не принимает NULL
        
        newans.created_date = datetime.now(timezone.utc)
        newans.user_id=current_user.id
        newans.task_id=id
        
        
        curr = db.session.get(Task, id)
        logger.info(f"Получен Answer: {curr.answer} (тип: {type(curr.answer)})")
        logger.info(f"Получен form.answer.data: {form.answer.data} (тип: {type(form.answer.data)})")
        newans.accept=(curr.answer==form.answer.data)
        
        
        db.session.add(newans)
        db.session.commit()
        flash('Your changes have been saved.')
    if is_admin():
        stmt = (
            select(Solve)
            .where(Solve.task_id == id)
            .order_by(Solve.created_date.desc())
            .options(
                selectinload(Solve.solver),  # Подгружаем пользователя (поле solver)
                selectinload(Solve.task)    # Подгружаем задачу (на всякий случай)
            )
        )
    else:
        stmt = (
            select(Solve)
            .where(Solve.task_id == id)
            .where(Solve.user_id == current_user.id)
            .order_by(Solve.created_date.desc())
            .options(
                selectinload(Solve.solver),  # Подгружаем пользователя (поле solver)
                selectinload(Solve.task)    # Подгружаем задачу (на всякий случай)
            )
        )
        
    
    solution = db.session.scalars(stmt).all()
    
       
    return render_template('task2.html', task=task2,is_admin=is_admin, form=form, solution=solution)

@app.route('/task/<int:id>', methods=['GET', 'POST'])
@login_required
def task(id):
    task2 = db.session.get(Task, id)
    if not task2:
        return abort(404)
    
    # Получаем все тесты
    all_tests = TestCase.query.filter_by(task_id=task2.id).order_by(TestCase.order_index).all()
    public_samples = [t for t in all_tests if t.is_sample]
    hidden_count = len(all_tests) - len(public_samples)
    is_code_task = (task2.task_type.name == 'code')
    
    form = SolutionForm()
          
    results = []
    is_checked = False
    final_status = "pending"
    
    
    # 👇 ПЕРЕМЕННЫЕ ДЛЯ ПРЕДЗАПОЛНЕНИЯ ФОРМЫ
    last_code = ""
    last_lang = ""

    if form.validate_on_submit():
        user_code = form.answer.data
        lang = form.language.data
        last_code = user_code  # Сохраняем, чтобы потом показать
        last_lang = lang      # Сохраняем язык
    
           
        if is_code_task:
            tests = task2.tests 
            if not tests:
                flash('У этой задачи нет тестов для проверки!', 'warning')
                # Сохраняем решение даже без тестов
                newans = Solve(content=user_code, language=lang, created_date=datetime.now(timezone.utc), 
                                user_id=current_user.id, task_id=id, accept=False)
                db.session.add(newans)
                db.session.commit()
                # Редирект на ту же страницу, чтобы сбросить форму и избежать повторной отправки
                return redirect(url_for('task', id=id))

            COMPILER_MAP = {'python3': 'python-3.14', 'cpp': 'g++-15', 'java': 'jdk-17'}
            compiler_name = COMPILER_MAP.get(lang, 'python-3.14')
            api_url = "https://api.onlinecompiler.io/api/run-code-sync/"
            headers = {"Authorization": f"{app.config['API_KEY']}", "Content-Type": "application/json"}

            all_passed = True
            
            for test in tests:
                try:
                    payload = {"compiler": compiler_name, "code": user_code, "input": test.input_data}
                    resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                    else:
                        data = {"status": "error", "output": "", "error": f"API Error: {resp.status_code}"}
                    
                    got_output = (data.get('output') or '').strip()
                    expected = test.expected_output.strip()
                    api_status = data.get('status')
                    
                    test_result = {
                        "test_num": test.order_index,
                        "input": test.input_data,
                        "expected": expected,
                        "got": got_output,
                        "error": data.get('error'),
                        "status": "",
                        "is_sample": test.is_sample
                    }

                    if api_status == 'success' and got_output == expected:
                        test_result["status"] = "OK"
                    elif api_status == 'error':
                        test_result["status"] = "Runtime Error"
                        all_passed = False
                    else:
                        test_result["status"] = "Wrong Answer"
                        all_passed = False
                        
                    results.append(test_result)

                except requests.exceptions.Timeout:
                    results.append({"test_num": test.order_index, "input": test.input_data, 
                                     "status": "System Error", "message": "Превышено время ожидания"})
                    all_passed = False
                except Exception as e:
                    results.append({"test_num": test.order_index, "input": test.input_data, 
                                    "status": "System Error", "error": str(e)})
                    all_passed = False
            
            final_status = "accepted" if all_passed else "rejected"
            is_checked = True

        else:
            # Текстовая задача
            is_accepted = (task2.answer.strip() == user_code.strip())
            results = [{"status": "OK" if is_accepted else "Wrong", "message": "Текстовая проверка"}]
            is_checked = True
            final_status = "accepted" if is_accepted else "rejected"
        
        final_language = lang if task2.task_type.name == 'code' else 'text'

        # --- СОХРАНЕНИЕ В БАЗУ ---
        newans = Solve(
            content=user_code,
            language=final_language,
            created_date=datetime.now(timezone.utc),
            user_id=current_user.id,
            task_id=id,
            accept=(final_status == "accepted")
        )
        
        
        
        db.session.add(newans)
        db.session.commit()
        
        flash(f'Решение проверено. Статус: {final_status.upper()}', 'info')
        
       

        # ВАЖНО: Сохраняем результаты во временную сессию ПЕРЕД редиректом
        session['last_results'] = results
        session['last_final_status'] = final_status
        session['last_is_checked'] = True
        
        # ДЕЛАЕМ РЕДИРЕКТ, чтобы при обновлении страницы форма не отправлялась снова
        #return redirect(url_for('task', id=id)) 

    
    # --- ЛОГИКА ОТОБРАЖЕНИЯ (GET) ---
    # Если мы попали сюда после редиректа, достаем данные из сессии
    if session.get('last_results'):
        results = session['last_results']
        final_status = session.get('last_final_status', "pending")
        is_checked = session.get('last_is_checked', False)
        
        # Очищаем сессию, чтобы данные показались только один раз
        session.pop('last_results', None)
        session.pop('last_final_status', None)
        session.pop('last_is_checked', None)
    else:
        # Если просто зашли на страницу (первый раз), результатов нет
        results = []
        is_checked = False
        final_status = "pending"

    # Выборка истории решений
   
    if is_admin():
        stmt = select(Solve).where(Solve.task_id == id).order_by(Solve.created_date.desc()).options(selectinload(Solve.solver))
    else:
        stmt = select(Solve).where(Solve.task_id == id).where(Solve.user_id == current_user.id).order_by(Solve.created_date.desc()).options(selectinload(Solve.solver))
    
    solution = db.session.scalars(stmt).all()

   
    
        
    return render_template(
        'task.html', 
        task=task2, 
        form=form, 
        solution=solution, 
        results=results, 
        is_checked=is_checked,
        final_status=final_status,
        is_admin=is_admin(),  # Передаем результат функции, а не саму функцию!
        public_samples=public_samples, 
        hidden_count=hidden_count,
        all_tests=all_tests,
        is_code_task=is_code_task,
        
    )
    
    
@app.route('/task/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    stmt = sa.select(Task).where(Task.id == id)
    result = db.session.execute(stmt)
    edittask = result.scalars().first()
    
    if not edittask:
        abort(404)
    if edittask.user_id != current_user.id:
        abort(403)
    
    form = EditTask(obj=edittask)
    
    if request.method == 'POST' and form.validate_on_submit():
       
        # --- Дальше твой обычный код ---
        # --- ОБНОВЛЕНИЕ ОСНОВНЫХ ПОЛЕЙ ---
        edittask.title = form.title.data
        edittask.content = form.content.data
        
        # 👇 ВАЖНО: Обновляем тип задачи через ID
        # В форме поле называется type_id, в модели задачи колонка task_type_id
        edittask.task_type_id = form.type_id.data
        
        # 👇 Если есть поле ответа, раскомментируй:
        edittask.answer = form.answer.data

        # 🔥 ГЛАВНАЯ ЛОГИКА: Сначала удаляем старые тесты
        # Это предотвращает ошибку "Instance has been deleted"
        TestCase.query.filter_by(task_id=edittask.id).delete()

        current_order = 1

        for test_data in form.tests.data:
            raw_input = test_data.get('input_data')
            
            input_val = str(raw_input).strip() if raw_input is not None else ''
            
            # Пропускаем пустые
            if not input_val:
                continue

            new_test = TestCase(
                task_id=edittask.id,
                order_index=current_order,
                input_data=input_val,
                expected_output=str(test_data.get('expected_output', '')).strip(),
                is_sample=bool(test_data.get('is_sample', False))
            )
            db.session.add(new_test)
            current_order += 1

        db.session.commit()
        return redirect(url_for('task', id=edittask.id))
    
    return render_template('edit_task.html', form=form, task=edittask)

@app.route('/task/<int:id>/delete', methods=['POST'])
@login_required
def delete_task(id):
    
    
        
    stmt = select(Task).where(Task.id == id)
    result = db.session.execute(stmt)
    deltask = result.scalars().first()

    if not task:
        flash('Задача не найдена', 'warning')
        return redirect(url_for('tasks_list'))
    if not is_admin():
        abort(403)
    
        
    try:
        db.session.delete(deltask)
        db.session.commit()
        flash('Задача успешно удалена', 'success')
    except Exception as e:
        db.session.rollback()
        # Логирование ошибки лучше делать через current_app.logger
        flash('Ошибка при удалении задачи', 'danger')

    return redirect(url_for('tasks_list'))    
    
     
    if is_admin() and deltask:  # Проверяем, что запись существует
        db.session.delete(deltask)  # Помечаем объект для удаления
        db.session.commit()  # Сохраняем изменения в базе
    tasks = db.session.scalars(sa.select(Task)).all()
    return render_template('view_tasks.html', tasks=tasks)

@app.route('/task/<int:id>/solution', methods=['GET','POST'])
@login_required
def solution_task(id):
    if not current_user.is_authenticated:
        return redirect(url_for('index'))
    soltn = db.session.scalars(sa.select(Solve).where(Solve.task_id == id)).all()
    
    return render_template('solution.html', solution_task=soltn, name=id)

@app.route('/solutions', methods=['GET'])
@admin_required
def solutions():
    from sqlalchemy.orm import selectinload
    if not current_user.is_authenticated:
        return redirect(url_for('index'))
    '''
    soltn = db.session.scalars(sa.select(Solve)).all()
    
    return render_template('solutions.html', solutions=soltn)
    
    '''
    stmt = (
        sa.select(Solve)
        .options(
            selectinload(Solve.solver),   # Подгружаем пользователя (поле solver)
            selectinload(Solve.task)     # Подгружаем задачу (поле task)
            
        )
        .order_by(Solve.created_date.desc())
    )
    solutions = db.session.scalars(stmt).all()
    
    return render_template('solutions.html', solutions=solutions,is_admin=is_admin)

@app.route('/task/<int:id>/export', methods=['GET'])
@admin_required
def export_solutions(id):
    # 1. Проверка прав (только админ!)
    if not is_admin():
        return abort(403)

    task = db.session.get(Task, id)
    if not task:
        return abort(404)

    # 2. Получаем даты из запроса (?start=2024-01-01&end=2024-01-31)
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    start_date = None
    end_date = None
    
    accepted_only = request.args.get('accepted') is not None
    rejected_only = request.args.get('rejected') is not None

    if start_str:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
    if end_str:
        # Конец дня, чтобы захватить все решения до 23:59:59
        end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    # 3. Формируем запрос с фильтром
    stmt = select(Solve).where(Solve.task_id == id)
    
    if start_date:
        stmt = stmt.where(Solve.created_date >= start_date)
    if end_date:
        stmt = stmt.where(Solve.created_date <= end_date)
    
    # Логика фильтрации по статусу
    # Если выбраны ОБА (или ни один не снят) -> показываем всё
    # Если выбран только Accepted -> фильтруем
    # Если выбран только Rejected -> фильтруем
    
    if accepted_only and not rejected_only:
        stmt = stmt.where(Solve.accept == True)
    elif rejected_only and not accepted_only:
        stmt = stmt.where(Solve.accept == False)
    # Если оба выбраны (checked) или оба сняты - оставляем без фильтрации по статусу
        
    solutions = db.session.scalars(stmt).all()

    if not solutions:
        flash('Нет решений для экспорта по выбранным датам', 'warning')
        return redirect(url_for('tasks_list', id=id))

    # 4. Создаем ZIP в памяти (без записи на диск!)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for sol in solutions:
            # Генерируем имя файла: user_123_task_45_2024-01-15_14-30-00.py
            username = sol.solver.username if sol.solver else f'user_{sol.user_id}'
            lang_ext = {
                'python': '.py',
                'cpp': '.cpp',
                'java': '.java',
                'js': '.js'
            }.get(sol.language or 'text', '.txt')
            
            timestamp = sol.created_date.strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"task_{id}_{username}_{timestamp}{lang_ext}"

            # Добавляем файл в архив
            zip_file.writestr(filename, sol.content)

    zip_buffer.seek(0)

    # 5. Отдаем файл пользователю
    filename_archive = f"solutions_task_{id}.zip"
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename_archive
    )


@app.route('/view_solutions', methods=['GET'])
@admin_required
def view_solutions():
    
    if not current_user.is_authenticated:
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status') 
    page = request.args.get('page', 1, type=int)
    stmt = (
        sa.select(Solve)
        .options(
        selectinload(Solve.solver), # Подгружаем пользователя (поле solver)
        selectinload(Solve.task) # Подгружаем задачу (поле task)

        )
        .order_by(Solve.created_date.desc())
    )
    
    if status_filter == 'accepted':
        stmt = stmt.where(Solve.accept == True)
    elif status_filter == 'rejected':
        stmt = stmt.where(Solve.accept == False)

    pagination = db.paginate(stmt,page=page, per_page=10, error_out=False)
    count_accepted_stmt = select(func.count()).select_from(Solve).where(Solve.accept == True)
    count_rejected_stmt = select(func.count()).select_from(Solve).where(Solve.accept == False)
    
    total_accepted = db.session.scalar(count_accepted_stmt)
    total_rejected = db.session.scalar(count_rejected_stmt)
    
    next_url = url_for('view_solutions', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('view_solutions', page=pagination.prev_num) if pagination.has_prev else None
    
    return render_template('view_solutions.html', pagination=pagination,is_admin=is_admin, current_status=status_filter,total_accepted=total_accepted, total_rejected=total_rejected)                   


@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    form = UploadImageForm()
    if form.validate_on_submit():
        file = form.image.data
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            return 'Image uploaded successfully'
        else:
            return 'Invalid file type', 400
    
    return render_template('upload.html', form=form)



@app.route('/add_tests/<int:task_id>', methods=['GET'])
@admin_required  # Если нет админа, временно закомментируй эту строку
def add_tests(task_id):
    from app.models import Task, TestCase
    
    task = Task.query.get(task_id)
    if not task:
        return f"Задача с ID {task_id} не найдена", 404
    
    if task.task_type.name != 'code':
        return f"Ошибка: Задача должна быть типа 'code', а не '{task.task_type.name}'", 400

    # Удаляем старые тесты для этой задачи, чтобы не дублировать при повторном запуске
    TestCase.query.filter_by(task_id=task_id).delete()
    
    # Добавляем новые
    tests = [
        TestCase(task_id=task_id, order_index=1, input_data="2\n2", expected_output="4", is_sample=True),
        TestCase(task_id=task_id, order_index=2, input_data="10\n20", expected_output="30", is_sample=False)
    ]
    
    db.session.add_all(tests)
    db.session.commit()
    
    return f"✅ Тесты добавлены для задачи '{task.title}'. Теперь проверяй код на /task/{task_id}" 

@app.route('/summer', methods=['GET', 'POST'])
def summer():
    return render_template('summer.html') 

def is_admin():
    # Проверяем, залогинен ли пользователь вообще
    if not current_user.is_authenticated:
        return False
    
    # Тут мы проверяем имя роли. У тебя в модели Role поле называется 'rolename'
    # Если у пользователя нет роли (rolet равен None), то он точно не админ
    if not current_user.role:
        return False
        
    return current_user.role.rolename == 'admin'

