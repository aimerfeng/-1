"""Unit tests for authentication routes.

Verifies registration, login, WeChat login, profile management,
and permission decorators.
"""

from unittest.mock import patch, MagicMock
import pytest
from flask import jsonify
from flask_jwt_extended import create_access_token, jwt_required

from server.extensions import db as _db
from server.models.user import User
from server.routes.auth import validate_phone, role_required, certification_required


class TestValidatePhone:
    """Tests for the validate_phone utility function."""

    def test_valid_phones(self):
        assert validate_phone('13800138000') is True
        assert validate_phone('15912345678') is True
        assert validate_phone('18600001111') is True
        assert validate_phone('19900009999') is True

    def test_invalid_phones(self):
        assert validate_phone('') is False
        assert validate_phone('1234567890') is False
        assert validate_phone('12345678901') is False
        assert validate_phone('10000000000') is False
        assert validate_phone('1380013800') is False
        assert validate_phone('138001380001') is False
        assert validate_phone('abc') is False
        assert validate_phone(None) is False
        assert validate_phone(13800138000) is False


class TestRegisterRoute:
    """Tests for POST /api/auth/register."""

    def test_register_success(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '13800138000', 'password': 'testpass123',
            'code': '123456', 'role': 'buyer'
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['phone'] == '13800138000'
        assert data['user']['role'] == 'buyer'

    def test_register_supplier(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '13800138001', 'password': 'testpass123',
            'code': '123456', 'role': 'supplier'
        })
        assert resp.status_code == 201
        assert resp.get_json()['user']['role'] == 'supplier'

    def test_register_invalid_phone(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '12345', 'password': 'testpass123',
            'code': '123456', 'role': 'buyer'
        })
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '13800138002', 'password': '123',
            'code': '123456', 'role': 'buyer'
        })
        assert resp.status_code == 400

    def test_register_duplicate_phone(self, client):
        client.post('/api/auth/register', json={
            'phone': '13800138003', 'password': 'testpass123',
            'code': '123456', 'role': 'buyer'
        })
        resp = client.post('/api/auth/register', json={
            'phone': '13800138003', 'password': 'otherpass',
            'code': '654321', 'role': 'supplier'
        })
        assert resp.status_code == 400

    def test_register_invalid_role(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '13800138004', 'password': 'testpass123',
            'code': '123456', 'role': 'admin'
        })
        assert resp.status_code == 400


