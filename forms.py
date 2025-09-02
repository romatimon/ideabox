from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, PasswordField, BooleanField
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional, Email
from models import IdeaCategory, Idea

class IdeaForm(FlaskForm):
    title = StringField('Заголовок идеи', 
                      validators=[
                          DataRequired(message="Поле обязательно"),
                          Length(max=100, message="Не более 100 символов")
                      ],
                      render_kw={
                          "placeholder": "Краткое название идеи",
                          "class": "form-control-lg"
                      })
    
    problem = TextAreaField('Проблема *',
                          validators=[
                              DataRequired(message="Поле обязательно"),
                              Length(min=20, message="Минимум 20 символов")
                          ],
                          render_kw={
                              "rows": 3,
                              "placeholder": "Опишите проблему, которую вы хотите решить"
                          })
    
    solution = TextAreaField('Предлагаемое решение *',
                           validators=[
                               DataRequired(message="Поле обязательно"),
                               Length(min=20, message="Минимум 20 символов")
                           ],
                           render_kw={
                               "rows": 3,
                               "placeholder": "Опишите ваше решение проблемы"
                           })
    
    description = TextAreaField('Дополнительное описание',
                              validators=[
                                  Optional(),  # Важно указать, что поле необязательное
                                  Length(max=500, message="Не более 500 символов")
                              ],
                              render_kw={
                                  "rows": 3,
                                  "placeholder": "Любая дополнительная информация"
                              })
    
    attachments = MultipleFileField('Прикрепленные файлы',
                                 validators=[
                                     Optional(),
                                     FileAllowed(['jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'], 
                                                'Разрешены только изображения и документы')
                                 ],
                                 render_kw={
                                     "class": "form-control",
                                     "multiple": True
                                 })
    
    author_name = StringField('Ваше имя',
                            validators=[
                                Optional(),  # Оставляем необязательным
                                Length(max=50, message="Не более 50 символов")
                            ],
                            render_kw={
                                "placeholder": "Оставьте пустым, если не хотите указывать"
                            })

    contact_email = StringField('Email для связи',
        validators=[
            Optional(),  # Оставляем необязательным
            Email(message="Введите корректный email"),
            Length(max=120)
        ],
        render_kw={
            "placeholder": "example@company.com",
            "class": "form-control"
        }
    )
    
    category = SelectField('Категория',
        validators=[DataRequired()],
        render_kw={"class": "form-select"})
    
    def __init__(self, *args, **kwargs):
        super(IdeaForm, self).__init__(*args, **kwargs)
        categories = IdeaCategory.query.filter_by(is_active=True).order_by('name').all()
        self.category.choices = [(c.name, c.name) for c in categories] or [('Общее', 'Общее')]
    
    submit = SubmitField('Отправить',
                       render_kw={"class": "btn btn-primary btn-lg w-100"})
    
class ModeratorLoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class EditIdeaForm(FlaskForm):
    title = StringField('Заголовок идеи',
                       validators=[
                           DataRequired(message="Поле обязательно"),
                           Length(max=100, message="Не более 100 символов")
                       ],
                       render_kw={"class": "form-control-lg"})
    
    problem = TextAreaField('Проблема',
                          validators=[DataRequired(message="Поле обязательно")],
                          render_kw={"class": "form-control", "rows": 4})
    
    solution = TextAreaField('Решение',
                           validators=[DataRequired(message="Поле обязательно")],
                           render_kw={"class": "form-control", "rows": 4})
    
    description = TextAreaField('Дополнительное описание',
                              validators=[Optional()],
                              render_kw={"class": "form-control", "rows": 3})
    
    status = SelectField('Статус', choices=[
        (Idea.STATUS_DRAFT, 'Черновик'),
        (Idea.STATUS_PENDING, 'На рассмотрении'),
        (Idea.STATUS_APPROVED, 'Одобрено'),
        (Idea.STATUS_REJECTED, 'Отклонено'),
        (Idea.STATUS_IN_PROGRESS, 'В работе'),
        (Idea.STATUS_IMPLEMENTED, 'Реализовано'),
        (Idea.STATUS_ARCHIVED, 'В архиве')
    ], validators=[DataRequired()])
    
    cost = SelectField('Стоимость',
                     choices=[
                         ('', 'Не выбрано'),
                         ('дорого', 'Дорого'),
                         ('бесплатно', 'Бесплатно')
                     ],
                     validators=[Optional()],
                     render_kw={"class": "form-select"})
    
    complexity = SelectField('Сложность',
                           choices=[
                               ('', 'Не выбрано'),
                               ('сложно', 'Сложно'),
                               ('просто', 'Просто')
                           ],
                           validators=[Optional()],
                           render_kw={"class": "form-select"})
    
    duration = SelectField('Время',
                         choices=[
                             ('', 'Не выбрано'),
                             ('долго', 'Долго'),
                             ('быстро', 'Быстро')
                         ],
                         validators=[Optional()],
                         render_kw={"class": "form-select"})
    
    submit = SubmitField('Сохранить',
                       render_kw={"class": "btn btn-primary"})
    

    moderator_feedback = TextAreaField('Обратная связь',
                                     validators=[Optional()],
                                     render_kw={
                                         "class": "form-control",
                                         "rows": 4,
                                         "placeholder": "Оставьте обратную связь автору"
                                     })


class CategoryForm(FlaskForm):
    name = StringField('Название категории', validators=[
        DataRequired(message="Поле обязательно для заполнения"),
        Length(min=2, max=100, message="Длина должна быть от 2 до 100 символов")
    ])
    description = TextAreaField('Описание', validators=[
        Length(max=500, message="Максимальная длина описания 500 символов")
    ])

class DeleteCategoryForm(FlaskForm):
    submit = SubmitField('Удалить')