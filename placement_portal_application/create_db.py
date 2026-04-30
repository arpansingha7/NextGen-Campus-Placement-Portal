import os
from flask import Flask
from models import db, User

def create_db():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        # creates all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # predefine admin acording to the requirements
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        if not User.query.filter_by(role='admin').first():
            admin_user = User(
                email='admin@institute.edu',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin',
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Pre-defined Admin user created.")

if __name__ == "__main__":
    create_db()
