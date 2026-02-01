from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app, jsonify, send_file, send_from_directory
from functools import wraps
from io import BytesIO
import os
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms import IdeaForm
from app.models import Attachment, Idea, IdeaCategory
from app.notifications import send_new_idea_notification, send_author_confirmation, send_status_update_notification

from config import Config


# Конфигурация
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}


# Создаем папку для загрузок
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Вспомогательные функции
def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ideas_bp = Blueprint("ideas", __name__)


@ideas_bp.route('/add_idea', methods=['GET', 'POST'])
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
                        
                        UPLOAD_FOLDER = 'uploads' 
                        filepath = os.path.join(UPLOAD_FOLDER, f"{idea.id}_{filename}")
                        
                        # Сохраняем файл (папка уже создана run.py)
                        file.save(filepath)
                        
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
            return redirect(url_for('public.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении идеи: {str(e)}', 'danger')
    
    return render_template('add_idea.html', form=form)


# Маршруты для работы с файлами
@ideas_bp.route('/download/<int:id>')
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