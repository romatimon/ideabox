from flask import Blueprint, render_template, redirect, url_for, session, flash
from functools import wraps
from sqlalchemy import select
from app.extensions import db
from app.forms import ModeratorLoginForm
from app.models import Moderator

auth_bp = Blueprint("auth", __name__, url_prefix="/moderator")

def moderator_required(f):
    """Декоратор для проверки авторизации модератора."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('moderator_id'):
            flash('Требуется авторизация модератора', 'warning')
            return redirect(url_for('auth.login'))
            
        moderator = db.session.get(Moderator, session['moderator_id'])
        if not moderator:
            session.pop('moderator_id', None)
            flash('Сессия устарела, войдите снова', 'warning')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа для модераторов."""
    if session.get('moderator_id'):
        return redirect(url_for('public.index'))
        
    form = ModeratorLoginForm()
    if form.validate_on_submit():
        moderator = db.session.execute(
            select(Moderator).where(Moderator.username == form.username.data)
        ).scalar_one_or_none()
        if moderator and moderator.check_password(form.password.data):
            session['moderator_id'] = moderator.id
            flash(f'Добро пожаловать, {moderator.full_name}!', 'success')
            return redirect(url_for('public.index'))
        flash('Неверные учетные данные', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    """Выход из системы модератора."""
    session.pop('moderator_id', None)
    flash('Вы вышли из режима модератора', 'info')
    return redirect(url_for('public.index'))