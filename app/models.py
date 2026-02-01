import os
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db


class Idea(db.Model):
    """Модель идеи/предложения."""
    
    # Константы статусов
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_PARTIALLY_APPROVED = 'partially_approved'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_IMPLEMENTED = 'implemented'
    STATUS_REJECTED = 'rejected'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    essence = db.Column(db.Text, nullable=False)  # Суть проблемы
    solution = db.Column(db.Text, nullable=False)  # Предлагаемое решение
    description = db.Column(db.Text)  # Дополнительное описание
    author_name = db.Column(db.String(50))  # Имя автора
    contact_email = db.Column(db.String(120))  # Email для связи
    is_anonymous = db.Column(db.Boolean, default=False)  # Анонимная публикация
    category = db.Column(db.String(50), default='Общее', nullable=False)  # Категория
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # Дата создания
    is_published = db.Column(db.Boolean, default=False)  # Опубликована ли идея
    moderator_feedback = db.Column(db.Text)  # Обратная связь от модератора
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)  # Статус идеи
    
    # Связи
    attachments = db.relationship(
        'Attachment', 
        backref='idea', 
        cascade='all, delete-orphan',
        lazy=True
    )
    
    def status_display(self):
        status_map = {
            self.STATUS_PENDING: 'На рассмотрении',
            self.STATUS_APPROVED: 'Одобрено',
            self.STATUS_PARTIALLY_APPROVED: 'Одобрено (частично)',
            self.STATUS_IN_PROGRESS: 'На реализации',
            self.STATUS_IMPLEMENTED: 'Реализовано',
            self.STATUS_REJECTED: 'Отклонено'
        }
        return status_map.get(self.status, self.status)
    
    def __repr__(self):
        return f'<Idea {self.id}: {self.title}>'


class Attachment(db.Model):
    """Модель прикрепленного файла."""
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)  # Имя файла
    filepath = db.Column(db.String(255), nullable=False)  # Путь к файлу
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)  # Ссылка на идею
    
    @property
    def file_size(self):
        """Возвращает размер файла в удобном формате."""
        try:
            full_path = os.path.join(current_app.root_path, self.filepath)
            if not os.path.exists(full_path):
                return "0 B"
                
            size = os.path.getsize(full_path)
            
            # Форматируем размер для удобного отображения
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} GB"
        except OSError:
            return "0 B"
    
    def __repr__(self):
        return f'<Attachment {self.id}: {self.filename}>'


class Moderator(db.Model):
    """Модель модератора."""
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # Логин
    password_hash = db.Column(db.String(128), nullable=False)  # Хэш пароля
    first_name = db.Column(db.String(50), nullable=False)  # Имя
    last_name = db.Column(db.String(50), nullable=False)  # Фамилия
    is_super_moderator = db.Column(db.Boolean, default=False)  # Супер-модератор
    can_manage_categories = db.Column(db.Boolean, default=False)  # Может управлять категориями
    
    def set_password(self, password):
        """Устанавливает хэш пароля."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверяет пароль."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Возвращает полное имя модератора."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Moderator {self.id}: {self.username}>'


class IdeaCategory(db.Model):
    """Модель категории идей."""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Название категории
    description = db.Column(db.String(100))  # Описание категории
    is_active = db.Column(db.Boolean, default=True)  # Активна ли категория
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # Дата создания
    
    def __repr__(self):
        return f'<IdeaCategory {self.id}: {self.name}>'