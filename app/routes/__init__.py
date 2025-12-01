from app.routes.api import api_bp
from app.routes.admin import admin_bp
from app.routes.user import user_bp
from app.routes.chat import chat_bp

__all__ = ['api_bp', 'admin_bp', 'user_bp', 'chat_bp']