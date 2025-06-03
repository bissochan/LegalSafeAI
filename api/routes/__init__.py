# api/routes/__init__.py
from .auth_routes import auth_bp
from .chat_routes import chat_bp
from .document_routes import document_bp
from .shadow_routes import shadow_bp
from .summary_routes import summary_bp
from .evaluator_routes import evaluator_bp
from .translator_routes import translator_bp
from .web_search_routes import web_search_bp