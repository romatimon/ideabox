import os
from dotenv import load_dotenv


load_dotenv() # Загружаем переменные из .env


class Config:
    """Базовая конфигурация приложения"""

    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY')
    WTF_CSRF_ENABLED = True # Глобальная защита от CSRF

    # База данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Отключаем дополонительное отслеживание изменений бд

    # Загрузка файлов
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Настройки почты
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT'))
    FROM_EMAIL = os.environ.get('FROM_EMAIL')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    MODERATOR_EMAIL = os.environ.get('MODERATOR_EMAIL')

    # Пароли модераторов (для инициализации)
    MODERATOR_VLASUK_PWD = os.environ.get('MODERATOR_VLASUK_PWD')
    MODERATOR_SCHEKOLDINA_PWD = os.environ.get('MODERATOR_SCHEKOLDINA_PWD')


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True # Режим отдалки

    # Можно переопределить URI для разработки
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev_ideas.db'


# В production используем другой путь к БД
class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False

# Дополнительные настройки безопасности для продакшена
    SESSION_COOKIE_SECURE = True # Браузер отправляет cookie файла сеанса только через защищённое HTTPS соединение
    SESSION_COOKIE_HTTPONLY = True # Браузер не разрешает JavaScript доступ к файлам cookie
    REMEMBER_COOKIE_SECURE =True # Браузеру разрешается отправлять cookie для сохранения сессии только через зашифрованное HTTPS-соединение

    SQLALCHEMY_DATABASE_URI = 'sqlite:////app/data/ideas.db'


# Словарь для удобного выбора конфигурации
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig  # по умолчанию используем development
}