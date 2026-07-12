from flask import render_template, flash, redirect, url_for, abort
from app import app,db
from app.forms import LoginForm, RegistrationForm, AdminRoleForm, CreateTask, EditTask, DeleteForm, SubmitForm, CreateTopic
from flask_login import current_user, login_user,logout_user
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.models import User, Role, Task, Solve, Topic
from flask_login import login_required
from flask import request
from urllib.parse import urlsplit
from datetime import datetime, timezone
from app.forms import EditProfileForm

from flask_login import login_required
from sqlalchemy import select
from flask import abort
from functools import wraps

from sqlalchemy.orm import selectinload


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
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    
    
    stmt = (
            select(Solve)
            
            .join(Solve.solver)  # Важно: явно указываем JOIN, чтобы можно было фильтровать по полям пользователя
            .where(User.username == username) # Сравниваем поле username пользователя со строкой
            .order_by(Solve.created_date.desc())
            .options(
                selectinload(Solve.solver),  # Подгружаем пользователя (поле solver)
                selectinload(Solve.task)    # Подгружаем задачу (на всякий случай)
            )
        )
        
    
    solutions = db.session.scalars(stmt).all()
     
    return render_template('user.html', user=user, posts=posts, solutions=solutions)

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
    return render_template('view_users.html', users=users)


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
        print("--- ОТЛАДКА: Форма прошла валидацию ---")
        print(f"Получен user_id: {form.user_id.data} (тип: {type(form.user_id.data)})")
        print(f"Получен new_role_id: {form.new_role_id.data} (тип: {type(form.new_role_id.data)})")

        user = User.query.get(form.user_id.data)
        
        if user:
            old_role_name = user.role.rolename if user.role else "None"
            user.role_id = form.new_role_id.data
            db.session.commit()
            print(f"✅ УСПЕХ: Роль пользователя {user.username} изменена с '{old_role_name}' на '{Role.query.get(form.new_role_id.data).rolename}'")
            flash(f'Роль пользователя {user.username} успешно изменена', 'success')
        else:
            print("❌ ОШИБКА: Пользователь не найден!")
            flash('Пользователь не найден', 'danger')
            
        return redirect(url_for('admin_users'))
    else:
        # Если валидация НЕ прошла, выводим ошибки в консоль
        if request.method == 'POST':
            print("--- ОТЛАДКА: Валидация НЕ пройдена ---")
            print(f"Ошибки формы: {form.errors}")
            # Это критически важно: если тут есть ошибки, код до commit не доходит!

    return render_template('admin_users.html', users=users, roles=roles, form=form)




@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
    form = CreateTask()
    if form.validate_on_submit():
        
        print("--- ОТЛАДКА: Форма прошла валидацию ---")
        print(f"Получен title: {form.title.data} (тип: {type(form.title.data)})")
        print(f"Получен content: {form.content.data} (тип: {type(form.content.data)})")
       
       
        newtask = Task(title=form.title.data, content=form.content.data, answer=form.answer.data)
        newtask.created_date = datetime.now(timezone.utc)
        newtask.user_id=current_user.id
        
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
    '''elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me'''
    return render_template('create_task.html', title='Create task',
                           form=form)
    
@app.route('/create_topic', methods=['GET', 'POST'])
@admin_required
def create_topic():
    form = CreateTopic()
    if form.validate_on_submit():
        
        print("--- ОТЛАДКА: Форма прошла валидацию ---")
        print(f"Получен topic: {form.topic.data} (тип: {type(form.topic.data)})")
               
        newtopic = Topic(topic=form.topic.data)
        db.session.add(newtopic)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('view_tasks'))
    '''elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me'''
    return render_template('create_topic.html', title='Create topic', form=form)

@app.route('/view_tasks', methods=['GET'])
@login_required
def view_tasks():
    
    
    topics = Topic.query.all()
    selected_topic_id = request.args.get('topic_id', type=int)
    query = Task.query.options(so.joinedload(Task.topic))
    if selected_topic_id:
         query = query.filter(Task.topic_id == selected_topic_id)
    tasks = query.all() 
    
    '''
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
        '''
    
    page = request.args.get('page', 1, type=int)  
    #subj = request.args.get('subj')
    #if subj:
    #    query = Task.query.filter(Task.subject == subj)
    #else:
    #    query = Task.query
  
    query = query.order_by(Task.created_date.desc())
    #per_page = request.args.get('per_page', 10, type=int)
  
    pagination = db.paginate(query,page=page, per_page=10, error_out=False)
    tasks=pagination.items
    next_url = url_for('view_tasks', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('view_tasks', page=pagination.prev_num) if pagination.has_prev else None
    
    form = DeleteForm()
    return render_template('view_tasks.html', tasks=tasks,form=form,is_admin=is_admin, next_url=next_url,
                           prev_url=prev_url,pagination=pagination, topics=topics, selected_topic_id=selected_topic_id)

@app.route('/task/<id>', methods=['GET','POST'])
@login_required
def task(id):
    task2 = db.session.get(Task, id)
    if not task2:
        return abort(404)
    form = SubmitForm()
    if form.validate_on_submit():
        
        
        newans = Solve(content=form.answer.data)
        
        print("--- ОТЛАДКА: Форма прошла валидацию ---")
        
        
        newans.created_date = datetime.now(timezone.utc)
        newans.user_id=current_user.id
        newans.task_id=id
        
        
        curr = db.session.get(Task, id)
        print(f"Получен Answer: {curr.answer} (тип: {type(curr.answer)})")
        print(f"Получен form.answer.data: {form.answer.data} (тип: {type(form.answer.data)})")
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
    
       
    return render_template('task.html', task=task2,is_admin=is_admin, form=form, solution=solution)

@app.route('/task/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    edittask = db.first_or_404(sa.select(Task).where(Task.id == id))
    #пользователь может редактировать только свои задачи
    if edittask.user_id != current_user.id:
        abort(403)
    
    
    form = EditTask(obj=edittask)
    
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(edittask)  # обновляем объект данными из формы
        db.session.commit()
        return redirect(url_for('task', id=edittask.id))
    '''
    if form.validate():
        form.populate_obj(edittask)  # автоматически заполняет объект task данными из формы
        db.session.commit()
        return redirect(url_for('task', id=edittask.id))
    '''
    return render_template('edit_task.html', form=form, id=edittask.id)

@app.route('/task/<int:id>/delete', methods=['POST'])
@login_required
def delete_task(id):
    
    
        
    stmt = select(Task).where(Task.id == id)
    result = db.session.execute(stmt)
    deltask = result.scalars().first()

    if not task:
        flash('Задача не найдена', 'warning')
        return redirect(url_for('view_tasks'))
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

    return redirect(url_for('view_tasks'))    
    
     
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
                   

def is_admin():
    # Проверяем, залогинен ли пользователь вообще
    if not current_user.is_authenticated:
        return False
    
    # Тут мы проверяем имя роли. У тебя в модели Role поле называется 'rolename'
    # Если у пользователя нет роли (rolet равен None), то он точно не админ
    if not current_user.role:
        return False
        
    return current_user.role.rolename == 'admin'

