from datetime import datetime
from functools import wraps
from io import BytesIO
import os

from dotenv import load_dotenv
from flask import (
    Flask, abort, current_app, flash, jsonify, redirect, render_template, 
    request, send_file, send_from_directory, session, url_for
)
from flask_wtf.csrf import CSRFProtect
from openpyxl import Workbook
from sqlalchemy import Engine, func, or_, select
from werkzeug.utils import secure_filename

from extensions import db
from forms import (
    CategoryForm, DeleteCategoryForm, EditCategoryForm, EditIdeaForm, IdeaForm, ModeratorLoginForm
)
from models import Attachment, Idea, IdeaCategory, Moderator
from notifications import send_new_idea_notification, send_author_confirmation, send_status_update_notification


# Загрузка переменных окружения
load_dotenv()


# Инициализация приложения
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY'),
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI'),
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB
    WTF_CSRF_ENABLED=True
)


# Инициализация расширений
csrf = CSRFProtect(app)
db.init_app(app)


# Конфигурация
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}


# Создаем папку для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.template_filter('nl2br')
def nl2br_filter(value):
    """Преобразует переносы строк в HTML теги <br>."""
    if not value:
        return ''
    
    # Преобразуем в строку
    value = str(value)
    
    # Заменяем все виды переносов строк
    # Сначала заменяем \r\n, потом \n, потом \r
    value = value.replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')
    
    return value


# Вспомогательные функции
def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def set_sqlite_pragma(dbapi_connection, connection_record):
    """Включает поддержку внешних ключей для SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def moderator_required(f):
    """Декоратор для проверки авторизации модератора."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('moderator_id'):
            flash('Требуется авторизация модератора', 'warning')
            return redirect(url_for('moderator_login'))
            
        moderator = db.session.get(Moderator, session['moderator_id'])
        if not moderator:
            session.pop('moderator_id', None)
            flash('Сессия устарела, войдите снова', 'warning')
            return redirect(url_for('moderator_login'))
            
        return f(*args, **kwargs)
    return decorated_function


# Контекстные процессоры
@app.context_processor
def utility_processor():
    def filesizeformat(value):
        """Правильное форматирование размера файла."""
        if value == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} TB"
    
    return dict(filesizeformat=filesizeformat, os=os)


@app.context_processor
def inject_moderator():
    """Добавляет информацию о текущем модераторе в контекст шаблонов."""
    if 'moderator_id' in session:
        moderator = db.session.get(Moderator, session['moderator_id'])
        return {'current_moderator': moderator}
    return {}


# Фильтры Jinja2
app.jinja_env.filters['filesizeformat'] = lambda value: value


# Функции инициализации
def init_moderators():
    """Инициализирует учетные записи модераторов."""
    moderators = [
        {
            'username': 'vlasuk', 
            'first_name': 'Ольга', 
            'last_name': 'Власюк',
            'password': os.getenv('MODERATOR_VLASUK_PWD'),
            'can_manage_categories': True
        },
        {
            'username': 'schekoldina', 
            'first_name': 'Анастасия', 
            'last_name': 'Щеколдина',
            'password': os.getenv('MODERATOR_SCHEKOLDINA_PWD'),
            'can_manage_categories': True
        }
    ]
    
    for mod in moderators:
        if not Moderator.query.filter_by(username=mod['username']).first():
            moderator = Moderator(
                username=mod['username'],
                first_name=mod['first_name'],
                last_name=mod['last_name'],
                can_manage_categories=mod['can_manage_categories']
            )
            moderator.set_password(mod['password'])
            db.session.add(moderator)
    db.session.commit()


def init_categories():
    """Инициализирует базовые категории идей."""
    default_categories = []  # Пустой список
    
    for cat in default_categories:
        if not db.session.execute(
            db.select(IdeaCategory).where(IdeaCategory.name == cat['name'])
        ).scalar_one_or_none():
            category = IdeaCategory(
                name=cat['name'],
                description=cat['description']
            )
            db.session.add(category)
    db.session.commit()


# Маршруты аутентификации
@app.route('/moderator/login', methods=['GET', 'POST'])
def moderator_login():
    """Страница входа для модераторов."""
    if session.get('moderator_id'):
        return redirect(url_for('index'))
        
    form = ModeratorLoginForm()
    if form.validate_on_submit():
        moderator = db.session.execute(
            select(Moderator).where(Moderator.username == form.username.data)
        ).scalar_one_or_none()
        if moderator and moderator.check_password(form.password.data):
            session['moderator_id'] = moderator.id
            flash(f'Добро пожаловать, {moderator.full_name}!', 'success')
            return redirect(url_for('index'))
        flash('Неверные учетные данные', 'danger')
    return render_template('moderator_login.html', form=form)


