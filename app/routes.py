from flask import render_template, flash, redirect, url_for
from app import app,db
from app.forms import LoginForm, RegistrationForm, AdminRoleForm, CreateTask
from flask_login import current_user, login_user,logout_user
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.models import User, Role,Task
from flask_login import login_required
from flask import request
from urllib.parse import urlsplit
from datetime import datetime, timezone
from app.forms import EditProfileForm




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
    return render_template('user.html', user=user, posts=posts)

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
            old_role_name = user.rolet.rolename if user.rolet else "None"
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
        print(f"Получен subject: {form.subject.data} (тип: {type(form.subject.data)})")
        
        newtask = Task(title=form.title.data, content=form.content.data, subject=form.subject.data)
        newtask.created_date = datetime.now(timezone.utc)
        newtask.user_id=current_user.id
        
        db.session.add(newtask)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('create_task'))
    '''elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me'''
    return render_template('create_task.html', title='Create task',
                           form=form)

@app.route('/view_tasks', methods=['GET'])
@login_required
def view_tasks():
    if not is_admin():
        flash('У вас нет прав для доступа к этой странице', 'danger')
        return redirect(url_for('index'))  # или url_for('login'), куда хочешь редиректить
    tasks = db.session.scalars(sa.select(Task)).all()
    return render_template('view_tasks.html', tasks=tasks)

@app.route('/task/<id>')
@login_required
def task(id):
    task2 = db.first_or_404(sa.select(Task).where(Task.id == id))
    print(f"Получен id: {task2} (тип: {type(task2)})")
    content2='3434324'
    return render_template('task.html', task=task2 )

def is_admin():
    # Проверяем, залогинен ли пользователь вообще
    if not current_user.is_authenticated:
        return False
    
    # Тут мы проверяем имя роли. У тебя в модели Role поле называется 'rolename'
    # Если у пользователя нет роли (rolet равен None), то он точно не админ
    if not current_user.rolet:
        return False
        
    return current_user.rolet.rolename == 'admin'