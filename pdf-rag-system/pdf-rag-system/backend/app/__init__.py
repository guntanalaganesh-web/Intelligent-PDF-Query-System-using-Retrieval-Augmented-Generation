"""
Intelligent PDF Query System - Flask Backend
RAG-based document intelligence with OpenAI GPT-3.5 Turbo
"""

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os

db = SQLAlchemy()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per hour"])

def create_app(config_name=None):
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'app.core.config.{config_name.capitalize()}Config')
    
    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register blueprints
    from app.api.routes import api_bp
    from app.api.health import health_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(health_bp, url_prefix='/health')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
