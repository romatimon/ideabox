from .extensions import db
from .models import IdeaCategory, Moderator
import os


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
    print("Модераторы инициализированы")

def init_categories():
    """Инициализирует базовые категории идей."""
    default_categories = []  # Пустой список
    
    for cat in default_categories:
        if not IdeaCategory.query.filter_by(name=cat['name']).first():
            category = IdeaCategory(
                name=cat['name'],
                description=cat['description']
            )
            db.session.add(category)
    db.session.commit()
    print("Категории инициализированы")

def init_database():
    """Полная инициализация базы данных."""
    print("Инициализация базы данных...")
    
    # Создаем таблицы
    db.create_all()
    
    # Инициализируем данные
    init_moderators()
    init_categories()
    
    print("Инициализация базы данных завершена")