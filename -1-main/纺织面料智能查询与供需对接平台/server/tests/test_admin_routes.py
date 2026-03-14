"""Unit tests for admin routes.

Verifies admin user listing, certification approval/rejection,
notification creation, authentication, and authorization.
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.message import Message


def _create_admin(db_session):
    """Create and return an admin user."""
    admin = User(phone='13900000001', role='admin', certification_status='approved')
    admin.set_password('adminpass')
    db_session.session.add(admin)
    db_session.session.commit()
    return admin


def _create_buyer(db_session, phone='13800000001', status='pending',
                  company_name=None, contact_name=None):
    """Create and return a buyer user."""
    user = User(
        phone=phone, role='buyer', certification_status=status,
        company_name=company_name, contact_name=contact_name,
    )
    user.set_password('testpass')
    db_session.session.add(user)
    db_session.session.commit()
    return user


def _get_admin_token(app, admin):
    """Generate a JWT token for the admin user."""
    with app.app_context():
        return create_access_token(identity=str(admin.id))


def _get_user_token(app, user):
    """Generate a JWT token for a regular user."""
    with app.app_context():
        return create_access_token(identity=str(user.id))


class TestListUsers:
    """Tests for GET /api/admin/users."""

    def test_list_pending_users_empty(self, client, app, db):
        """List pending users when none exist returns empty list."""
        admin = _create_admin(db)
        token = _get_admin_token(app, admin)

        resp = client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'] == []
        assert data['total'] == 0
        assert data['page'] == 1

    def test_list_pending_users_with_data(self, client, app, db):
        """List pending users returns correct user data."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000002', status='pending',
                              company_name='测试公司', contact_name='张三')
        token = _get_admin_token(app, admin)

        resp = client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert len(data['items']) == 1

        user_item = data['items'][0]
        assert user_item['id'] == buyer.id
        assert user_item['company_name'] == '测试公司'
        assert user_item['contact_name'] == '张三'
        assert user_item['phone'] == '13800000002'
        assert user_item['role'] == 'buyer'
        assert user_item['certification_status'] == 'pending'
        assert 'created_at' in user_item

    def test_list_users_pagination(self, client, app, db):
        """Pagination works correctly."""
        admin = _create_admin(db)
        # Create 5 pending users
        for i in range(5):
            _create_buyer(db, phone=f'1380000{i:04d}', status='pending')
        token = _get_admin_token(app, admin)

        # Request page 1 with per_page=2
        resp = client.get(
            '/api/admin/users?page=1&per_page=2',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['items']) == 2
        assert data['total'] == 5
        assert data['page'] == 1
        assert data['per_page'] == 2

        # Request page 3 with per_page=2 (should have 1 item)
        resp = client.get(
            '/api/admin/users?page=3&per_page=2',
            headers={'Authorization': f'Bearer {token}'},
        )
        data = resp.get_json()
        assert len(data['items']) == 1
        assert data['total'] == 5

    def test_list_users_status_filter(self, client, app, db):
        """Status filter returns only users with matching status."""
        admin = _create_admin(db)
        _create_buyer(db, phone='13800000010', status='pending')
        _create_buyer(db, phone='13800000011', status='approved')
        _create_buyer(db, phone='13800000012', status='rejected')
        token = _get_admin_token(app, admin)

        # Filter by approved (admin user is also approved, so total=2)
        resp = client.get(
            '/api/admin/users?status=approved',
            headers={'Authorization': f'Bearer {token}'},
        )
        data = resp.get_json()
        assert data['total'] == 2
        for item in data['items']:
            assert item['certification_status'] == 'approved'

        # Filter by rejected
        resp = client.get(
            '/api/admin/users?status=rejected',
            headers={'Authorization': f'Bearer {token}'},
        )
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['certification_status'] == 'rejected'

        # Default filter (pending)
        resp = client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {token}'},
        )
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['certification_status'] == 'pending'

    def test_list_users_not_admin(self, client, app, db):
        """Non-admin users cannot access the endpoint."""
        buyer = _create_buyer(db, phone='13800000020', status='approved')
        token = _get_user_token(app, buyer)

        resp = client.get(
            '/api/admin/users',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

    def test_list_users_no_auth(self, client):
        """Unauthenticated requests are rejected."""
        resp = client.get('/api/admin/users')
        assert resp.status_code == 401


class TestCertifyUser:
    """Tests for PUT /api/admin/users/<id>/certify."""

    def test_approve_user(self, client, app, db):
        """Admin can approve a pending user."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000030', status='pending')
        token = _get_admin_token(app, admin)

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={'status': 'approved'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['certification_status'] == 'approved'

        # Verify the user was actually updated in the database
        updated_user = db.session.get(User, buyer.id)
        assert updated_user.certification_status == 'approved'

        # Verify a notification was created
        notification = Message.query.filter_by(
            user_id=buyer.id, type='review'
        ).first()
        assert notification is not None
        assert '通过' in notification.title

    def test_reject_user_with_reason(self, client, app, db):
        """Admin can reject a user with a reason."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000031', status='pending')
        token = _get_admin_token(app, admin)

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={'status': 'rejected', 'reason': '资料不完整'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['certification_status'] == 'rejected'

        # Verify notification contains the reason
        notification = Message.query.filter_by(
            user_id=buyer.id, type='review'
        ).first()
        assert notification is not None
        assert '未通过' in notification.title
        assert '资料不完整' in notification.content

    def test_reject_user_without_reason(self, client, app, db):
        """Admin can reject a user without providing a reason."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000032', status='pending')
        token = _get_admin_token(app, admin)

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={'status': 'rejected'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['user']['certification_status'] == 'rejected'

    def test_certify_user_not_found(self, client, app, db):
        """Certifying a non-existent user returns 404."""
        admin = _create_admin(db)
        token = _get_admin_token(app, admin)

        resp = client.put(
            '/api/admin/users/99999/certify',
            json={'status': 'approved'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 404

    def test_certify_invalid_status(self, client, app, db):
        """Invalid status value returns 400."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000033', status='pending')
        token = _get_admin_token(app, admin)

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={'status': 'invalid_status'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 400

    def test_certify_not_admin(self, client, app, db):
        """Non-admin users cannot certify."""
        buyer = _create_buyer(db, phone='13800000034', status='approved')
        target = _create_buyer(db, phone='13800000035', status='pending')
        token = _get_user_token(app, buyer)

        resp = client.put(
            f'/api/admin/users/{target.id}/certify',
            json={'status': 'approved'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

    def test_certify_no_auth(self, client, db):
        """Unauthenticated requests are rejected."""
        buyer = _create_buyer(db, phone='13800000036', status='pending')

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={'status': 'approved'},
        )
        assert resp.status_code == 401

    def test_certify_missing_status(self, client, app, db):
        """Missing status in request body returns 400."""
        admin = _create_admin(db)
        buyer = _create_buyer(db, phone='13800000037', status='pending')
        token = _get_admin_token(app, admin)

        resp = client.put(
            f'/api/admin/users/{buyer.id}/certify',
            json={},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 400
