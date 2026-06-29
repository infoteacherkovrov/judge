from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from app import login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5

class Role(UserMixin,db.Model):
    __tablename__ = 'roles'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    rolename:so.Mapped[str] = so.mapped_column(sa.String(30), index=True,
                                                unique=True)
    roles: so.WriteOnlyMapped[list['User']] = so.relationship(back_populates='rolet')
    
    def __repr__(self):
        return '<Role {}>'.format(self.rolename)
    
class User(UserMixin, db.Model):
    __tablename__ ='users'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))
    
    role_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Role.id),index=True)
    rolet: so.Mapped['Role'] = so.relationship(back_populates='roles')
    
    task_user: so.Mapped['Task']=so.relationship(back_populates='user_task')
    
    solve_user: so.Mapped[list['Solve']] = so.relationship(back_populates='user_solve')
    
    def __repr__(self):
        return '<User {}>'.format(self.username)
    
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
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)
    
class Task(UserMixin, db.Model):
    __tablename__ ='tasks'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True, autoincrement=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    
    content: so.Mapped[str] = so.mapped_column(sa.String, nullable=True, default='Условие')
    subject: so.Mapped[str] = so.mapped_column(sa.String, nullable=True, default='Без темы')
    created_date: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    rating: so.Mapped[int] = so.mapped_column(sa.Integer,nullable=True,default=1)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               nullable = True)
    user_task: so.Mapped['User'] = so.relationship(back_populates='task_user')
    
    solve_task: so.Mapped['Solve'] = so.relationship(back_populates='task_solve',cascade="all,delete")
    
    def __repr__(self):
        return '<Task {}>'.format(self.title)
    
   

class Solve(UserMixin, db.Model):
    __tablename__ ='solves'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True,autoincrement=True)
    content: so.Mapped[str] = so.mapped_column(sa.String, nullable = True)
    accept: so.Mapped[bool] = so.mapped_column(sa.Boolean, default = False)
    created_date: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               nullable=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Task.id),
                                               nullable=True)
  
    user_solve: so.Mapped['User'] = so.relationship(back_populates='solve_user')
    task_solve: so.Mapped['Task'] = so.relationship(back_populates='solve_task')
    
    
 
    
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))