@app.route('/moderator/logout')
def moderator_logout():
    """Выход из системы модератора."""
    session.pop('moderator_id', None)
    flash('Вы вышли из режима модератора', 'info')
    return redirect(url_for('index'))


# Основные маршруты
@app.route('/')
def index():
    """Главная страница со списком идей."""
    page = request.args.get('page', 1, type=int)
    per_page = 6

    # Получаем параметры фильтрации
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort', 'newest')

    # Для ВСЕХ пользователей (включая модераторов) показываем только опубликованные идеи на главной
    query = Idea.query.filter_by(is_published=True)

    # Применяем фильтры
    if status_filter != 'all':
        query = query.filter(Idea.status == status_filter)

    if category_filter != 'all':
        query = query.filter(Idea.category == category_filter)

    if search_query:
        query = query.filter(or_(
            Idea.title.ilike(f'%{search_query}%'),
            Idea.essence.ilike(f'%{search_query}%'),
            Idea.solution.ilike(f'%{search_query}%'),
            Idea.description.ilike(f'%{search_query}%')
        ))

    # Применяем сортировку
    if sort_by == 'newest':
        query = query.order_by(Idea.created_at.desc())
    else:
        query = query.order_by(Idea.created_at.asc())

    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    ideas = pagination.items

    # Получаем список категорий для фильтра
    categories = IdeaCategory.query.filter_by(is_active=True).order_by(IdeaCategory.name).all()

    return render_template('index.html', 
                         ideas=ideas,
                         pagination=pagination,
                         current_status=status_filter,
                         current_category=category_filter,
                         current_sort=sort_by,
                         search_query=search_query,
                         categories=categories)


@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    """Добавление новой идеи."""
    form = IdeaForm()
    
    if form.validate_on_submit():
        try:
            # Проверяем, что выбрана категория
            if not form.category.data:
                flash('Пожалуйста, выберите категорию', 'danger')
                return render_template('add_idea.html', form=form)
            
            idea = Idea(
                title=form.title.data.strip(),
                essence=form.essence.data,
                solution=form.solution.data,
                description=form.description.data.strip() if form.description.data else None,
                author_name=form.author_name.data.strip() if form.author_name.data else None,
                contact_email=form.contact_email.data.strip() if form.contact_email.data else None,
                is_anonymous=False,
                category=form.category.data,
                status=Idea.STATUS_PENDING
            )
            
            db.session.add(idea)
            db.session.flush()  # Получаем ID до коммита
            
            # Обработка файлов
            if 'attachments' in request.files:
                files = request.files.getlist('attachments')
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{idea.id}_{filename}")
                        file.save(os.path.join(current_app.root_path, filepath))
                        
                        attachment = Attachment(
                            filename=filename,
                            filepath=filepath,
                            idea_id=idea.id
                        )
                        db.session.add(attachment)
            
            db.session.commit()

            # Уведомление модератору
            send_new_idea_notification(idea)
            
            # Подтверждение автору (если указан email)
            send_author_confirmation(idea)
            
            flash('Идея успешно отправлена на модерацию!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении идеи: {str(e)}', 'danger')
    
    return render_template('add_idea.html', form=form)


@app.route('/idea/<int:id>')
def idea_detail(id):
    """Детальная страница идеи."""
    idea = db.session.get(Idea, id) or abort(404)
    
    # Проверка публикации для обычных пользователей
    if not session.get('moderator_id') and not idea.is_published:
        abort(403)
    
    current_moderator = None
    if 'moderator_id' in session:
        current_moderator = db.session.get(Moderator, session['moderator_id'])
    
    return render_template(
        'idea_detail.html', 
        idea=idea,
        current_moderator=current_moderator
    )


# Маршруты для работы с файлами
@app.route('/download/<int:id>')
def download_attachment(id):
    """Скачивание прикрепленного файла."""
    attachment = Attachment.query.get_or_404(id)
    if not os.path.exists(os.path.join(current_app.root_path, attachment.filepath)):
        abort(404)
    return send_from_directory(
        os.path.dirname(os.path.join(current_app.root_path, attachment.filepath)),
        os.path.basename(attachment.filepath),
        as_attachment=True
    )


