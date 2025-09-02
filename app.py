from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy.engine import Engine
from forms import IdeaForm, ModeratorLoginForm, EditIdeaForm, CategoryForm, DeleteCategoryForm
from models import Idea, Moderator, Attachment, IdeaStats, IdeaCategory
from extensions import db
from functools import wraps
from sqlalchemy import select
from openpyxl import Workbook
from io import BytesIO
from flask import send_file
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy import func
from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ideas.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

app.config['WTF_CSRF_ENABLED'] = True
csrf = CSRFProtect(app)
db.init_app(app)

@app.context_processor
def utility_processor():
    return dict(os=os)

app.jinja_env.filters['filesizeformat'] = lambda value: value

# Создаем папку для загрузок, если ее нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Конфигурация загрузки файлов
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def moderator_required(f):
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

@app.context_processor
def inject_moderator():
    if 'moderator_id' in session:
        moderator = db.session.get(Moderator, session['moderator_id'])
        return {'current_moderator': moderator}
    return {}


def init_moderators():
    moderators = [
        {
            'username': 'vlasuk', 
            'first_name': 'Ольга', 
            'last_name': 'Власюк',
            'password': 'super123',
            'can_manage_categories': True
        },
        {
            'username': 'schekoldina', 
            'first_name': 'Анастасия', 
            'last_name': 'Щеколдина',
            'password': 'super456',
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


@app.route('/manage_categories')
@moderator_required
def manage_categories():
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    categories = IdeaCategory.query.filter_by(is_active=True).order_by(IdeaCategory.name).all()
    add_form = CategoryForm()
    delete_form = DeleteCategoryForm()
    
    return render_template('manage_categories.html', 
                        categories=categories,
                        add_form=add_form,
                        delete_form=delete_form)

from sqlalchemy.exc import IntegrityError


from sqlalchemy.exc import IntegrityError

@app.route('/add_category', methods=['POST'])
@moderator_required
def add_category():
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
        except IntegrityError:
            db.session.rollback()
            flash('Ошибка базы данных при добавлении категории', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    else:
        # Собираем все ошибки валидации
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
                
    return redirect(url_for('manage_categories'))


@app.route('/delete_category/<int:id>', methods=['POST'])
@moderator_required
def delete_category(id):
    moderator = db.session.get(Moderator, session['moderator_id'])
    if not moderator.can_manage_categories:
        abort(403)
        
    form = DeleteCategoryForm()
    if form.validate_on_submit():
        category = IdeaCategory.query.get_or_404(id)
        try:
            category.is_active = False
            db.session.commit()
            flash(f'Категория "{category.name}" успешно удалена', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении категории: {str(e)}', 'danger')
    else:
        flash('Неверный запрос на удаление', 'danger')
        
    return redirect(url_for('manage_categories'))


@app.route('/mod_dashboard')
@moderator_required
def mod_dashboard():
    # Получаем параметры фильтрации и сортировки
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
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
    
    # Получаем данные за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    stats_data = IdeaStats.query.filter(IdeaStats.date >= thirty_days_ago.date()).order_by(IdeaStats.date).all()
    
    # Подготавливаем данные для графика
    dates = [stat.date.strftime('%d.%m') for stat in stats_data]
    total = [stat.total_ideas for stat in stats_data]
    approved = [stat.approved_ideas for stat in stats_data]
    pending = [stat.pending_ideas for stat in stats_data]
    rejected = [stat.rejected_ideas for stat in stats_data]
    
    # Категориальная статистика
    categories = ['Общее', 'Процессы', 'Клиенты', 'Обучение', 'Маркетинг', 'Культура']
    category_counts = [Idea.query.filter_by(category=cat).count() for cat in categories]
    
    # Получаем общее количество идей
    total_ideas = Idea.query.count()
    approved_ideas = Idea.query.filter_by(status='Одобрено').count()
    pending_ideas = Idea.query.filter_by(status='На рассмотрении').count()
    rejected_ideas = Idea.query.filter_by(status='Отклонено').count()
    
    return render_template('stats.html', 
                         dates=dates,
                         total=total,
                         approved=approved,
                         pending=pending,
                         rejected=rejected,
                         categories=categories,
                         category_counts=category_counts,
                         total_ideas=total_ideas,
                         approved_ideas=approved_ideas,
                         pending_ideas=pending_ideas,
                         rejected_ideas=rejected_ideas)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Количество идей на странице

    # Получаем параметры фильтрации
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    search_query = request.args.get('search', '')  # Для поиска
    sort_by = request.args.get('sort', 'newest')

    if session.get('moderator_id'):
        # Для модераторов показываем все идеи
        query = Idea.query
    else:
        # Для обычных пользователей показываем только опубликованные идеи
        query = Idea.query.filter_by(is_published=True)

    # Фильтрация по статусу
    if status_filter != 'all':
        query = query.filter(Idea.status == status_filter)

    # Фильтрация по категории
    if category_filter != 'all':
        query = query.filter(Idea.category == category_filter)

    # Поиск (если реализован)
    if search_query:
        query = query.filter(or_(
            Idea.title.ilike(f'%{search_query}%'),
            Idea.problem.ilike(f'%{search_query}%'),
            Idea.solution.ilike(f'%{search_query}%'),
            Idea.description.ilike(f'%{search_query}%')
        ))

    # Сортировка
    if sort_by == 'newest':
        query = query.order_by(Idea.created_at.desc())
    else:
        query = query.order_by(Idea.created_at.asc())

    # Пагинация
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    ideas = pagination.items

    return render_template('index.html', 
                         ideas=ideas,
                         pagination=pagination,
                         current_status=status_filter,
                         current_category=category_filter,
                         current_sort=sort_by,
                         search_query=search_query)

@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    form = IdeaForm()
    if form.validate_on_submit():
        try:
            idea = Idea(
                title=form.title.data.strip(),
                problem=form.problem.data.strip(),
                solution=form.solution.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                author_name=form.author_name.data.strip() if form.author_name.data else None,
                contact_email=form.contact_email.data.strip() if form.contact_email.data else None,
                is_anonymous=False,  # Больше не используем анонимность
                category=form.category.data,
                status=Idea.STATUS_DRAFT
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
            flash('Идея успешно отправлена на модерацию!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении идеи: {str(e)}', 'danger')
    
    return render_template('add_idea.html', form=form)


@app.route('/idea/<int:id>/toggle_publish', methods=['POST'])
@moderator_required
def toggle_publish(id):
    try:
        idea = db.session.get(Idea, id) or abort(404)
        idea.is_published = request.json.get('is_published', False)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<int:id>')
def download_attachment(id):
    attachment = Attachment.query.get_or_404(id)
    if not os.path.exists(os.path.join(current_app.root_path, attachment.filepath)):
        abort(404)
    return send_from_directory(
        os.path.dirname(os.path.join(current_app.root_path, attachment.filepath)),
        os.path.basename(attachment.filepath),
        as_attachment=True
    )

@app.route('/idea/<int:id>')
def idea_detail(id):
    idea = db.session.get(Idea, id) or abort(404)
    
    # Проверка публикации для обычных пользователей
    if not session.get('moderator_id') and not idea.is_published:
        abort(403)  # Доступ запрещен
    
    current_moderator = None
    if 'moderator_id' in session:
        current_moderator = db.session.get(Moderator, session['moderator_id'])
    
    return render_template(
        'idea_detail.html', 
        idea=idea,
        current_moderator=current_moderator
    )

@app.route('/edit_idea/<int:id>', methods=['GET', 'POST'])
@moderator_required
def edit_idea(id):
    idea = db.session.get(Idea, id) or abort(404)
    form = EditIdeaForm(obj=idea)
    
    if form.validate_on_submit():
        # Сохраняем текущее состояние is_published перед populate_obj
        was_published = idea.is_published

        idea.moderator_feedback = form.moderator_feedback.data
        
        # Обновляем только нужные поля вручную
        idea.title = form.title.data
        idea.problem = form.problem.data
        idea.solution = form.solution.data
        idea.description = form.description.data
        idea.status = form.status.data
        
        # Восстанавливаем is_published
        idea.is_published = was_published
        
        # Обновляем дополнительные оценки
        idea.cost = form.cost.data
        idea.complexity = form.complexity.data
        idea.duration = form.duration.data
        
        db.session.commit()
        flash('Изменения сохранены', 'success')
        return redirect(url_for('idea_detail', id=id))
    
    # Убедимся, что поля формы заполнены текущими значениями
    form.moderator_feedback.data = idea.moderator_feedback
    form.cost.data = idea.cost
    form.complexity.data = idea.complexity
    form.duration.data = idea.duration
    form.status.data = idea.status
    
    return render_template('edit_idea.html', form=form, idea=idea)


@app.route('/moderator/login', methods=['GET', 'POST'])
def moderator_login():
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
    session.pop('moderator_id', None)
    flash('Вы вышли из режима модератора', 'info')
    return redirect(url_for('index'))


@app.route('/idea/<int:id>/approve', methods=['POST'])
@moderator_required
def approve_idea(id):
    try:
        idea = db.session.get(Idea, id) or abort(404)
        idea.status = Idea.STATUS_APPROVED
        db.session.commit()
        flash('Идея одобрена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при одобрении идеи: {str(e)}', 'danger')
    return redirect(url_for('idea_detail', id=id))


@app.route('/idea/<int:id>/reject', methods=['POST'])
@moderator_required
def reject_idea(id):
    try:
        idea = db.session.get(Idea, id) or abort(404)
        idea.status = Idea.STATUS_REJECTED
        db.session.commit()
        flash('Идея отклонена', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при отклонении идеи: {str(e)}', 'danger')
    return redirect(url_for('idea_detail', id=id))


@app.route('/idea/<int:id>/delete', methods=['POST'])
@moderator_required
def delete_idea(id):
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


@app.route('/export-ideas')
@moderator_required
def export_ideas():
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
            "ID", "Заголовок", "Проблема", "Решение", 
            "Описание", "Автор", 
            "Анонимно", "Категория", "Статус", "Дата создания",
            "Кол-во файлов"
        ]
        ws.append(headers)
        
        # Данные
        for idea in ideas:
            ws.append([
                idea.id,
                idea.title,
                idea.problem,
                idea.solution,
                idea.description or "",
                idea.author_name or "",
                "Да" if idea.is_anonymous else "Нет",
                idea.category,
                idea.status,
                idea.created_at.strftime('%d.%m.%Y %H:%M'),
                len(idea.attachments)
            ])
        
        # Автоподбор ширины столбцов
        for col in ws.columns:
            max_length = 0
            for cell in col:
                try:
                    max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[col[0].column_letter].width = adjusted_width
        
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


def init_categories():
    default_categories = [
        {'name': 'Общее', 'description': 'Общие идеи и предложения'},
    ]
    
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_moderators()
        init_categories()
    app.run(debug=True)