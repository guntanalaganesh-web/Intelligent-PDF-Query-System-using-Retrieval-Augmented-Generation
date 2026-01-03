"""API module initialization."""
from app.api.routes import api_bp
from app.api.health import health_bp

__all__ = ['api_bp', 'health_bp']
