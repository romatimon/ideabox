from flask import Blueprint, render_template, request, abort, session
from app.models import Idea, IdeaCategory, Moderator
from app.extensions import db
from sqlalchemy import or_


# Объявляем блупринт 
public_bp = Blueprint("public", __name__)


@public_bp.route('/')
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


@public_bp.route('/idea/<int:id>')
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