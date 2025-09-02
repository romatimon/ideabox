from extensions import db
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app


class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)  # Убрали nullable=False
    attachments = db.relationship('Attachment', backref='idea', cascade='all, delete-orphan')
    author_name = db.Column(db.String(50))
    contact_email = db.Column(db.String(120))  # Новое поле для email
    is_anonymous = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default='Общее', nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    cost = db.Column(db.String(20))  # 'дорого' или 'бесплатно'
    complexity = db.Column(db.String(20))  # 'сложно' или 'просто'
    duration = db.Column(db.String(20))  # 'долго' или 'быстро'
    is_published = db.Column(db.Boolean, default=False)
    moderator_feedback = db.Column(db.Text)  # Обратная связь от модератора

    # Константы статусов
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_IMPLEMENTED = 'implemented'
    STATUS_ARCHIVED = 'archived'

    # Поле статуса
    status = db.Column(db.String(20), default=STATUS_DRAFT, nullable=False)
    
    def status_display(self):
        status_map = {
            self.STATUS_DRAFT: 'Черновик',
            self.STATUS_PENDING: 'На рассмотрении',
            self.STATUS_APPROVED: 'Одобрено',
            self.STATUS_REJECTED: 'Отклонено',
            self.STATUS_IN_PROGRESS: 'В работе',
            self.STATUS_IMPLEMENTED: 'Реализовано',
            self.STATUS_ARCHIVED: 'В архиве'
        }
        return status_map.get(self.status, self.status)


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)
    
    @property
    def file_size(self):
        try:
            full_path = os.path.join(current_app.root_path, self.filepath)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            # Форматируем размер для удобного отображения
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} GB"
        except OSError:
            return "0 B"

class Moderator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_super_moderator = db.Column(db.Boolean, default=False)
    can_manage_categories = db.Column(db.Boolean, default=False)  # Новое поле

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)  # Хэшируем пароль

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)  # Проверяем пароль

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class IdeaStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_ideas = db.Column(db.Integer, default=0)
    approved_ideas = db.Column(db.Integer, default=0)
    pending_ideas = db.Column(db.Integer, default=0)
    rejected_ideas = db.Column(db.Integer, default=0)


class IdeaCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())