# Маршруты модератора
@app.route('/mod_dashboard')
@moderator_required
def mod_dashboard():
    """Панель управления модератора."""
    page = request.args.get('page', 1, type=int)
    per_page = 6
    
    status_filter = request.args.get('status', 'all')
    published_filter = request.args.get('published', 'all')
    category_filter = request.args.get('category', 'all')
    
    # Параметры сортировки
    sort_field = request.args.get('sort', 'created_at')
    sort_direction = request.args.get('dir', 'desc')
    
    # Формируем базовый запрос
    query = Idea.query
    
    # Применяем фильтры
    if status_filter != 'all':
        query = query.filter(Idea.status == status_filter)
    
    if published_filter == 'published':
        query = query.filter(Idea.is_published == True)
    elif published_filter == 'unpublished':
        query = query.filter(Idea.is_published == False)
    
    if category_filter != 'all':
        query = query.filter(Idea.category == category_filter)
    
    # Применяем сортировку
    if sort_field == 'title':
        field = Idea.title
    elif sort_field == 'author':
        field = Idea.author_name
    elif sort_field == 'category':
        field = Idea.category
    elif sort_field == 'status':
        field = Idea.status
    else:  # по умолчанию сортируем по дате
        field = Idea.created_at
    
    if sort_direction == 'asc':
        query = query.order_by(field.asc())
    else:
        query = query.order_by(field.desc())
    
    # Применяем пагинацию
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    ideas = pagination.items
    
    # Получаем список категорий для фильтра
    categories = IdeaCategory.query.filter_by(is_active=True).order_by(IdeaCategory.name).all()
    
    return render_template('mod_dashboard.html', 
                         ideas=ideas,
                         pagination=pagination,
                         categories=categories,
                         sort_field=sort_field,
                         sort_direction=sort_direction)



@app.route('/stats')
@moderator_required
def stats():
    """Страница статистики."""
    # Категориальная статистика
    categories = [cat.name for cat in IdeaCategory.query.filter_by(is_active=True).all()]
    category_counts = [Idea.query.filter_by(category=cat).count() for cat in categories]
    
    # Статистика по статусам
    total_ideas = Idea.query.count()
    pending_ideas = Idea.query.filter_by(status=Idea.STATUS_PENDING).count()
    approved_ideas = Idea.query.filter_by(status=Idea.STATUS_APPROVED).count()
    partially_approved_ideas = Idea.query.filter_by(status=Idea.STATUS_PARTIALLY_APPROVED).count()
    in_progress_ideas = Idea.query.filter_by(status=Idea.STATUS_IN_PROGRESS).count()
    implemented_ideas = Idea.query.filter_by(status=Idea.STATUS_IMPLEMENTED).count()
    rejected_ideas = Idea.query.filter_by(status=Idea.STATUS_REJECTED).count()
    
    return render_template('stats.html', 
                         categories=categories,
                         category_counts=category_counts,
                         total_ideas=total_ideas,
                         pending_ideas=pending_ideas,
                         approved_ideas=approved_ideas,
                         partially_approved_ideas=partially_approved_ideas,
                         in_progress_ideas=in_progress_ideas,
                         implemented_ideas=implemented_ideas,
                         rejected_ideas=rejected_ideas)


@app.route('/export-ideas')
@moderator_required
def export_ideas():
    """Экспорт идей в Excel."""
    try:
        # Получаем параметры фильтрации
        status = request.args.get('status', 'all')
        category = request.args.get('category', 'all')
        
        # Формируем запрос с фильтрами
        query = Idea.query
        if status != 'all':
            query = query.filter(Idea.status == status)
        if category != 'all':
            query = query.filter(Idea.category == category)
        
        ideas = query.order_by(Idea.created_at.desc()).all()
        
        # Создаем Excel-файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Идеи"
        
        # Заголовки
        headers = [
            "ID", "Заголовок", "Проблема", "Решение", "Дополнительно",
            "Автор", "Категория", "Статус", "Дата создания",
            "Кол-во файлов"
        ]
        ws.append(headers)
        
        # Данные
        for idea in ideas:
            ws.append([
                idea.id,
                idea.title,
                idea.essence,
                idea.solution,
                idea.description or "",
                idea.author_name or "",
                "Да" if idea.is_anonymous else "Нет",
                idea.category,
                idea.status_display(),
                idea.created_at.strftime('%d.%m.%Y %H:%M'),
                len(idea.attachments)
            ])
        
        # Оптимальные ширины столбцов (уменьшенные)
        column_widths = {
            'A': 6,   # ID
            'B': 20,  # Заголовок
            'C': 40,  # Проблема
            'D': 40,  # Решение
            'E': 40,  # Дополнительно
            'F': 15,  # Автор
            'H': 15,  # Категория
            'I': 15,  # Статус
            'J': 15,  # Дата создания
            'K': 10   # Кол-во файлов
        }
        
        # Устанавливаем ширины столбцов
        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width
        
        # Сохраняем в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Формируем имя файла
        filename = f"ideas_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        
        # Отправляем файл
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при экспорте идей: {str(e)}")
        flash('Произошла ошибка при формировании отчета', 'danger')
        return redirect(url_for('index'))


