# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем зависимости для работы с SQLite и другими библиотеками
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем папку для загрузок
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Указываем порт
EXPOSE 5000

# Команда для запуска приложения
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]