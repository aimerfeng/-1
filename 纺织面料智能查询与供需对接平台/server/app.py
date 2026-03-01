"""Flask application factory module."""

from flask import Flask
from flask_cors import CORS

from server.config import config_by_name
from server.extensions import db, jwt


def create_app(config_name="development"):
    """Create and configure the Flask application.

    Args:
        config_name: Configuration name ('development', 'testing', 'production').

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"),
         supports_credentials=app.config.get("CORS_SUPPORTS_CREDENTIALS", True))

    # Register blueprints
    _register_blueprints(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def _register_blueprints(app):
    """Register all Flask blueprints.

    Blueprints are imported and registered here. New blueprints for
    fabric, demand, sample, order, and message routes will be
    added in subsequent tasks.
    """
    from server.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from server.routes.fabric import fabric_bp
    app.register_blueprint(fabric_bp, url_prefix="/api/fabrics")

    from server.routes.demand import demand_bp
    app.register_blueprint(demand_bp, url_prefix="/api/demands")

    from server.routes.sample import sample_bp
    app.register_blueprint(sample_bp, url_prefix="/api/samples")

    from server.routes.order import order_bp
    app.register_blueprint(order_bp, url_prefix="/api/orders")

    from server.routes.message import message_bp
    app.register_blueprint(message_bp, url_prefix="/api/messages")

    from server.routes.conversation import conversation_bp
    app.register_blueprint(conversation_bp, url_prefix="/api/conversations")

    from server.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
