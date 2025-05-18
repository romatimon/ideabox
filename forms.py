from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, PasswordField
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional, Email

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
    
    expected_result = TextAreaField('Ожидаемый результат *',
                                  validators=[
                                      DataRequired(message="Поле обязательно"),
                                      Length(min=20, message="Минимум 20 символов")
                                  ],
                                  render_kw={
                                      "rows": 2,
                                      "placeholder": "Опишите, каких результатов вы ожидаете"
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
                                Optional(),
                                Length(max=50, message="Не более 50 символов")
                            ],
                            render_kw={
                                "placeholder": "Оставьте пустым для анонимности"
                            })
    
    contact_email = StringField('Email для связи',
    validators=[
        Optional(),
        Email(message="Введите корректный email"),
        Length(max=120)
    ],
    render_kw={
        "placeholder": "example@company.com",
        "class": "form-control"
    }
)
    
    category = SelectField('Категория',
                        choices=[
                            ('Общее', 'Общие предложения'),
                            ('Процессы', 'Оптимизация процессов'),
                            ('Клиенты', 'Клиентское взаимодействие'),
                            ('Обучение', 'Обучение и развитие сотрудников'),
                            ('Маркетинг', 'Маркетинг и продвижение услуг'),
                            ('Культура', 'Корпоративная культура'),
                        ],
                        validators=[DataRequired()],
                        render_kw={"class": "form-select"})
    
    submit = SubmitField('Отправить',
                       render_kw={"class": "btn btn-primary btn-lg w-100"})

class CommentForm(FlaskForm):
    text = TextAreaField('Ваш комментарий',
                       validators=[
                           DataRequired(message="Поле обязательно для заполнения"),
                           Length(min=10, max=500, message="От 10 до 500 символов")
                       ],
                       render_kw={
                           "rows": 3,
                           "placeholder": "Напишите содержательный комментарий"
                       })
    
    author_name = StringField('Подпись (необязательно)',
                            validators=[
                                Optional(),
                                Length(max=50, message="Не более 50 символов")
                            ],
                            render_kw={
                                "placeholder": "Оставьте пустым для анонимности"
                            })
    
    submit = SubmitField('Опубликовать',
                       render_kw={"class": "btn btn-outline-primary"})
    
class ModeratorLoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')