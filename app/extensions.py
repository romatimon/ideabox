from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Расширения базы данных и защита CSRF (подделка межсетевых запросов)
db = SQLAlchemy() 
csrf = CSRFProtect()