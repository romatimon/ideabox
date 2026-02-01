import os
from flask import Flask
from dotenv import load_dotenv
from config import config
from .extensions import csrf, db
from .template_utils import register_template_utils

# Импорт Blueprints
from .blueprints.public import public_bp
from .blueprints.auth import auth_bp
from .blueprints.ideas import ideas_bp
from .blueprints.moderator import moderator_bp


def create_app(config_name='default'):
    """
    Фабрика приложений Flask.
    """

    # Создаем экземпляр приложения Flask
    app = Flask(__name__)
    
    # Загружаем переменные среды
    load_dotenv()

    # Настраиваем приложение через словарь конфигурации
    app.config.from_object(config[config_name])

    # Регистрируем дополнительные расширения Flask (ORM, защита от атак)
    db.init_app(app)
    csrf.init_app(app)
    
    # Регистрируем маршруты (блупринты)
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ideas_bp)
    app.register_blueprint(moderator_bp)

    # Регистрация контекстных процессоров и фильтров
    register_template_utils(app)
    
    # Возвращаем сконфигурированное приложение
    return app