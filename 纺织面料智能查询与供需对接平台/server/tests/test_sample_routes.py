"""Unit tests for sample management routes.

Tests all sample endpoints:
- POST /api/samples (create sample request, buyer only)
- GET /api/samples (list with role-based filtering)
- PUT /api/samples/<id>/review (review sample, supplier only)
- GET /api/samples/<id>/logistics (query logistics status)

Validates: Requirements 6.1, 6.2, 6.3
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.sample import Sample


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
def supplier_token(client):
    """Create a supplier user and return their JWT token and user ID."""
    user = User(phone='13900139002', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_supplier_token(client):
    """Create another supplier user and return their JWT token and user ID."""
    user = User(phone='13900139003', role='supplier')
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


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestCreateSample:
    """Tests for POST /api/samples."""

    def test_create_sample_success(self, client, buyer_token, sample_fabric):
        token, buyer_id = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 5,
            'address': '上海市浦东新区张江高科技园区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['fabric_id'] == sample_fabric.id
        assert data['buyer_id'] == buyer_id
        assert data['supplier_id'] == sample_fabric.supplier_id
        assert data['quantity'] == 5
        assert data['address'] == '上海市浦东新区张江高科技园区'
        assert data['status'] == 'pending'
        assert data['id'] is not None

    def test_create_sample_missing_fabric_id(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'quantity': 5,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'fabric_id' in data.get('errors', {})

    def test_create_sample_missing_quantity(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'quantity' in data.get('errors', {})

    def test_create_sample_missing_address(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 5,
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'address' in data.get('errors', {})

    def test_create_sample_invalid_quantity(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': -1,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'quantity' in data.get('errors', {})

    def test_create_sample_zero_quantity(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 0,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_create_sample_fabric_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': 99999,
            'quantity': 5,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 404

    def test_create_sample_supplier_forbidden(self, client, supplier_token, sample_fabric):
        token, _ = supplier_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 5,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_create_sample_no_auth(self, client, sample_fabric):
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 5,
            'address': '上海市浦东新区',
        })
        assert resp.status_code == 401

    def test_create_sample_empty_address(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 5,
            'address': '   ',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'address' in data.get('errors', {})

    def test_create_sample_derives_supplier_from_fabric(self, client, buyer_token, sample_fabric):
        """Supplier ID should be derived from the fabric's supplier."""
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 3,
            'address': '北京市朝阳区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['supplier_id'] == sample_fabric.supplier_id


