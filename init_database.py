from app import app, db

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")
    
    print("Initializing moderators...")
    from app import init_moderators, init_categories
    init_moderators()
    print("Moderators initialized!")
    
    print("Initializing categories...")
    init_categories()
    print("Categories initialized!")
    
    print("Database initialization completed!")