class TestLoginRoute:
    """Tests for POST /api/auth/login."""

    def _create_user(self, client):
        client.post('/api/auth/register', json={
            'phone': '13800138000', 'password': 'testpass123',
            'code': '123456', 'role': 'buyer'
        })

    def test_login_success(self, client):
        self._create_user(client)
        resp = client.post('/api/auth/login', json={
            'phone': '13800138000', 'password': 'testpass123'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['phone'] == '13800138000'

    def test_login_wrong_password(self, client):
        self._create_user(client)
        resp = client.post('/api/auth/login', json={
            'phone': '13800138000', 'password': 'wrongpass'
        })
        assert resp.status_code == 401

    def test_login_unregistered(self, client):
        resp = client.post('/api/auth/login', json={
            'phone': '13800138000', 'password': 'testpass123'
        })
        assert resp.status_code == 401

    def test_login_empty_fields(self, client):
        resp = client.post('/api/auth/login', json={
            'phone': '', 'password': ''
        })
        assert resp.status_code == 400


class TestWxLoginRoute:
    """Tests for POST /api/auth/wx-login."""

    def test_wx_login_new_user(self, client):
        resp = client.post('/api/auth/wx-login', json={'code': 'test_code_123'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['is_new'] is True

    def test_wx_login_existing_user(self, client):
        client.post('/api/auth/wx-login', json={'code': 'test_code_456'})
        resp = client.post('/api/auth/wx-login', json={'code': 'test_code_456'})
        assert resp.status_code == 200
        assert resp.get_json()['is_new'] is False

    def test_wx_login_missing_code(self, client):
        resp = client.post('/api/auth/wx-login', json={})
        assert resp.status_code == 400


class TestProfileRoute:
    """Tests for GET/PUT /api/auth/profile."""

    def _get_token(self, client):
        resp = client.post('/api/auth/register', json={
            'phone': '13700137000', 'password': 'testpass123',
            'code': '123456', 'role': 'buyer'
        })
        return resp.get_json()['token']

    def test_get_profile(self, client):
        token = self._get_token(client)
        resp = client.get('/api/auth/profile',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        assert resp.get_json()['user']['phone'] == '13700137000'

    def test_update_profile(self, client):
        token = self._get_token(client)
        resp = client.put('/api/auth/profile',
                          json={'company_name': '测试公司', 'contact_name': '张三'},
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['company_name'] == '测试公司'
        assert data['user']['contact_name'] == '张三'

    def test_get_profile_unauthorized(self, client):
        resp = client.get('/api/auth/profile')
        assert resp.status_code == 401


@pytest.fixture(scope="module")
def decorator_app():
    """Create a fresh app with test endpoints for decorator testing."""
    from server.app import create_app
    app = create_app("testing")

    @app.route("/test/role-admin")
    @jwt_required()
    @role_required(["admin"])
    def _test_admin():
        return jsonify({"message": "ok"})

    @app.route("/test/role-supplier")
    @jwt_required()
    @role_required(["supplier"])
    def _test_supplier():
        return jsonify({"message": "ok"})

    @app.route("/test/cert-only")
    @jwt_required()
    @certification_required
    def _test_cert():
        return jsonify({"message": "ok"})

    return app


class TestRoleRequired:
    """Tests for the role_required decorator."""

    def test_allows_matching_role(self, decorator_app):
        with decorator_app.app_context():
            _db.create_all()
            user = User(phone="13800138000", role="admin")
            _db.session.add(user)
            _db.session.commit()
            token = create_access_token(identity=user.id)
        with decorator_app.test_client() as c:
            resp = c.get("/test/role-admin",
                         headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
        with decorator_app.app_context():
            _db.session.rollback()
            _db.drop_all()

    def test_rejects_wrong_role(self, decorator_app):
        with decorator_app.app_context():
            _db.create_all()
            user = User(phone="13800138001", role="buyer")
            _db.session.add(user)
            _db.session.commit()
            token = create_access_token(identity=user.id)
        with decorator_app.test_client() as c:
            resp = c.get("/test/role-supplier",
                         headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        with decorator_app.app_context():
            _db.session.rollback()
            _db.drop_all()


class TestCertificationRequired:
    """Tests for the certification_required decorator."""

    def test_allows_approved(self, decorator_app):
        with decorator_app.app_context():
            _db.create_all()
            user = User(phone="13800138010", role="buyer",
                        certification_status="approved")
            _db.session.add(user)
            _db.session.commit()
            token = create_access_token(identity=user.id)
        with decorator_app.test_client() as c:
            resp = c.get("/test/cert-only",
                         headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
        with decorator_app.app_context():
            _db.session.rollback()
            _db.drop_all()

    def test_rejects_pending(self, decorator_app):
        with decorator_app.app_context():
            _db.create_all()
            user = User(phone="13800138011", role="buyer",
                        certification_status="pending")
            _db.session.add(user)
            _db.session.commit()
            token = create_access_token(identity=user.id)
        with decorator_app.test_client() as c:
            resp = c.get("/test/cert-only",
                         headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        with decorator_app.app_context():
            _db.session.rollback()
            _db.drop_all()

    def test_rejects_rejected(self, decorator_app):
        with decorator_app.app_context():
            _db.create_all()
            user = User(phone="13800138012", role="supplier",
                        certification_status="rejected")
            _db.session.add(user)
            _db.session.commit()
            token = create_access_token(identity=user.id)
        with decorator_app.test_client() as c:
            resp = c.get("/test/cert-only",
                         headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
        with decorator_app.app_context():
            _db.session.rollback()
            _db.drop_all()
