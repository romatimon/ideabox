from extensions import db
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory, current_app

class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    expected_result = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)  # Убрали nullable=False
    attachments = db.relationship('Attachment', backref='idea', cascade='all, delete-orphan')
    author_name = db.Column(db.String(50))
    contact_email = db.Column(db.String(120))  # Новое поле для email
    is_anonymous = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default='Общее')
    status = db.Column(db.String(20), default='На рассмотрении')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    comments = db.relationship('Comment', backref='idea', cascade='all, delete-orphan', passive_deletes=True)

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id'), nullable=False)

    def delete_file(self):
        try:
            os.remove(os.path.join(current_app.root_path, self.filepath))
            return True
        except Exception:
            return False
        
    @property
    def file_size(self):
        full_path = os.path.join(current_app.root_path, self.filepath)
        if os.path.exists(full_path):
            try:
                return os.path.getsize(full_path)
            except OSError:
                return 0
        return 0

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(50))
    is_anonymous = db.Column(db.Boolean, default=False)
    idea_id = db.Column(db.Integer, db.ForeignKey('idea.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Moderator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    

class ExportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('moderator.id'), nullable=False)
    exported_at = db.Column(db.DateTime, server_default=db.func.now())
    params = db.Column(db.String(200))
    
    moderator = db.relationship('Moderator', backref='export_logs')