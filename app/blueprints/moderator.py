from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app, jsonify, send_file, session
from functools import wraps
from io import BytesIO
import os
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from datetime import datetime
from sqlalchemy import func

from app.extensions import db
from app.forms import CategoryForm, DeleteCategoryForm, EditCategoryForm, EditIdeaForm
from app.models import Attachment, Idea, IdeaCategory, Moderator
from app.notifications import send_status_update_notification
from .auth import moderator_required

moderator_bp = Blueprint("moderator", __name__, url_prefix="/moderator")


# Маршруты модератора
@moderator_bp.route('/dashboard')
@moderator_required
def dashboard():
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
    
    return render_template('dashboard.html', 
                         ideas=ideas,
                         pagination=pagination,
                         categories=categories,
                         sort_field=sort_field,
                         sort_direction=sort_direction)
                         


@moderator_bp.route('/stats')
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


@moderator_bp.route('/export-ideas')
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
        return redirect(url_for('public.index'))


# Маршруты управления идеями (модератор)
@moderator_bp.route('/idea/<int:id>/toggle_publish', methods=['POST'])
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


@moderator_bp.route('/edit_idea/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('public.idea_detail', id=id))
    
    # Убедимся, что поля формы заполнены текущими значениями
    form.moderator_feedback.data = idea.moderator_feedback
    form.status.data = idea.status
    form.category.data = idea.category
    
    return render_template('edit_idea.html', form=form, idea=idea)


@moderator_bp.route('/idea/<int:id>/approve', methods=['POST'])
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
    return redirect(url_for('public.idea_detail', id=id))


@moderator_bp.route('/idea/<int:id>/partially_approve', methods=['POST'])
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
    return redirect(url_for('public.idea_detail', id=id))


@moderator_bp.route('/idea/<int:id>/reject', methods=['POST'])
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
    return redirect(url_for('public.idea_detail', id=id))


@moderator_bp.route('/idea/<int:id>/delete', methods=['POST'])
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
    return redirect(url_for('moderator.dashboard'))


# Маршруты управления категориями
@moderator_bp.route('/manage_categories')
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


@moderator_bp.route('/add_category', methods=['POST'])
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
                
    return redirect(url_for('moderator.manage_categories'))


@moderator_bp.route('/edit_category/<int:id>', methods=['GET', 'POST'])
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
                return redirect(url_for('moderator.manage_categories'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении категории: {str(e)}', 'danger')
    
    return render_template('edit_category.html', 
                         form=form, 
                         category=category,
                         ideas_count=ideas_count)


@moderator_bp.route('/delete_category/<int:id>', methods=['POST'])
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
        
    return redirect(url_for('moderator.manage_categories'))
