import os
from dotenv import load_dotenv

load_dotenv()

# SMTP настройки
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.yandex.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
FROM_EMAIL = os.getenv('FROM_EMAIL', 'rost3st@yandex.ru')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
MODERATOR_EMAIL = os.getenv('MODERATOR_EMAIL', 'mod-ideabox@rtmsk.ru')


# # Новые настройки для проекта
# PROJECT_EMAIL = os.getenv('PROJECT_EMAIL', 'moder-ideabox@rtmsk.ru')
# PROJECT_NAME = os.getenv('PROJECT_NAME', 'Лаборатория идей РОСТЕСТ')