import os
from app import create_app
from app.init_data import init_database


# Создание приложения
app = create_app('default') # 'default' = 'development' из config.py

if __name__ == "__main__":
    # Создаем папку для загрузок
    uploads_dir = 'uploads'
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"Создана папка {uploads_dir}")
    
    # Инициализируем базу данных
    with app.app_context():
        try:
            init_database()
        except Exception as e:
            print(f"Ошибка при инициализации БД: {e}")
    
    # Запускаем приложение
    app.run(debug=True, host='0.0.0.0', port=5000)