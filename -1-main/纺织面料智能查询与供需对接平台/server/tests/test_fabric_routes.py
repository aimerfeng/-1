"""Unit tests for fabric management routes.

Tests all fabric endpoints:
- POST /api/fabrics (create)
- GET /api/fabrics (list with filters)
- GET /api/fabrics/<id> (detail)
- PUT /api/fabrics/<id> (update)
- GET /api/fabrics/compare?ids=... (compare)
- POST /api/fabrics/<id>/images (upload images)

Validates: Requirements 3.1, 3.3, 3.4, 3.6, 4.5, 4.6
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.fabric import Fabric


@pytest.fixture
def supplier_token(client):
    """Create a supplier user and return their JWT token."""
    user = User(phone='13900139001', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def buyer_token(client):
    """Create a buyer user and return their JWT token."""
    user = User(phone='13900139002', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_supplier_token(client):
    """Create another supplier user and return their JWT token."""
    user = User(phone='13900139003', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def sample_fabric_data():
    """Return valid fabric creation data."""
    return {
        'name': '纯棉面料',
        'composition': '100%棉',
        'weight': 180.0,
        'width': 150.0,
        'craft': '平纹',
        'color': '白色',
        'price': 25.5,
        'min_order_qty': 100,
        'delivery_days': 7,
    }


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestCreateFabric:
    """Tests for POST /api/fabrics."""

    def test_create_fabric_success(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        resp = client.post('/api/fabrics', json=sample_fabric_data,
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == '纯棉面料'
        assert data['composition'] == '100%棉'
        assert data['weight'] == 180.0
        assert data['price'] == 25.5
        assert data['id'] is not None

    def test_create_fabric_missing_required_field(self, client, supplier_token):
        token, _ = supplier_token
        # Missing composition
        resp = client.post('/api/fabrics', json={
            'name': '测试面料',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'composition' in data.get('errors', {})

    def test_create_fabric_invalid_weight(self, client, supplier_token):
        token, _ = supplier_token
        resp = client.post('/api/fabrics', json={
            'name': '测试面料',
            'composition': '100%棉',
            'weight': -10.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'weight' in data.get('errors', {})

    def test_create_fabric_buyer_forbidden(self, client, buyer_token, sample_fabric_data):
        token, _ = buyer_token
        resp = client.post('/api/fabrics', json=sample_fabric_data,
                           headers=_auth_header(token))
        assert resp.status_code == 403

    def test_create_fabric_no_auth(self, client, sample_fabric_data):
        resp = client.post('/api/fabrics', json=sample_fabric_data)
        assert resp.status_code == 401

    def test_create_fabric_with_images(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        sample_fabric_data['images'] = ['https://example.com/img1.jpg']
        resp = client.post('/api/fabrics', json=sample_fabric_data,
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['images'] == ['https://example.com/img1.jpg']


class TestListFabrics:
    """Tests for GET /api/fabrics."""

    def _create_fabrics(self, client, supplier_token):
        """Helper to create multiple fabrics for testing."""
        token, supplier_id = supplier_token
        fabrics_data = [
            {'name': '纯棉面料', 'composition': '100%棉', 'weight': 180.0,
             'width': 150.0, 'craft': '平纹', 'color': '白色', 'price': 25.5},
            {'name': '涤纶面料', 'composition': '100%涤纶', 'weight': 120.0,
             'width': 140.0, 'craft': '斜纹', 'color': '黑色', 'price': 15.0},
            {'name': '棉麻混纺', 'composition': '60%棉40%麻', 'weight': 200.0,
             'width': 160.0, 'craft': '平纹', 'color': '米色', 'price': 35.0},
        ]
        for fd in fabrics_data:
            client.post('/api/fabrics', json=fd, headers=_auth_header(token))

    def test_list_all_fabrics(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 3
        assert len(data['items']) == 3
        assert data['page'] == 1
        assert data['per_page'] == 20

    def test_filter_by_composition(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?composition=棉')
        data = resp.get_json()
        # Should match '100%棉' and '60%棉40%麻'
        assert data['total'] == 2

    def test_filter_by_craft(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?craft=斜纹')
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['craft'] == '斜纹'

    def test_filter_by_color(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?color=白')
        data = resp.get_json()
        assert data['total'] == 1

    def test_filter_by_price_range(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?price_min=20&price_max=30')
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['price'] == 25.5

    def test_filter_by_weight_range(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?weight_min=150&weight_max=190')
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['weight'] == 180.0

    def test_pagination(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?page=1&per_page=2')
        data = resp.get_json()
        assert data['total'] == 3
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_pagination_page_2(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?page=2&per_page=2')
        data = resp.get_json()
        assert data['total'] == 3
        assert len(data['items']) == 1
        assert data['page'] == 2

    def test_combined_filters(self, client, supplier_token):
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics?composition=棉&craft=平纹&price_max=30')
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['name'] == '纯棉面料'

    def test_no_auth_required(self, client, supplier_token):
        """List endpoint should be public (no auth required)."""
        self._create_fabrics(client, supplier_token)
        resp = client.get('/api/fabrics')
        assert resp.status_code == 200


class TestGetFabric:
    """Tests for GET /api/fabrics/<id>."""

    def test_get_fabric_success(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.get(f'/api/fabrics/{fabric_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == fabric_id
        assert data['composition'] == '100%棉'

    def test_get_fabric_not_found(self, client):
        resp = client.get('/api/fabrics/99999')
        assert resp.status_code == 404

    def test_get_fabric_no_auth_required(self, client, supplier_token, sample_fabric_data):
        """Detail endpoint should be public."""
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.get(f'/api/fabrics/{fabric_id}')
        assert resp.status_code == 200


class TestUpdateFabric:
    """Tests for PUT /api/fabrics/<id>."""

    def test_update_fabric_success(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.put(f'/api/fabrics/{fabric_id}',
                          json={'price': 30.0, 'color': '蓝色'},
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['price'] == 30.0
        assert data['color'] == '蓝色'
        # Unchanged fields should remain
        assert data['composition'] == '100%棉'

    def test_update_fabric_not_owner(self, client, supplier_token,
                                     another_supplier_token, sample_fabric_data):
        token, _ = supplier_token
        other_token, _ = another_supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.put(f'/api/fabrics/{fabric_id}',
                          json={'price': 30.0},
                          headers=_auth_header(other_token))
        assert resp.status_code == 403

    def test_update_fabric_not_found(self, client, supplier_token):
        token, _ = supplier_token
        resp = client.put('/api/fabrics/99999',
                          json={'price': 30.0},
                          headers=_auth_header(token))
        assert resp.status_code == 404

    def test_update_fabric_invalid_data(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.put(f'/api/fabrics/{fabric_id}',
                          json={'price': -5.0},
                          headers=_auth_header(token))
        assert resp.status_code == 400

    def test_update_fabric_no_auth(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.put(f'/api/fabrics/{fabric_id}',
                          json={'price': 30.0})
        assert resp.status_code == 401


class TestCompareFabrics:
    """Tests for GET /api/fabrics/compare."""

    def _create_fabrics(self, client, supplier_token):
        token, _ = supplier_token
        ids = []
        for i, name in enumerate(['面料A', '面料B', '面料C']):
            resp = client.post('/api/fabrics', json={
                'name': name,
                'composition': f'成分{i}',
                'weight': 100.0 + i * 50,
                'width': 140.0 + i * 10,
                'craft': '平纹',
                'price': 20.0 + i * 10,
            }, headers=_auth_header(token))
            ids.append(resp.get_json()['id'])
        return ids

    def test_compare_fabrics_success(self, client, supplier_token):
        ids = self._create_fabrics(client, supplier_token)
        ids_str = ','.join(str(i) for i in ids)
        resp = client.get(f'/api/fabrics/compare?ids={ids_str}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 3
        assert len(data['items']) == 3

    def test_compare_fabrics_partial(self, client, supplier_token):
        ids = self._create_fabrics(client, supplier_token)
        resp = client.get(f'/api/fabrics/compare?ids={ids[0]},{ids[1]}')
        data = resp.get_json()
        assert data['total'] == 2

    def test_compare_fabrics_missing_ids(self, client):
        resp = client.get('/api/fabrics/compare')
        assert resp.status_code == 400

    def test_compare_fabrics_empty_ids(self, client):
        resp = client.get('/api/fabrics/compare?ids=')
        assert resp.status_code == 400

    def test_compare_fabrics_invalid_ids(self, client):
        resp = client.get('/api/fabrics/compare?ids=abc,def')
        assert resp.status_code == 400

    def test_compare_fabrics_nonexistent_ids(self, client):
        resp = client.get('/api/fabrics/compare?ids=99998,99999')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['total'] == 0

    def test_compare_no_auth_required(self, client, supplier_token):
        """Compare endpoint should be public."""
        ids = self._create_fabrics(client, supplier_token)
        ids_str = ','.join(str(i) for i in ids)
        resp = client.get(f'/api/fabrics/compare?ids={ids_str}')
        assert resp.status_code == 200


class TestUploadImages:
    """Tests for POST /api/fabrics/<id>/images."""

    def test_upload_images_success(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': ['https://example.com/img1.jpg',
                                            'https://example.com/img2.jpg']},
                           headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['images']) == 2

    def test_upload_images_appends(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        sample_fabric_data['images'] = ['https://example.com/existing.jpg']
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': ['https://example.com/new.jpg']},
                           headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['images']) == 2
        assert 'https://example.com/existing.jpg' in data['images']
        assert 'https://example.com/new.jpg' in data['images']

    def test_upload_images_not_owner(self, client, supplier_token,
                                     another_supplier_token, sample_fabric_data):
        token, _ = supplier_token
        other_token, _ = another_supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': ['https://example.com/img.jpg']},
                           headers=_auth_header(other_token))
        assert resp.status_code == 403

    def test_upload_images_not_found(self, client, supplier_token):
        token, _ = supplier_token
        resp = client.post('/api/fabrics/99999/images',
                           json={'images': ['https://example.com/img.jpg']},
                           headers=_auth_header(token))
        assert resp.status_code == 404

    def test_upload_images_empty_list(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': []},
                           headers=_auth_header(token))
        assert resp.status_code == 400

    def test_upload_images_buyer_forbidden(self, client, buyer_token,
                                           supplier_token, sample_fabric_data):
        s_token, _ = supplier_token
        b_token, _ = buyer_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(s_token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': ['https://example.com/img.jpg']},
                           headers=_auth_header(b_token))
        assert resp.status_code == 403

    def test_upload_images_no_auth(self, client, supplier_token, sample_fabric_data):
        token, _ = supplier_token
        create_resp = client.post('/api/fabrics', json=sample_fabric_data,
                                  headers=_auth_header(token))
        fabric_id = create_resp.get_json()['id']

        resp = client.post(f'/api/fabrics/{fabric_id}/images',
                           json={'images': ['https://example.com/img.jpg']})
        assert resp.status_code == 401
