from datetime import datetime, timezone
from typing import Optional,List
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from app import login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5

class TaskType(db.Model):
    __tablename__ = 'task_types'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, nullable=False) # 'text', 'code', 'file'
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    
   

    def __repr__(self):
        return f'<TaskType {self.name}>'

class Topic(UserMixin,db.Model):
    __tablename__ = 'topics' 
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    topic: so.Mapped[str] = so.mapped_column(sa.String(50), index=True, unique=True)
    tasks: so.WriteOnlyMapped[list['Task']] = so.relationship(back_populates='topic')

class Role(UserMixin, db.Model):
    __tablename__ = 'roles'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    rolename: so.Mapped[str] = so.mapped_column(sa.String(30), index=True, unique=True)
    users: so.WriteOnlyMapped[list['User']] = so.relationship(back_populates='role')
    
    def __repr__(self):
        return f'<Role {self.rolename}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    role_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Role.id), index=True)
    role: so.Mapped['Role'] = so.relationship(back_populates='users')
    
    task_user: so.Mapped['Task'] = so.relationship(back_populates='creator')
    solve_user: so.Mapped[list['Solve']] = so.relationship(back_populates='solver')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

class Post(db.Model):
    __tablename__ = 'posts'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return f'<Post {self.body}>'

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    content: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=True, default='Условие')
     
    topic_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Topic.id, name='fk_tasks_topic'), nullable=True)
    topic: so.Mapped['Topic'] = so.relationship(back_populates='tasks')
    
    answer: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=True, default='Без ответа')
    
    created_date: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    rating: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=True, default=1)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=True)
    
    creator: so.Mapped['User'] = so.relationship(back_populates='task_user')
    solve_task: so.Mapped[list['Solve']] = so.relationship(back_populates='task', cascade="all,delete")
    
     # 👇 ВОТ ЭТО МЫ ДОБАВИЛИ:
    type_id = db.Column(db.Integer, sa.ForeignKey('task_types.id'), nullable=False)
    
    # 👇 И ЭТО (чтобы удобно обращаться к типу, например task.task_type.name):
    task_type = db.relationship('TaskType', backref='tasks', lazy=True)
    
    tests: so.Mapped[list['TestCase']] = so.relationship(back_populates='task', cascade="all, delete", order_by="TestCase.order_index")
    
    def __repr__(self):
        return f'<Task {self.title}>'

class Solve(db.Model):
    __tablename__ = 'solves'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    
    content: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=True)
    
    language = so.mapped_column(db.String(20), nullable=True, default='python') 
    accept: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)
    created_date: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Task.id), nullable=True)
  
    solver: so.Mapped['User'] = so.relationship(back_populates='solve_user')
    task: so.Mapped['Task'] = so.relationship(back_populates='solve_task')
    
    __table_args__ = (
        db.Index('idx_solves_user_task', 'user_id', 'task_id'), 
    )
    
class TestCase(db.Model):
    __tablename__ = 'test_cases'

    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    
    # Связь с задачей: один тест принадлежит одной задаче
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('tasks.id'), nullable=False, index=True)
    
    # Входные данные (строка). Сюда можно кидать числа, JSON, текст — всё, что нужно программе на вход.
    input_data: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=False)
    
    # Ожидаемый результат (строка). То, что программа должна вывести.
    expected_output: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=False)
    
    # Порядок важен! Тесты должны идти строго по порядку, иначе проверка будет хаотичной.
    order_index: so.Mapped[int] = so.mapped_column(default=0, index=True)

    # Флаг: это пример для пользователя (видно в условии) или скрытый тест?
    is_sample: so.Mapped[bool] = so.mapped_column(default=False)

    # 👇 Вот эта строка отвечает за связь с твоим Task. 
    # Она должна точно совпадать с именем поля в Task (там у тебя 'tests')
    task: so.Mapped['Task'] = so.relationship(back_populates='tests')

    def __repr__(self):
        return f'<TestCase #{self.id} for Task {self.task_id}>'
    
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
import sqlalchemy as sa
from datetime import datetime, timezone


    

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))