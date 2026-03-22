"""Flask application factory module."""

import os
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect, text

from server.config import config_by_name
from server.extensions import db, jwt

logger = logging.getLogger(__name__)


def create_app(config_name="development"):
    """Create and configure the Flask application.

    Args:
        config_name: Configuration name ('development', 'testing', 'production').

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # 静态文件目录（图片上传）
    static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

    @app.route('/static/uploads/fabrics/<path:filename>')
    def serve_fabric_image(filename):
        return send_from_directory(os.path.join(static_folder, 'uploads', 'fabrics'), filename)

    @app.route('/static/avatars/<path:filename>')
    def serve_avatar_image(filename):
        return send_from_directory(os.path.join(static_folder, 'avatars'), filename)

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
        _auto_migrate(app)

    return app


def _auto_migrate(app):
    """Add missing columns to existing tables.

    SQLAlchemy's create_all() only creates new tables; it does not
    alter existing ones.  This helper inspects each model's columns
    and issues ALTER TABLE … ADD COLUMN for any that are absent in
    the live database.  Only supports SQLite and MySQL.
    """
    inspector = inspect(db.engine)
    meta = db.metadata

    for table_name, table in meta.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing = {col['name'] for col in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile(db.engine.dialect)
                nullable = 'NULL' if col.nullable else 'NOT NULL'
                default = ''
                if col.default is not None:
                    default = f" DEFAULT '{col.default.arg}'" if isinstance(col.default.arg, str) else f" DEFAULT {col.default.arg}"
                sql = f'ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type} {nullable}{default}'
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info('Auto-migrate: added column %s.%s', table_name, col.name)
                except Exception as e:
                    db.session.rollback()
                    logger.warning('Auto-migrate: skip %s.%s: %s', table_name, col.name, e)


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