class TestListSamples:
    """Tests for GET /api/samples."""

    def _create_sample(self, client, buyer_token, fabric):
        """Helper to create a sample request."""
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': 3,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def test_buyer_sees_own_samples(self, client, buyer_token, another_buyer_token, sample_fabric):
        token, _ = buyer_token
        other_token, _ = another_buyer_token

        # Create samples for both buyers
        self._create_sample(client, buyer_token, sample_fabric)
        self._create_sample(client, another_buyer_token, sample_fabric)

        # Buyer 1 should only see their own sample
        resp = client.get('/api/samples', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_supplier_sees_received_samples(self, client, buyer_token, supplier_token, sample_fabric):
        b_token, _ = buyer_token
        s_token, _ = supplier_token

        self._create_sample(client, buyer_token, sample_fabric)

        # Supplier should see samples sent to them
        resp = client.get('/api/samples', headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_supplier_does_not_see_other_supplier_samples(
        self, client, buyer_token, supplier_token, another_supplier_token, sample_fabric
    ):
        """A supplier should only see samples addressed to them."""
        s_token, _ = supplier_token
        other_s_token, _ = another_supplier_token

        self._create_sample(client, buyer_token, sample_fabric)

        # The other supplier should not see this sample
        resp = client.get('/api/samples', headers=_auth_header(other_s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0

    def test_list_samples_pagination(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        for _ in range(5):
            self._create_sample(client, buyer_token, sample_fabric)

        resp = client.get('/api/samples?page=1&per_page=2',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_list_samples_no_auth(self, client):
        resp = client.get('/api/samples')
        assert resp.status_code == 401

    def test_list_samples_empty(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/samples', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []


class TestReviewSample:
    """Tests for PUT /api/samples/<id>/review."""

    def _create_sample(self, client, buyer_token, fabric):
        """Helper to create a sample request and return its data."""
        token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': 3,
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def test_approve_sample_success(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        # After approval, logistics creation is triggered, so status may be
        # 'approved' or 'shipping' depending on logistics success
        assert data['status'] in ('approved', 'shipping')

    def test_reject_sample_success(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'rejected',
            'reject_reason': '库存不足',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'rejected'
        assert data['reject_reason'] == '库存不足'

    def test_reject_sample_missing_reason(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'rejected',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_reject_sample_empty_reason(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'rejected',
            'reject_reason': '   ',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_review_invalid_status(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'invalid_status',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_review_sample_not_found(self, client, supplier_token):
        s_token, _ = supplier_token
        resp = client.put('/api/samples/99999/review', json={
            'status': 'approved',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 404

    def test_review_by_wrong_supplier(
        self, client, buyer_token, supplier_token, another_supplier_token, sample_fabric
    ):
        """Only the sample's supplier can review it."""
        other_s_token, _ = another_supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(other_s_token))
        assert resp.status_code == 403

    def test_review_by_buyer_forbidden(self, client, buyer_token, sample_fabric):
        """Buyers cannot review samples."""
        b_token, _ = buyer_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(b_token))
        assert resp.status_code == 403

    def test_review_already_reviewed_sample(self, client, buyer_token, supplier_token, sample_fabric):
        """Cannot review a sample that has already been reviewed."""
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        # First review
        client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(s_token))

        # Second review should fail
        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'rejected',
            'reject_reason': '改主意了',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_review_no_auth(self, client):
        resp = client.put('/api/samples/1/review', json={
            'status': 'approved',
        })
        assert resp.status_code == 401

    def test_approve_triggers_logistics(self, client, buyer_token, supplier_token, sample_fabric):
        """Approving a sample should trigger logistics creation."""
        s_token, _ = supplier_token
        sample_data = self._create_sample(client, buyer_token, sample_fabric)
        sample_id = sample_data['id']

        resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        # After logistics creation, the sample should have a logistics_no
        # and status should be 'shipping' (set by create_logistics)
        assert data['status'] in ('approved', 'shipping')


class TestGetSampleLogistics:
    """Tests for GET /api/samples/<id>/logistics."""

    def _create_and_approve_sample(self, client, buyer_token, supplier_token, fabric):
        """Helper to create and approve a sample."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token

        # Create sample
        resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': 3,
            'address': '上海市浦东新区',
        }, headers=_auth_header(b_token))
        sample_id = resp.get_json()['id']

        # Approve sample (triggers logistics)
        client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(s_token))

        return sample_id

    def test_get_logistics_success(self, client, buyer_token, supplier_token, sample_fabric):
        b_token, _ = buyer_token
        sample_id = self._create_and_approve_sample(
            client, buyer_token, supplier_token, sample_fabric
        )

        resp = client.get(f'/api/samples/{sample_id}/logistics',
                          headers=_auth_header(b_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['sample_id'] == sample_id
        assert data['logistics_no'] is not None
        assert 'logistics' in data

    def test_get_logistics_supplier_can_view(self, client, buyer_token, supplier_token, sample_fabric):
        """Supplier should also be able to view logistics."""
        s_token, _ = supplier_token
        sample_id = self._create_and_approve_sample(
            client, buyer_token, supplier_token, sample_fabric
        )

        resp = client.get(f'/api/samples/{sample_id}/logistics',
                          headers=_auth_header(s_token))
        assert resp.status_code == 200

    def test_get_logistics_unauthorized_user(
        self, client, buyer_token, supplier_token, another_buyer_token, sample_fabric
    ):
        """A user who is neither buyer nor supplier of the sample cannot view logistics."""
        other_b_token, _ = another_buyer_token
        sample_id = self._create_and_approve_sample(
            client, buyer_token, supplier_token, sample_fabric
        )

        resp = client.get(f'/api/samples/{sample_id}/logistics',
                          headers=_auth_header(other_b_token))
        assert resp.status_code == 403

    def test_get_logistics_sample_not_found(self, client, buyer_token):
        b_token, _ = buyer_token
        resp = client.get('/api/samples/99999/logistics',
                          headers=_auth_header(b_token))
        assert resp.status_code == 404

    def test_get_logistics_no_logistics_info(self, client, buyer_token, sample_fabric):
        """A pending sample has no logistics info."""
        b_token, _ = buyer_token
        resp = client.post('/api/samples', json={
            'fabric_id': sample_fabric.id,
            'quantity': 3,
            'address': '上海市浦东新区',
        }, headers=_auth_header(b_token))
        sample_id = resp.get_json()['id']

        resp = client.get(f'/api/samples/{sample_id}/logistics',
                          headers=_auth_header(b_token))
        assert resp.status_code == 404

    def test_get_logistics_no_auth(self, client):
        resp = client.get('/api/samples/1/logistics')
        assert resp.status_code == 401
