from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,SelectField,IntegerField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
import sqlalchemy as sa
from app import db
from app.models import User, Role,Task,Topic,TaskType
from wtforms import TextAreaField
from wtforms.validators import Length
from wtforms import HiddenField
from wtforms_alchemy.fields import QuerySelectField 
from flask_wtf.file import FileField, FileAllowed, FileRequired


class UploadImageForm(FlaskForm):
    image = FileField(
        'Image',
        validators=[
            FileRequired(),  # Проверяет, что файл был выбран
            FileAllowed(['jpg', 'jpeg', 'png','gif','pdf'], 'Only image files are allowed.')
        ]
    )

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')
    
class RegistrationForm(FlaskForm):
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data))
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data))
        if user is not None:
            raise ValidationError('Please use a different emailaddress.')

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Please use a different username.')

class AdminRoleForm(FlaskForm):
    user_id = IntegerField('User ID', validators=[DataRequired()])
    new_role_id = SelectField('New Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Change Role')
    
class CreateTask(FlaskForm):
    topic = QuerySelectField(
        'Тема задачи', 
        query_factory=lambda: Topic.query.all(), 
        get_label='topic', 
        allow_blank=True,  # Разрешаем оставить пустым, если тема необязательна
        blank_text='-- Выберите тему --'
        )
    
    type_id = SelectField('Тип задачи', coerce=int, validators=[DataRequired()])
    
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[Length(min=0, max=10000)])
    answer = TextAreaField('Answer', validators=[DataRequired()])
    submit = SubmitField('Create task')
    
    def __init__(self, *args, **kwargs):
        super(CreateTask, self).__init__(*args, **kwargs)
        # Динамически загружаем типы задач из БД
        # <-- Проверь путь импорта! Может быть просто from models import TaskType
        types = TaskType.query.all()
        self.type_id.choices = [(t.id, t.description) for t in types]
    
   
class EditTask(FlaskForm):
    topic = QuerySelectField(
        'Тема задачи', 
        query_factory=lambda: Topic.query.all(), 
        get_label='topic', 
        allow_blank=True,  # Разрешаем оставить пустым, если тема необязательна
        blank_text='-- Выберите тему --'
        )
    
    type_id = SelectField('Тип задачи', coerce=int, validators=[DataRequired()])
    
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[Length(min=0, max=10000)])
    answer = TextAreaField('Answer', validators=[DataRequired()])
    submit = SubmitField('Edit task')
    
    def __init__(self, *args, **kwargs):
        super(EditTask, self).__init__(*args, **kwargs)
        types = TaskType.query.all()
        self.type_id.choices = [(t.id, t.description) for t in types]
    
class DeleteForm(FlaskForm):
    # Это поле нужно только для CSRF токена, если используешь hidden_tag()
    csrf_token = HiddenField() 

class SubmitForm(FlaskForm):
    # Это поле нужно только для CSRF токена, если используешь hidden_tag()
    csrf_token = HiddenField() 
    answer = StringField('Enter your answer:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
class SolutionForm(FlaskForm):  # Назовем её SolutionForm, так как это форма отправки решения, а не создания задачи
    # Для ответа используем TextAreaField (он всегда многострочный)
    # Мы будем управлять его высотой через CSS классы в шаблоне
    csrf_token = HiddenField() 
    # 1. Выпадающий список языков
    language = SelectField(
        'Язык программирования',
        choices=[('python', 'Python'), ('cpp', 'C++'), ('java', 'Java')],
        default='python',
        validators=[DataRequired()]
    )
    
    # 2. Поле для ответа (оставляем как было)
    answer = TextAreaField('Ваш ответ', validators=[DataRequired()])
    submit = SubmitField('Отправить решение')

class CreateTopic(FlaskForm):
    csrf_token = HiddenField() 
    topic = StringField('Enter new topic:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
class CodeForm(FlaskForm):
    language = SelectField('Язык', choices=[
        ('python3', 'Python 3'),
        ('cpp', 'C++'),
        ('java', 'Java')
    ], default='python3')
    code = TextAreaField('Код решения', validators=[DataRequired()])
    submit = SubmitField('Запустить тесты')