# Маршруты управления идеями (модератор)
@app.route('/idea/<int:id>/toggle_publish', methods=['POST'])
@moderator_required
def toggle_publish(id):
    """Переключение статуса публикации идеи."""
    try:
        idea = db.session.get(Idea, id) or abort(404)
        idea.is_published = request.json.get('is_published', False)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/edit_idea/<int:id>', methods=['GET', 'POST'])
@moderator_required
def edit_idea(id):
    """Редактирование идеи модератором."""
    idea = db.session.get(Idea, id) or abort(404)
    old_status = idea.status
    form = EditIdeaForm(obj=idea)
    
    if form.validate_on_submit():
        # Сохраняем текущее состояние is_published перед обновлением
        was_published = idea.is_published

        idea.moderator_feedback = form.moderator_feedback.data
        
        # Обновляем поля вручную
        idea.title = form.title.data.strip()
        idea.essence = form.essence.data
        idea.solution = form.solution.data
        idea.description = form.description.data
        idea.category = form.category.data
        idea.status = form.status.data
        
        # Восстанавливаем is_published
        idea.is_published = was_published
        
        db.session.commit()

        send_status_update_notification(idea, old_status, idea.status)
        
        flash('Изменения сохранены', 'success')
        return redirect(url_for('idea_detail', id=id))
    
    # Убедимся, что поля формы заполнены текущими значениями
    form.moderator_feedback.data = idea.moderator_feedback
    form.status.data = idea.status
    form.category.data = idea.category
    
    return render_template('edit_idea.html', form=form, idea=idea)


@app.route('/idea/<int:id>/approve', methods=['POST'])
@moderator_required
def approve_idea(id):
    """Одобрение идеи."""
    try:
        idea = db.session.get(Idea, id) or abort(404)
        old_status = idea.status
        idea.status = Idea.STATUS_APPROVED
        db.session.commit()

        # 🔔 Уведомление автору об изменении статуса
        send_status_update_notification(idea, old_status, idea.status)

        flash('Идея одобрена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при одобрении идеи: {str(e)}', 'danger')
    return redirect(url_for('idea_detail', id=id))


