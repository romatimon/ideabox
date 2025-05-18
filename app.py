from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
import os
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy import event
from sqlalchemy.engine import Engine
from forms import IdeaForm, CommentForm, ModeratorLoginForm
from models import Idea, Comment, Moderator, Attachment, ExportLog
from extensions import db
from functools import wraps
from sqlalchemy import select
from openpyxl import Workbook
from io import BytesIO
from flask import send_file
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ideas.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
db.init_app(app)

app.jinja_env.filters['filesizeformat'] = lambda value: value

# Создаем папку для загрузок, если ее нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Конфигурация загрузки файлов
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

@event.listens_for(Engine, "connect")
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
        {'username': 'moderator1', 'first_name': 'Ольга', 'last_name': 'Власюк', 'password': 'moder123'},
        {'username': 'moderator2', 'first_name': 'Ольга', 'last_name': 'Шкляр', 'password': 'moder456'},
        {'username': 'moderator3', 'first_name': 'Анастасия', 'last_name': 'Щеколдина', 'password': 'moder789'}
    ]
    
    for mod in moderators:
        if not db.session.execute(
            db.select(Moderator).where(Moderator.username == mod['username'])
        ).scalar_one_or_none():
            moderator = Moderator(
                username=mod['username'],
                first_name=mod['first_name'],
                last_name=mod['last_name']
            )
            moderator.set_password(mod['password'])
            db.session.add(moderator)
    db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    form = IdeaForm()
    if form.validate_on_submit():
        try:
            idea = Idea(
                title=form.title.data.strip(),
                problem=form.problem.data.strip(),
                solution=form.solution.data.strip(),
                expected_result=form.expected_result.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                author_name=form.author_name.data.strip() if form.author_name.data else None,
                is_anonymous=not bool(form.author_name.data),
                category=form.category.data,
                status='На рассмотрении'
            )
            db.session.add(idea)
            db.session.commit()
            flash('Идея отправлена на модерацию!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении идеи: {str(e)}', 'danger')
    
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'newest')
    
    query = Idea.query
    if status_filter != 'all':
        query = query.filter(Idea.status == status_filter)
    if category_filter != 'all':
        query = query.filter(Idea.category == category_filter)
    query = query.order_by(Idea.created_at.desc() if sort_by == 'newest' else Idea.created_at.asc())
    
    ideas = query.all()
    return render_template('index.html', form=form, ideas=ideas,
                         current_status=status_filter, current_category=category_filter, current_sort=sort_by)

@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    form = IdeaForm()
    if form.validate_on_submit():
        try:
            idea = Idea(
                title=form.title.data.strip(),
                problem=form.problem.data.strip(),
                solution=form.solution.data.strip(),
                expected_result=form.expected_result.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                author_name=form.author_name.data.strip() if form.author_name.data else None,
                contact_email=form.contact_email.data.strip() if form.contact_email.data else None,
                is_anonymous=not bool(form.author_name.data),
                category=form.category.data,
                status='На рассмотрении'
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

@app.route('/idea/<int:id>', methods=['GET', 'POST'])
def idea_detail(id):
    idea = db.session.get(Idea, id) or abort(404)
    form = CommentForm()
    current_moderator = None
    
    if 'moderator_id' in session:
        current_moderator = db.session.get(Moderator, session['moderator_id'])
    
    # Обработка комментариев только для модераторов
    if form.validate_on_submit():
        if not current_moderator:
            abort(403)  # Запрещаем доступ для не-модераторов
        
        try:
            comment = Comment(
                text=form.text.data.strip(),
                author_name=current_moderator.full_name,
                is_anonymous=False,
                idea_id=id
            )
            db.session.add(comment)
            db.session.commit()
            flash('Комментарий добавлен', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении комментария: {str(e)}', 'danger')
        return redirect(url_for('idea_detail', id=id))
    
    # Загрузка комментариев только для модераторов
    comments = []
    if current_moderator:
        comments = db.session.execute(
            select(Comment)
            .where(Comment.idea_id == id)
            .order_by(Comment.created_at.desc())
        ).scalars().all()
    
    return render_template(
        'idea_detail.html', 
        idea=idea,
        form=form,
        comments=comments,
        current_moderator=current_moderator
    )

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
        idea.status = 'Одобрено'
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
        idea.status = 'Отклонено'
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
    return redirect(url_for('index'))


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
            "Ожидаемый результат", "Описание", "Автор", 
            "Анонимно", "Категория", "Статус", "Дата создания",
            "Кол-во файлов", "Кол-во комментариев"
        ]
        ws.append(headers)
        
        # Данные
        for idea in ideas:
            ws.append([
                idea.id,
                idea.title,
                idea.problem,
                idea.solution,
                idea.expected_result,
                idea.description or "",
                idea.author_name or "",
                "Да" if idea.is_anonymous else "Нет",
                idea.category,
                idea.status,
                idea.created_at.strftime('%d.%m.%Y %H:%M'),
                len(idea.attachments),
                len(idea.comments)
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
        
        # Логируем действие
        if 'moderator_id' in session:
            log = ExportLog(
                moderator_id=session['moderator_id'],
                params=f"status={status}&category={category}"
            )
            db.session.add(log)
            db.session.commit()
        
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_moderators()
    app.run(debug=True)