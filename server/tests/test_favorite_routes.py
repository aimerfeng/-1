"""Unit tests for favorite management routes.

Tests all favorite endpoints:
- POST /api/fabrics/<id>/favorite (add favorite)
- DELETE /api/fabrics/<id>/favorite (remove favorite)
- GET /api/fabrics/favorites (list user's favorites)

Validates: Requirements 9.2, 9.3, 9.4
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.fabric import Fabric, Favorite


@pytest.fixture
def buyer_token(client):
    """Create a buyer user and return their JWT token and user ID."""
    user = User(phone='13900139001', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_buyer_token(client):
    """Create another buyer user and return their JWT token and user ID."""
    user = User(phone='13900139004', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def supplier_token(client):
    """Create a supplier user and return their JWT token and user ID."""
    user = User(phone='13900139002', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def sample_fabric(client, supplier_token):
    """Create a fabric and return it."""
    _, supplier_id = supplier_token
    fabric = Fabric(
        supplier_id=supplier_id,
        name='测试面料',
        composition='100%棉',
        weight=180.0,
        width=150.0,
        craft='平纹',
        color='白色',
        price=25.0,
        status='active',
    )
    _db.session.add(fabric)
    _db.session.commit()
    return fabric


@pytest.fixture
def another_fabric(client, supplier_token):
    """Create another fabric and return it."""
    _, supplier_id = supplier_token
    fabric = Fabric(
        supplier_id=supplier_id,
        name='涤纶面料',
        composition='100%涤纶',
        weight=120.0,
        width=140.0,
        craft='斜纹',
        color='黑色',
        price=15.0,
        status='active',
    )
    _db.session.add(fabric)
    _db.session.commit()
    return fabric


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestAddFavorite:
    """Tests for POST /api/fabrics/<id>/favorite."""

    def test_add_favorite_success(self, client, buyer_token, sample_fabric):
        token, user_id = buyer_token
        resp = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['user_id'] == user_id
        assert data['fabric_id'] == sample_fabric.id
        assert data['id'] is not None
        assert data['created_at'] is not None

    def test_add_favorite_duplicate_returns_existing(self, client, buyer_token, sample_fabric):
        """Adding the same favorite twice should return 200 with existing."""
        token, user_id = buyer_token
        # First add
        resp1 = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp1.status_code == 201
        first_id = resp1.get_json()['id']

        # Second add (duplicate)
        resp2 = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp2.status_code == 200
        assert resp2.get_json()['id'] == first_id

    def test_add_favorite_fabric_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post(
            '/api/fabrics/99999/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 404

    def test_add_favorite_no_auth(self, client, sample_fabric):
        resp = client.post(f'/api/fabrics/{sample_fabric.id}/favorite')
        assert resp.status_code == 401

    def test_supplier_can_also_favorite(self, client, supplier_token, sample_fabric):
        """Suppliers should also be able to favorite fabrics."""
        token, _ = supplier_token
        resp = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 201

    def test_different_users_can_favorite_same_fabric(
        self, client, buyer_token, another_buyer_token, sample_fabric
    ):
        """Different users should be able to favorite the same fabric."""
        token1, user_id1 = buyer_token
        token2, user_id2 = another_buyer_token

        resp1 = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token1),
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token2),
        )
        assert resp2.status_code == 201

        # They should have different favorite IDs
        assert resp1.get_json()['id'] != resp2.get_json()['id']


class TestRemoveFavorite:
    """Tests for DELETE /api/fabrics/<id>/favorite."""

    def test_remove_favorite_success(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        # First add
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )

        # Then remove
        resp = client.delete(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['message'] == '取消收藏成功'

    def test_remove_favorite_not_favorited(self, client, buyer_token, sample_fabric):
        """Removing a non-existent favorite should return 404."""
        token, _ = buyer_token
        resp = client.delete(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 404

    def test_remove_favorite_no_auth(self, client, sample_fabric):
        resp = client.delete(f'/api/fabrics/{sample_fabric.id}/favorite')
        assert resp.status_code == 401

    def test_remove_favorite_only_removes_own(
        self, client, buyer_token, another_buyer_token, sample_fabric
    ):
        """Removing a favorite should only affect the current user's favorite."""
        token1, _ = buyer_token
        token2, _ = another_buyer_token

        # Both users favorite the same fabric
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token1),
        )
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token2),
        )

        # User 1 removes their favorite
        resp = client.delete(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token1),
        )
        assert resp.status_code == 200

        # User 2's favorite should still exist
        resp2 = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token2),
        )
        assert resp2.status_code == 200
        assert resp2.get_json()['total'] == 1

    def test_remove_then_re_add(self, client, buyer_token, sample_fabric):
        """Should be able to re-favorite after removing."""
        token, _ = buyer_token

        # Add
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        # Remove
        client.delete(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        # Re-add
        resp = client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        assert resp.status_code == 201


class TestListFavorites:
    """Tests for GET /api/fabrics/favorites."""

    def test_list_favorites_empty(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_list_favorites_with_fabric_info(self, client, buyer_token, sample_fabric):
        token, user_id = buyer_token
        # Add favorite
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )

        resp = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert len(data['items']) == 1

        item = data['items'][0]
        assert item['user_id'] == user_id
        assert item['fabric_id'] == sample_fabric.id
        assert item['fabric'] is not None
        assert item['fabric']['name'] == '测试面料'
        assert item['fabric']['composition'] == '100%棉'
        assert item['fabric']['price'] == 25.0
        assert item['fabric']['status'] == 'active'

    def test_list_favorites_multiple(
        self, client, buyer_token, sample_fabric, another_fabric
    ):
        token, _ = buyer_token
        # Add two favorites
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        client.post(
            f'/api/fabrics/{another_fabric.id}/favorite',
            headers=_auth_header(token),
        )

        resp = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2
        assert len(data['items']) == 2

    def test_list_favorites_only_own(
        self, client, buyer_token, another_buyer_token, sample_fabric
    ):
        """Each user should only see their own favorites."""
        token1, _ = buyer_token
        token2, _ = another_buyer_token

        # User 1 favorites a fabric
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token1),
        )

        # User 2 should see empty list
        resp = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token2),
        )
        assert resp.status_code == 200
        assert resp.get_json()['total'] == 0

    def test_list_favorites_pagination(
        self, client, buyer_token, supplier_token
    ):
        """Test pagination of favorites list."""
        token, _ = buyer_token
        _, supplier_id = supplier_token

        # Create 5 fabrics and favorite them all
        for i in range(5):
            fabric = Fabric(
                supplier_id=supplier_id,
                name=f'面料{i}',
                composition=f'成分{i}',
                weight=100.0 + i * 10,
                width=140.0,
                craft='平纹',
                price=20.0 + i,
                status='active',
            )
            _db.session.add(fabric)
            _db.session.commit()
            client.post(
                f'/api/fabrics/{fabric.id}/favorite',
                headers=_auth_header(token),
            )

        # Get page 1 with 2 per page
        resp = client.get(
            '/api/fabrics/favorites?page=1&per_page=2',
            headers=_auth_header(token),
        )
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

        # Get page 3 with 2 per page (should have 1 item)
        resp = client.get(
            '/api/fabrics/favorites?page=3&per_page=2',
            headers=_auth_header(token),
        )
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 1

    def test_list_favorites_no_auth(self, client):
        resp = client.get('/api/fabrics/favorites')
        assert resp.status_code == 401

    def test_list_favorites_after_remove(self, client, buyer_token, sample_fabric):
        """After removing a favorite, it should not appear in the list."""
        token, _ = buyer_token

        # Add and then remove
        client.post(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )
        client.delete(
            f'/api/fabrics/{sample_fabric.id}/favorite',
            headers=_auth_header(token),
        )

        resp = client.get(
            '/api/fabrics/favorites',
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['total'] == 0
