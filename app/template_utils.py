import os
from flask import session
from .models import Moderator
from .extensions import db


def register_template_utils(app):
    """Регистрация контекстных процессоров и фильтров Jinja2."""
    
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        """Преобразует переносы строк в HTML теги <br>."""
        if not value:
            return ''
        value = str(value)
        value = value.replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')
        return value
    
    @app.context_processor
    def utility_processor():
        def filesizeformat(value):
            """Форматирует размер файла в удобочитаемый вид."""
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