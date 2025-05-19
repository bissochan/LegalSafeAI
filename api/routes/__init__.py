from .document_routes import document_bp
from .shadow_routes import shadow_bp
from .summary_routes import summary_bp
from .evaluator_routes import evaluator_bp
from .chat_routes import chat_bp

__all__ = [
    'document_bp',
    'shadow_bp',
    'summary_bp',
    'evaluator_bp',
    'chat_bp'
]