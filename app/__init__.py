from flask import Flask, session as flask_session
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.config import Config

mongo_client = None
db = None


def get_db():
    global db
    return db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    # Initialize MongoDB
    global mongo_client, db

    mongodb_uri = app.config.get('MONGODB_URI', 'mongodb://localhost:27017')
    mongodb_db = app.config.get('MONGODB_DB', 'badminton_tracker')

    try:
        mongo_client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        mongo_client.admin.command('ping')
        db = mongo_client[mongodb_db]
        print(f"[App] ✅ MongoDB connected: {mongodb_db}")
    except ConnectionFailure as e:
        print(f"[App] ❌ MongoDB connection failed: {e}")
        raise
    except Exception as e:
        print(f"[App] ❌ Error: {e}")
        raise

    # Ensure default data exists
    with app.app_context():
        from app.models.user import User
        from app.models.settings import Settings

        User.ensure_admin_exists()
        Settings.ensure_defaults_exist()

    # Register blueprints
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.user import user_bp
    from app.routes.chat import chat_bp

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/')
    app.register_blueprint(chat_bp, url_prefix='/chat')

    # Context processor để inject biến vào tất cả templates
    @app.context_processor
    def inject_globals():
        return {
            'admin_username': flask_session.get('admin_username', 'Admin'),
            'admin_logged_in': flask_session.get('admin_logged_in', False)
        }

    # Template filters
    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return "0đ"
        return f"{int(value):,}đ".replace(",", ".")

    @app.template_filter('format_date')
    def format_date(value):
        if value is None:
            return ""
        return value.strftime("%d/%m/%Y")

    @app.template_filter('format_datetime')
    def format_datetime(value):
        if value is None:
            return ""
        return value.strftime("%d/%m/%Y %H:%M")

    return app