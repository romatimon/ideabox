from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField, 
    PasswordField, BooleanField
)
from wtforms.validators import DataRequired, Length, Optional, Email

from models import IdeaCategory, Idea


class IdeaForm(FlaskForm):
    """Форма для добавления новой идеи."""
    
    title = StringField(
        'Название идеи',
        validators=[
            DataRequired(message="Поле обязательно"),
            Length(max=100, message="Не более 100 символов")
        ],
        render_kw={
            "placeholder": "Дайте краткое название",
            "class": "form-control-lg"
        }
    )
    
    essence = TextAreaField(
        'В чем суть идеи',
        validators=[
            DataRequired(message="Поле обязательно"),
            Length(min=10, message="Минимум 10 символов")
        ],
        render_kw={
            "rows": 3,
            "placeholder": "Напишите, что можно улучшить и почему"
        }
    )
    
    solution = TextAreaField(
        'Варианты решения',
        validators=[
            DataRequired(message="Поле обязательно"),
            Length(min=10, message="Минимум 10 символов")
        ],
        render_kw={
            "rows": 3,
            "placeholder": "Напишите, как можно улучшить процесс/реализовать идею"
        }
    )
    
    description = TextAreaField(
        'Дополнительно',
        validators=[
            Optional(),
            Length(max=500, message="Не более 500 символов")
        ],
        render_kw={
            "rows": 3,
            "placeholder": "Если что-то важное не вошло в описание идеи и вариантов решения"
        }
    )
    
    attachments = MultipleFileField(
        'Прикрепленные файлы',
        validators=[
            Optional(),
            FileAllowed(
                ['jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'], 
                'Разрешены только изображения и документы'
            )
        ],
        render_kw={
            "class": "form-control",
            "multiple": True
        }
    )
    
    author_name = StringField(
        'Имя',
        validators=[
            Optional(),
            Length(max=50, message="Не более 50 символов")
        ],
        render_kw={
            "placeholder": "Оставьте пустым, если хотите сохранить анонимность"
        }
    )

    contact_email = StringField(
        'Email для обратной связи',
        validators=[
            Optional(),
            Email(message="Введите корректный email"),
            Length(max=120)
        ],
        render_kw={
            "placeholder": "IvanPM@rostest.ru (укажите рабочую почту)",
            "class": "form-control"
        }
    )
    
    category = SelectField(
        'Категория',
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    submit = SubmitField(
        'Отправить',
        render_kw={"class": "btn btn-primary btn-lg w-100"}
    )
    
    def __init__(self, *args, **kwargs):
        """Инициализация формы с загрузкой категорий."""
        super(IdeaForm, self).__init__(*args, **kwargs)
        categories = IdeaCategory.query.filter_by(is_active=True).order_by('name').all()
        
        # Добавляем пустую опцию в начало списка
        category_choices = [('', '--- Выберите категорию ---')]
        category_choices.extend([(c.name, c.name) for c in categories])
        
        self.category.choices = category_choices
        
        # Сохраняем описания для использования в шаблоне
        self.category.descriptions = {c.name: c.description or '' for c in categories}
        
        # Если нет категорий, оставляем только пустой выбор
        if not categories:
            self.category.choices = [('', '--- Нет доступных категорий ---')]


class ModeratorLoginForm(FlaskForm):
    """Форма входа для модераторов."""
    
    username = StringField(
        'Логин', 
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Введите логин"}
    )
    
    password = PasswordField(
        'Пароль', 
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Введите пароль"}
    )
    
    submit = SubmitField(
        'Войти',
        render_kw={"class": "btn btn-primary w-100"}
    )


class EditIdeaForm(FlaskForm):
    """Форма редактирования идеи модератором."""
    
    title = StringField(
        'Название идеи',
        validators=[
            DataRequired(message="Поле обязательно"),
            Length(max=100, message="Не более 100 символов")
        ],
        render_kw={"class": "form-control-lg"}
    )
    
    essence = TextAreaField(
        'В чем суть идеи',
        validators=[DataRequired(message="Поле обязательно")],
        render_kw={"class": "form-control", "rows": 4}
    )
    
    solution = TextAreaField(
        'Варианты решения',
        validators=[DataRequired(message="Поле обязательно")],
        render_kw={"class": "form-control", "rows": 4}
    )
    
    description = TextAreaField(
        'Дополнительно',
        validators=[Optional()],
        render_kw={"class": "form-control", "rows": 3}
    )
    
    category = SelectField(
        'Категория',
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    status = SelectField(
        'Статус', 
        choices=[
            (Idea.STATUS_PENDING, 'На рассмотрении'),
            (Idea.STATUS_APPROVED, 'Одобрено'),
            (Idea.STATUS_PARTIALLY_APPROVED, 'Одобрено (частично)'),
            (Idea.STATUS_IN_PROGRESS, 'На реализации'),
            (Idea.STATUS_IMPLEMENTED, 'Реализовано'),
            (Idea.STATUS_REJECTED, 'Отклонено')
        ], 
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )

    moderator_feedback = TextAreaField(
        'Комментарий модератора',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Введите комментарий или сообщение"
        }
    )
    
    submit = SubmitField(
        'Сохранить',
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, *args, **kwargs):
        """Инициализация формы с загрузкой категорий."""
        super(EditIdeaForm, self).__init__(*args, **kwargs)
        categories = IdeaCategory.query.filter_by(is_active=True).order_by('name').all()
        self.category.choices = [(c.name, c.name) for c in categories]
        
        # Если нет категорий, добавляем пустой выбор
        if not categories:
            self.category.choices = [('', '--- Нет категорий ---')]

        if kwargs.get('obj'):
            # Восстанавливаем переносы строк для редактирования
            self.essence.data = kwargs['obj'].essence
            self.solution.data = kwargs['obj'].solution


class CategoryForm(FlaskForm):
    """Форма для добавления/редактирования категорий."""
    
    name = StringField(
        'Название категории', 
        validators=[
            DataRequired(message="Поле обязательно для заполнения"),
            Length(min=2, max=100, message="Длина должна быть от 2 до 100 символов")
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "Введите название категории"
        }
    )
    
    description = TextAreaField(
        'Описание', 
        validators=[
            Length(max=500, message="Максимальная длина описания 500 символов")
        ],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Введите описание категории (необязательно)"
        }
    )
    
    submit = SubmitField(
        'Сохранить',
        render_kw={"class": "btn btn-success"}
    )


class DeleteCategoryForm(FlaskForm):
    """Форма для удаления категорий."""
    
    submit = SubmitField(
        'Удалить',
        render_kw={"class": "btn btn-danger"}
    )



class EditCategoryForm(FlaskForm):
    """Форма для редактирования категорий."""
    
    name = StringField(
        'Название категории', 
        validators=[
            DataRequired(message="Поле обязательно для заполнения"),
            Length(min=2, max=100, message="Длина должна быть от 2 до 100 символов")
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "Введите название категории"
        }
    )
    
    description = TextAreaField(
        'Описание', 
        validators=[
            Length(max=500, message="Максимальная длина описания 500 символов")
        ],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Введите описание категории (необязательно)"
        }
    )
    
    submit = SubmitField(
        'Сохранить изменения',
        render_kw={"class": "btn btn-primary"}
    )