@app.route('/idea/<int:id>/partially_approve', methods=['POST'])
@moderator_required
def partially_approve_idea(id):
    """Частичное одобрение идеи."""
    try:
        idea = db.session.get(Idea, id) or abort(404)
        old_status = idea.status
        idea.status = Idea.STATUS_PARTIALLY_APPROVED
        db.session.commit()

        # 🔔 Уведомление автору об изменении статуса
        send_status_update_notification(idea, old_status, idea.status)

        flash('Идея одобрена частично', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при частичном одобрении идеи: {str(e)}', 'danger')
    return redirect(url_for('idea_detail', id=id))


@app.route('/idea/<int:id>/reject', methods=['POST'])
@moderator_required
def reject_idea(id):
    """Отклонение идеи."""
    try:
        idea = db.session.get(Idea, id) or abort(404)
        old_status = idea.status
        idea.status = Idea.STATUS_REJECTED
        db.session.commit()

        send_status_update_notification(idea, old_status, idea.status)

        flash('Идея отклонена', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при отклонении идеи: {str(e)}', 'danger')
    return redirect(url_for('idea_detail', id=id))


@app.route('/idea/<int:id>/delete', methods=['POST'])
@moderator_required
def delete_idea(id):
    """Удаление идеи."""
    try:
        idea = db.session.get(Idea, id) or abort(404)
        
        # Удаляем связанные файлы
        for attachment in idea.attachments:
            if os.path.exists(os.path.join(current_app.root_path, attachment.filepath)):
                try:
                    os.remove(os.path.join(current_app.root_path, attachment.filepath))
                except Exception as e:
                    flash(f'Ошибка при удалении файла: {str(e)}', 'warning')
        
        db.session.delete(idea)
        db.session.commit()
        flash('Идея и все связанные материалы удалены', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении идеи: {str(e)}', 'danger')
    return redirect(url_for('mod_dashboard'))


# Маршруты управления категориями
@app.route('/manage_categories')
@moderator_required
def manage_categories():
    """Управление категориями идей."""
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    categories = IdeaCategory.query.filter_by(is_active=True).order_by(IdeaCategory.name).all()
    add_form = CategoryForm()
    delete_form = DeleteCategoryForm()
    
    # Подсчитываем количество идей для каждой категории
    categories_with_counts = []
    for category in categories:
        ideas_count = Idea.query.filter_by(category=category.name).count()
        categories_with_counts.append({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'ideas_count': ideas_count
        })
    
    return render_template('manage_categories.html', 
                        categories=categories_with_counts,
                        add_form=add_form,
                        delete_form=delete_form)


@app.route('/add_category', methods=['POST'])
@moderator_required
def add_category():
    """Добавление новой категории."""
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            # Проверка на существующую категорию
            if IdeaCategory.query.filter(func.lower(IdeaCategory.name) == func.lower(form.name.data.strip())).first():
                flash('Категория с таким названием уже существует', 'danger')
            else:
                category = IdeaCategory(
                    name=form.name.data.strip(),
                    description=form.description.data.strip() if form.description.data else None
                )
                db.session.add(category)
                db.session.commit()
                flash('Категория успешно добавлена', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    else:
        # Собираем все ошибки валидации
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
                
    return redirect(url_for('manage_categories'))


@app.route('/edit_category/<int:id>', methods=['GET', 'POST'])
@moderator_required
def edit_category(id):
    """Редактирование категории."""
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    category = IdeaCategory.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    # Подсчитываем количество идей для этой категории
    ideas_count = Idea.query.filter_by(category=category.name).count()
    
    if form.validate_on_submit():
        try:
            # Проверяем, не меняем ли на существующее имя
            existing_category = IdeaCategory.query.filter(
                IdeaCategory.name == form.name.data.strip(),
                IdeaCategory.id != id
            ).first()
            
            if existing_category:
                flash('Категория с таким названием уже существует', 'danger')
            else:
                # Обновляем категорию
                old_name = category.name
                category.name = form.name.data.strip()
                category.description = form.description.data.strip() if form.description.data else None
                
                # Обновляем категорию у всех связанных идей
                if old_name != category.name:
                    ideas_to_update = Idea.query.filter_by(category=old_name).all()
                    for idea in ideas_to_update:
                        idea.category = category.name
                
                db.session.commit()
                flash('Категория успешно обновлена', 'success')
                return redirect(url_for('manage_categories'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении категории: {str(e)}', 'danger')
    
    return render_template('edit_category.html', 
                         form=form, 
                         category=category,
                         ideas_count=ideas_count)


@app.route('/delete_category/<int:id>', methods=['POST'])
@moderator_required
def delete_category(id):
    """Удаление категории."""
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    form = DeleteCategoryForm()
    if form.validate_on_submit():
        category = IdeaCategory.query.get_or_404(id)
        
        # Находим идеи в этой категории
        ideas_in_category = Idea.query.filter_by(category=category.name).all()
        
        try:
            # Ищем другую активную категорию для перемещения идей
            other_category = IdeaCategory.query.filter(
                IdeaCategory.id != id,
                IdeaCategory.is_active == True
            ).first()
            
            if other_category:
                new_category = other_category.name
                # Перемещаем категорию у всех идей в этой категории
                for idea in ideas_in_category:
                    idea.category = new_category
                
                # Удаляем саму категорию
                db.session.delete(category)
                db.session.commit()
                
                if ideas_in_category:
                    flash(f'Категория "{category.name}" удалена. {len(ideas_in_category)} идей перемещено в категорию "{new_category}".', 'success')
                else:
                    flash(f'Категория "{category.name}" успешно удалена', 'success')
            else:
                # Если это последняя категория и в ней есть идеи, нельзя удалить
                if ideas_in_category:
                    flash('Нельзя удалить последнюю категорию, в которой есть идеи. Сначала создайте новую категорию или удалите/переместите идеи.', 'danger')
                else:
                    # Если это последняя категория и она пустая - можно удалить
                    db.session.delete(category)
                    db.session.commit()
                    flash(f'Категория "{category.name}" успешно удалена', 'success')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении категории: {str(e)}', 'danger')
    else:
        flash('Неверный запрос на удаление', 'danger')
        
    return redirect(url_for('manage_categories'))


# Точка входа
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_moderators()
        init_categories()
    app.run(debug=True)