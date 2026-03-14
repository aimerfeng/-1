"""Pytest configuration and shared fixtures.

Configures a test Flask application with SQLite in-memory database
and provides reusable fixtures for test client and database session.
"""

import pytest

from server.app import create_app
from server.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create a Flask application configured for testing.

    Uses SQLite in-memory database for fast, isolated tests.
    Scope is 'session' so the app is created once per test session.
    """
    app = create_app("testing")

    # Register a test endpoint for certification_required property tests.
    # Must be done before the app handles its first request.
    _register_test_endpoints(app)

    yield app


def _register_test_endpoints(app):
    """Register test-only endpoints needed by property-based tests.

    These must be registered before the app handles its first request
    to avoid Flask's setup-finished assertion.
    """
    from flask import jsonify
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from server.extensions import db as _test_db
    from server.models.user import User

    # Register conversation blueprint for tests (not yet in app.py, task 5.4)
    if 'conversation' not in app.blueprints:
        from server.routes.conversation import conversation_bp
        app.register_blueprint(conversation_bp, url_prefix='/api/conversations')

    @app.route('/api/test-cert-required', methods=['GET'])
    @jwt_required()
    def _test_cert_required_endpoint():
        user_id = int(get_jwt_identity())
        user = _test_db.session.get(User, user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在'}), 401
        if user.certification_status != 'approved':
            return jsonify({'code': 403, 'message': '请先完成资质认证'}), 403
        return jsonify({'message': 'access granted'}), 200


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean database for each test function.

    Creates all tables before the test and drops them after,
    ensuring complete isolation between tests.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Provide a Flask test client with a clean database.

    The test client can be used to make HTTP requests to the
    application without running a real server.
    """
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope="function")
def app_context(app, db):
    """Provide an application context with a clean database.

    Useful for tests that need to interact with the database
    directly without going through HTTP routes.
    """
    with app.app_context():
        yield app
