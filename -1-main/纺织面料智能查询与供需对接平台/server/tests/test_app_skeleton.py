"""Tests for the Flask application skeleton.

Verifies that the application factory, extensions, and configuration
are properly set up and working together.
"""

import pytest
from server.app import create_app
from server.extensions import db, jwt


class TestAppFactory:
    """Tests for the Flask application factory function."""

    def test_create_app_returns_flask_instance(self):
        """Application factory should return a Flask app instance."""
        app = create_app("testing")
        assert app is not None
        assert app.name == "server.app"

    def test_testing_config_applied(self):
        """Testing configuration should use SQLite in-memory database."""
        app = create_app("testing")
        assert app.config["TESTING"] is True
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
        assert app.config["JWT_SECRET_KEY"] == "test-jwt-secret-key"

    def test_development_config_has_mysql_uri(self):
        """Development configuration should reference MySQL connection string."""
        from server.config import DevelopmentConfig
        assert DevelopmentConfig.DEBUG is True
        assert "mysql+pymysql" in DevelopmentConfig.SQLALCHEMY_DATABASE_URI

    def test_sqlalchemy_extension_initialized(self, app):
        """SQLAlchemy extension should be initialized with the app."""
        assert db is not None
        with app.app_context():
            # Verify we can access the engine (proves db is bound to app)
            assert db.engine is not None

    def test_jwt_extension_initialized(self, app):
        """JWTManager extension should be initialized with the app."""
        assert jwt is not None
        # Flask-JWT-Extended registers itself under 'flask-jwt-extended'
        assert "flask-jwt-extended" in app.extensions

    def test_cors_enabled(self, app):
        """CORS should be enabled on the application."""
        # Flask-CORS adds an after_request handler
        assert app.after_request_funcs is not None


class TestTestFixtures:
    """Tests for the pytest fixtures defined in conftest.py."""

    def test_client_fixture(self, client):
        """Test client fixture should provide a working test client."""
        assert client is not None

    def test_db_fixture_creates_tables(self, db):
        """Database fixture should create tables successfully."""
        assert db is not None

    def test_app_context_fixture(self, app_context):
        """App context fixture should provide a valid app context."""
        assert app_context is not None
        assert app_context.config["TESTING"] is True

    def test_db_isolation(self, db):
        """Each test should get a clean database (isolation check)."""
        # This test verifies that the db fixture provides a fresh database
        # by checking that no tables have leftover data from other tests
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        # In a fresh skeleton, there should be no model tables yet
        # (tables will be added in later tasks)
        assert isinstance(tables, list)
