"""Unit tests for order management routes.

Tests all order endpoints:
- POST /api/orders (create order, buyer only)
- GET /api/orders (list with role-based filtering, paginated)
- GET /api/orders/<id> (order detail with items, fabric info, timeline)
- PUT /api/orders/<id>/status (status transition with validation)

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.order import Order, OrderItem


@pytest.fixture
def buyer_token(client):
    """Create a buyer user and return their JWT token and user ID."""
    user = User(phone='13800138001', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def supplier_token(client):
    """Create a supplier user and return their JWT token and user ID."""
    user = User(phone='13800138002', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_supplier_token(client):
    """Create another supplier user and return their JWT token and user ID."""
    user = User(phone='13800138003', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_buyer_token(client):
    """Create another buyer user and return their JWT token and user ID."""
    user = User(phone='13800138004', role='buyer')
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
        name='测试面料A',
        composition='100%棉',
        weight=180.0,
        width=150.0,
        craft='平纹',
        color='白色',
        price=25.0,
        stock_quantity=10000,
        status='active',
    )
    _db.session.add(fabric)
    _db.session.commit()
    return fabric


@pytest.fixture
def second_fabric(client, supplier_token):
    """Create a second fabric from the same supplier."""
    _, supplier_id = supplier_token
    fabric = Fabric(
        supplier_id=supplier_id,
        name='测试面料B',
        composition='涤纶',
        weight=200.0,
        width=160.0,
        craft='斜纹',
        color='蓝色',
        price=30.0,
        stock_quantity=10000,
        status='active',
    )
    _db.session.add(fabric)
    _db.session.commit()
    return fabric


@pytest.fixture
def other_supplier_fabric(client, another_supplier_token):
    """Create a fabric from a different supplier."""
    _, supplier_id = another_supplier_token
    fabric = Fabric(
        supplier_id=supplier_id,
        name='其他供应商面料',
        composition='丝绸',
        weight=100.0,
        width=140.0,
        craft='缎纹',
        color='红色',
        price=50.0,
        stock_quantity=10000,
        status='active',
    )
    _db.session.add(fabric)
    _db.session.commit()
    return fabric


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestCreateOrder:
    """Tests for POST /api/orders."""

    def test_create_order_success(self, client, buyer_token, sample_fabric):
        token, buyer_id = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 10}],
            'address': '上海市浦东新区张江高科技园区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['buyer_id'] == buyer_id
        assert data['supplier_id'] == sample_fabric.supplier_id
        assert data['address'] == '上海市浦东新区张江高科技园区'
        assert data['status'] == 'pending'
        assert data['order_no'] is not None
        assert data['total_amount'] == 10 * sample_fabric.price
        assert len(data['items']) == 1
        assert data['items'][0]['fabric_id'] == sample_fabric.id
        assert data['items'][0]['quantity'] == 10
        assert data['items'][0]['unit_price'] == sample_fabric.price
        assert data['items'][0]['subtotal'] == 10 * sample_fabric.price

    def test_create_order_multiple_items(self, client, buyer_token, sample_fabric, second_fabric):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [
                {'fabric_id': sample_fabric.id, 'quantity': 10},
                {'fabric_id': second_fabric.id, 'quantity': 5},
            ],
            'address': '北京市朝阳区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        expected_total = 10 * sample_fabric.price + 5 * second_fabric.price
        assert data['total_amount'] == expected_total
        assert len(data['items']) == 2

    def test_create_order_missing_address(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 10}],
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'address' in data.get('errors', {})

    def test_create_order_empty_address(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 10}],
            'address': '   ',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'address' in data.get('errors', {})

    def test_create_order_missing_items(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'items' in data.get('errors', {})

    def test_create_order_empty_items(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'items' in data.get('errors', {})

    def test_create_order_invalid_quantity(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': -1}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_create_order_zero_quantity(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 0}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_create_order_missing_fabric_id(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'quantity': 10}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_create_order_fabric_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': 99999, 'quantity': 10}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 404

    def test_create_order_different_suppliers(
        self, client, buyer_token, sample_fabric, other_supplier_fabric
    ):
        """All items must belong to the same supplier."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [
                {'fabric_id': sample_fabric.id, 'quantity': 10},
                {'fabric_id': other_supplier_fabric.id, 'quantity': 5},
            ],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert '同一供应商' in data.get('message', '')

    def test_create_order_supplier_forbidden(self, client, supplier_token, sample_fabric):
        """Suppliers cannot create orders."""
        token, _ = supplier_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 10}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_create_order_no_auth(self, client, sample_fabric):
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 10}],
            'address': '上海市浦东新区',
        })
        assert resp.status_code == 401

    def test_create_order_derives_supplier_from_fabric(self, client, buyer_token, sample_fabric):
        """Supplier ID should be derived from the fabric's supplier."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 5}],
            'address': '北京市朝阳区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['supplier_id'] == sample_fabric.supplier_id

    def test_create_order_price_from_fabric(self, client, buyer_token, sample_fabric):
        """Unit price should come from the fabric's price."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': sample_fabric.id, 'quantity': 3}],
            'address': '北京市朝阳区',
        }, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['items'][0]['unit_price'] == sample_fabric.price
        assert data['items'][0]['subtotal'] == 3 * sample_fabric.price


class TestListOrders:
    """Tests for GET /api/orders."""

    def _create_order(self, client, buyer_token, fabric):
        """Helper to create an order."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': 5}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def test_buyer_sees_own_orders(self, client, buyer_token, another_buyer_token, sample_fabric):
        token, _ = buyer_token
        other_token, _ = another_buyer_token

        self._create_order(client, buyer_token, sample_fabric)
        self._create_order(client, another_buyer_token, sample_fabric)

        resp = client.get('/api/orders', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_supplier_sees_received_orders(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        self._create_order(client, buyer_token, sample_fabric)

        resp = client.get('/api/orders', headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_supplier_does_not_see_other_supplier_orders(
        self, client, buyer_token, supplier_token, another_supplier_token, sample_fabric
    ):
        other_s_token, _ = another_supplier_token
        self._create_order(client, buyer_token, sample_fabric)

        resp = client.get('/api/orders', headers=_auth_header(other_s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0

    def test_list_orders_pagination(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        for _ in range(5):
            self._create_order(client, buyer_token, sample_fabric)

        resp = client.get('/api/orders?page=1&per_page=2', headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_list_orders_descending_order(self, client, buyer_token, sample_fabric):
        """Orders should be returned in descending creation time order."""
        token, _ = buyer_token
        for _ in range(3):
            self._create_order(client, buyer_token, sample_fabric)

        resp = client.get('/api/orders', headers=_auth_header(token))
        data = resp.get_json()
        items = data['items']
        # IDs should be in descending order (later created = higher ID)
        for i in range(len(items) - 1):
            assert items[i]['id'] > items[i + 1]['id']

    def test_list_orders_no_auth(self, client):
        resp = client.get('/api/orders')
        assert resp.status_code == 401

    def test_list_orders_empty(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/orders', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []


class TestGetOrderDetail:
    """Tests for GET /api/orders/<id>."""

    def _create_order(self, client, buyer_token, fabric):
        """Helper to create an order and return its data."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': 5}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def test_get_order_detail_buyer(self, client, buyer_token, sample_fabric):
        token, _ = buyer_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == order_id
        assert data['status'] == 'pending'
        assert 'items' in data
        assert len(data['items']) == 1
        assert 'fabric' in data['items'][0]
        assert data['items'][0]['fabric']['id'] == sample_fabric.id
        assert 'buyer' in data
        assert 'supplier' in data
        assert 'timeline' in data

    def test_get_order_detail_supplier(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == order_id

    def test_get_order_detail_unauthorized(
        self, client, buyer_token, another_buyer_token, sample_fabric
    ):
        """A user who is neither buyer nor supplier cannot view the order."""
        other_token, _ = another_buyer_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(other_token))
        assert resp.status_code == 403

    def test_get_order_detail_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/orders/99999', headers=_auth_header(token))
        assert resp.status_code == 404

    def test_get_order_detail_no_auth(self, client):
        resp = client.get('/api/orders/1')
        assert resp.status_code == 401

    def test_order_detail_timeline(self, client, buyer_token, sample_fabric):
        """Timeline should show current status correctly."""
        token, _ = buyer_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(token))
        data = resp.get_json()
        timeline = data['timeline']
        assert len(timeline) == 6
        assert timeline[0]['status'] == 'pending'
        assert timeline[0]['completed'] is True
        assert timeline[0]['current'] is True
        assert timeline[1]['status'] == 'confirmed'
        assert timeline[1]['completed'] is False
        assert timeline[1]['current'] is False

    def test_order_detail_includes_fabric_info(self, client, buyer_token, sample_fabric):
        """Order detail items should include fabric information."""
        token, _ = buyer_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(token))
        data = resp.get_json()
        fabric_info = data['items'][0]['fabric']
        assert fabric_info['name'] == sample_fabric.name
        assert fabric_info['composition'] == sample_fabric.composition
        assert fabric_info['price'] == sample_fabric.price


class TestUpdateOrderStatus:
    """Tests for PUT /api/orders/<id>/status."""

    def _create_order(self, client, buyer_token, fabric):
        """Helper to create an order and return its data."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': 5}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def test_supplier_confirms_order(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'confirmed'

    def test_supplier_advances_to_producing(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # confirmed
        client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(s_token))

        # producing
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'producing',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'producing'

    def test_supplier_ships_order(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Advance to shipped
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        resp = client.get(f'/api/orders/{order_id}', headers=_auth_header(s_token))
        assert resp.get_json()['status'] == 'shipped'

    def test_buyer_confirms_received(self, client, buyer_token, supplier_token, sample_fabric):
        """Buyer can confirm 'received' status."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Supplier advances to shipped
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Buyer confirms received
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'received',
        }, headers=_auth_header(b_token))
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'received'

    def test_supplier_completes_order(self, client, buyer_token, supplier_token, sample_fabric):
        """Buyer can mark order as completed after received."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Advance through all statuses
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Buyer confirms received
        client.put(f'/api/orders/{order_id}/status', json={
            'status': 'received',
        }, headers=_auth_header(b_token))

        # Buyer completes
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'completed',
        }, headers=_auth_header(b_token))
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'completed'

    def test_invalid_status_transition(self, client, buyer_token, supplier_token, sample_fabric):
        """Cannot skip statuses."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Try to skip from pending to producing
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'producing',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_reverse_status_transition(self, client, buyer_token, supplier_token, sample_fabric):
        """Cannot go backwards in status."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Advance to confirmed
        client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(s_token))

        # Try to go back to pending
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'pending',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_buyer_cannot_confirm_order(self, client, buyer_token, sample_fabric):
        """Buyer cannot confirm order (only supplier can)."""
        b_token, _ = buyer_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(b_token))
        assert resp.status_code == 403

    def test_supplier_cannot_confirm_received(
        self, client, buyer_token, supplier_token, sample_fabric
    ):
        """Supplier cannot confirm 'received' (only buyer can)."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Advance to shipped
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Supplier tries to confirm received
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'received',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 403

    def test_update_status_order_not_found(self, client, supplier_token):
        s_token, _ = supplier_token
        resp = client.put('/api/orders/99999/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 404

    def test_update_status_missing_status(self, client, buyer_token, supplier_token, sample_fabric):
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.put(f'/api/orders/{order_id}/status', json={},
                          headers=_auth_header(s_token))
        assert resp.status_code == 400

    def test_update_status_no_auth(self, client):
        resp = client.put('/api/orders/1/status', json={'status': 'confirmed'})
        assert resp.status_code == 401

    def test_wrong_supplier_cannot_update(
        self, client, buyer_token, supplier_token, another_supplier_token, sample_fabric
    ):
        """A different supplier cannot update the order status."""
        other_s_token, _ = another_supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
        }, headers=_auth_header(other_s_token))
        assert resp.status_code == 403

    def test_shipped_with_tracking_no(self, client, buyer_token, supplier_token, sample_fabric):
        """Tracking number should be stored when transitioning to shipped."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Advance to producing
        for status in ['confirmed', 'producing']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Ship with tracking number
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'shipped',
            'tracking_no': 'SF1234567890',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'shipped'
        assert data['tracking_no'] == 'SF1234567890'

    def test_shipped_without_tracking_no(self, client, buyer_token, supplier_token, sample_fabric):
        """Shipping without tracking number should still succeed."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        for status in ['confirmed', 'producing']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'shipped',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'shipped'
        assert resp.get_json()['tracking_no'] is None

    def test_tracking_no_ignored_for_non_shipped(self, client, buyer_token, supplier_token, sample_fabric):
        """Tracking number in request body should be ignored for non-shipped transitions."""
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'confirmed',
            'tracking_no': 'SF9999999999',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 200
        assert resp.get_json()['tracking_no'] is None

    def test_buyer_can_complete_order(self, client, buyer_token, supplier_token, sample_fabric):
        """Buyer should be able to transition from received to completed."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Supplier advances to shipped
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Buyer confirms received
        client.put(f'/api/orders/{order_id}/status', json={
            'status': 'received',
        }, headers=_auth_header(b_token))

        # Buyer completes
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'completed',
        }, headers=_auth_header(b_token))
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'completed'

    def test_supplier_cannot_complete_order(self, client, buyer_token, supplier_token, sample_fabric):
        """Supplier should not be able to transition to completed (only buyer can)."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token
        order_data = self._create_order(client, buyer_token, sample_fabric)
        order_id = order_data['id']

        # Supplier advances to shipped
        for status in ['confirmed', 'producing', 'shipped']:
            client.put(f'/api/orders/{order_id}/status', json={
                'status': status,
            }, headers=_auth_header(s_token))

        # Buyer confirms received
        client.put(f'/api/orders/{order_id}/status', json={
            'status': 'received',
        }, headers=_auth_header(b_token))

        # Supplier tries to complete — should be forbidden
        resp = client.put(f'/api/orders/{order_id}/status', json={
            'status': 'completed',
        }, headers=_auth_header(s_token))
        assert resp.status_code == 403


class TestListOrdersEnhanced:
    """Tests for enhanced GET /api/orders with admin role, status filter, and enriched response.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 9.3
    """

    @pytest.fixture
    def admin_token(self, client):
        """Create an admin user and return their JWT token and user ID."""
        user = User(phone='13800138099', role='admin', company_name='平台管理')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def buyer_with_company(self, client):
        """Create a buyer user with company_name and return their JWT token and user ID."""
        user = User(phone='13800138010', role='buyer', company_name='采购公司A')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def supplier_with_company(self, client):
        """Create a supplier user with company_name and return their JWT token and user ID."""
        user = User(phone='13800138011', role='supplier', company_name='供应商公司B')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def fabric_for_supplier(self, client, supplier_with_company):
        """Create a fabric for the supplier_with_company."""
        _, supplier_id = supplier_with_company
        fabric = Fabric(
            supplier_id=supplier_id,
            name='增强测试面料',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            color='白色',
            price=25.0,
            stock_quantity=10000,
            status='active',
        )
        _db.session.add(fabric)
        _db.session.commit()
        return fabric

    def _create_fabric_order(self, client, buyer_token, fabric):
        """Helper to create a fabric-based order (no demand/quote)."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': 5}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def _create_demand_order(self, client, buyer_id, supplier_id, demand_title='测试需求',
                             quote_price=30.0, quantity=100):
        """Helper to create an order linked to a demand and quote."""
        from server.models.demand import Demand, Quote
        from server.models.order import generate_order_no

        demand = Demand(
            buyer_id=buyer_id,
            title=demand_title,
            composition='100%棉',
            quantity=quantity,
            status='closed',
        )
        _db.session.add(demand)
        _db.session.flush()

        quote = Quote(
            demand_id=demand.id,
            supplier_id=supplier_id,
            price=quote_price,
            delivery_days=7,
            status='accepted',
        )
        _db.session.add(quote)
        _db.session.flush()

        order = Order(
            buyer_id=buyer_id,
            supplier_id=supplier_id,
            order_no=generate_order_no(),
            total_amount=quote_price * quantity,
            address='上海市浦东新区',
            status='pending',
            demand_id=demand.id,
            quote_id=quote.id,
        )
        _db.session.add(order)
        _db.session.commit()
        return order

    # --- Admin role tests ---

    def test_admin_sees_all_orders(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier, admin_token
    ):
        """Admin should see all orders regardless of buyer/supplier."""
        # Create an order as buyer
        self._create_fabric_order(client, buyer_with_company, fabric_for_supplier)

        admin_tok, _ = admin_token
        resp = client.get('/api/orders', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_admin_sees_multiple_buyers_orders(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier, admin_token
    ):
        """Admin should see orders from different buyers."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        # Create orders via demand for the first buyer
        self._create_demand_order(client, buyer_id, supplier_id, '需求A')

        # Create another buyer and their order
        buyer2 = User(phone='13800138012', role='buyer', company_name='采购公司C')
        buyer2.set_password('testpass123')
        _db.session.add(buyer2)
        _db.session.commit()
        self._create_demand_order(client, buyer2.id, supplier_id, '需求B')

        admin_tok, _ = admin_token
        resp = client.get('/api/orders', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2

    # --- Status filter tests ---

    def test_status_filter_returns_matching_orders(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier
    ):
        """Status filter should return only orders with matching status."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        # Create two orders: one pending, one confirmed
        self._create_demand_order(client, buyer_id, supplier_id, '需求1')
        order2 = self._create_demand_order(client, buyer_id, supplier_id, '需求2')
        order2.status = 'confirmed'
        _db.session.commit()

        resp = client.get('/api/orders?status=confirmed', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['status'] == 'confirmed'

    def test_status_filter_returns_empty_when_no_match(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Status filter should return empty when no orders match."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id)

        resp = client.get('/api/orders?status=shipped', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0

    def test_admin_status_filter(
        self, client, buyer_with_company, supplier_with_company, admin_token
    ):
        """Admin can also use status filter."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id, '需求1')
        order2 = self._create_demand_order(client, buyer_id, supplier_id, '需求2')
        order2.status = 'producing'
        _db.session.commit()

        admin_tok, _ = admin_token
        resp = client.get('/api/orders?status=producing', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['status'] == 'producing'

    # --- Enhanced response fields tests ---

    def test_demand_title_included_in_response(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order list items should include demand_title when demand is linked."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id, '高端棉布采购需求')

        resp = client.get('/api/orders', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['demand_title'] == '高端棉布采购需求'

    def test_quote_price_included_in_response(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order list items should include quote_price when quote is linked."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id, quote_price=45.5)

        resp = client.get('/api/orders', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['quote_price'] == 45.5

    def test_counterparty_for_buyer_is_supplier_company(
        self, client, buyer_with_company, supplier_with_company
    ):
        """For buyer, counterparty should be the supplier's company_name."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id)

        resp = client.get('/api/orders', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'][0]['counterparty'] == '供应商公司B'

    def test_counterparty_for_supplier_is_buyer_company(
        self, client, buyer_with_company, supplier_with_company
    ):
        """For supplier, counterparty should be the buyer's company_name."""
        _, buyer_id = buyer_with_company
        supplier_tok, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id)

        resp = client.get('/api/orders', headers=_auth_header(supplier_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'][0]['counterparty'] == '采购公司A'

    def test_counterparty_for_admin_includes_both(
        self, client, buyer_with_company, supplier_with_company, admin_token
    ):
        """For admin, counterparty should include both buyer and supplier company names."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company

        self._create_demand_order(client, buyer_id, supplier_id)

        admin_tok, _ = admin_token
        resp = client.get('/api/orders', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        counterparty = data['items'][0]['counterparty']
        assert isinstance(counterparty, dict)
        assert counterparty['buyer_company_name'] == '采购公司A'
        assert counterparty['supplier_company_name'] == '供应商公司B'

    # --- Backward compatibility tests ---

    def test_fabric_order_has_null_demand_title_and_quote_price(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier
    ):
        """Fabric-based orders (no demand/quote) should have null demand_title and quote_price."""
        buyer_tok, _ = buyer_with_company
        self._create_fabric_order(client, buyer_with_company, fabric_for_supplier)

        resp = client.get('/api/orders', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['demand_title'] is None
        assert data['items'][0]['quote_price'] is None

    def test_fabric_order_still_has_counterparty(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier
    ):
        """Fabric-based orders should still include counterparty info."""
        buyer_tok, _ = buyer_with_company
        self._create_fabric_order(client, buyer_with_company, fabric_for_supplier)

        resp = client.get('/api/orders', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'][0]['counterparty'] == '供应商公司B'


class TestGetOrderDetailEnhanced:
    """Tests for enhanced GET /api/orders/<id> with admin access and demand/quote info.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    @pytest.fixture
    def admin_token(self, client):
        """Create an admin user and return their JWT token and user ID."""
        user = User(phone='13800139001', role='admin', company_name='平台管理')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def buyer_with_company(self, client):
        """Create a buyer user with company_name."""
        user = User(phone='13800139010', role='buyer', company_name='采购公司X')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def supplier_with_company(self, client):
        """Create a supplier user with company_name."""
        user = User(phone='13800139011', role='supplier', company_name='供应商公司Y')
        user.set_password('testpass123')
        _db.session.add(user)
        _db.session.commit()
        token = create_access_token(identity=str(user.id))
        return token, user.id

    @pytest.fixture
    def fabric_for_supplier(self, client, supplier_with_company):
        """Create a fabric for the supplier_with_company."""
        _, supplier_id = supplier_with_company
        fabric = Fabric(
            supplier_id=supplier_id,
            name='详情测试面料',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            color='白色',
            price=25.0,
            stock_quantity=10000,
            status='active',
        )
        _db.session.add(fabric)
        _db.session.commit()
        return fabric

    def _create_fabric_order(self, client, buyer_token, fabric):
        """Helper to create a fabric-based order (no demand/quote)."""
        token, _ = buyer_token
        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': 5}],
            'address': '上海市浦东新区',
        }, headers=_auth_header(token))
        return resp.get_json()

    def _create_demand_order(self, buyer_id, supplier_id, demand_title='测试需求',
                             demand_composition='100%棉', demand_quantity=100,
                             quote_price=30.0, quote_delivery_days=7,
                             quote_message='优质面料，保证质量'):
        """Helper to create an order linked to a demand and quote."""
        from server.models.demand import Demand, Quote
        from server.models.order import generate_order_no

        demand = Demand(
            buyer_id=buyer_id,
            title=demand_title,
            composition=demand_composition,
            quantity=demand_quantity,
            status='closed',
        )
        _db.session.add(demand)
        _db.session.flush()

        quote = Quote(
            demand_id=demand.id,
            supplier_id=supplier_id,
            price=quote_price,
            delivery_days=quote_delivery_days,
            message=quote_message,
            status='accepted',
        )
        _db.session.add(quote)
        _db.session.flush()

        order = Order(
            buyer_id=buyer_id,
            supplier_id=supplier_id,
            order_no=generate_order_no(),
            total_amount=quote_price * demand_quantity,
            address='上海市浦东新区',
            status='pending',
            demand_id=demand.id,
            quote_id=quote.id,
        )
        _db.session.add(order)
        _db.session.commit()
        return order

    # --- Admin access tests ---

    def test_admin_can_view_any_order(
        self, client, buyer_with_company, supplier_with_company, admin_token
    ):
        """Admin should be able to view any order detail."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(buyer_id, supplier_id)

        admin_tok, _ = admin_token
        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == order.id

    def test_admin_sees_full_order_detail(
        self, client, buyer_with_company, supplier_with_company, admin_token
    ):
        """Admin should see all detail fields including buyer, supplier, timeline."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(buyer_id, supplier_id)

        admin_tok, _ = admin_token
        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'buyer' in data
        assert 'supplier' in data
        assert 'timeline' in data
        assert 'demand_info' in data
        assert 'quote_info' in data

    def test_non_participant_non_admin_forbidden(
        self, client, buyer_with_company, supplier_with_company
    ):
        """A user who is not buyer, supplier, or admin should get 403."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(buyer_id, supplier_id)

        # Create a random other user
        other_user = User(phone='13800139099', role='buyer', company_name='其他公司')
        other_user.set_password('testpass123')
        _db.session.add(other_user)
        _db.session.commit()
        other_token = create_access_token(identity=str(other_user.id))

        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(other_token))
        assert resp.status_code == 403

    # --- Demand info tests ---

    def test_demand_info_included_when_linked(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order detail should include demand_info when demand is linked."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(
            buyer_id, supplier_id,
            demand_title='高端棉布采购',
            demand_composition='80%棉20%涤纶',
            demand_quantity=200,
        )

        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['demand_info'] is not None
        assert data['demand_info']['title'] == '高端棉布采购'
        assert data['demand_info']['quantity'] == 200
        assert data['demand_info']['composition'] == '80%棉20%涤纶'

    def test_demand_info_null_when_not_linked(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier
    ):
        """Order detail should have null demand_info for fabric-based orders."""
        buyer_tok, _ = buyer_with_company
        order_data = self._create_fabric_order(client, buyer_with_company, fabric_for_supplier)

        resp = client.get(f'/api/orders/{order_data["id"]}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['demand_info'] is None

    # --- Quote info tests ---

    def test_quote_info_included_when_linked(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order detail should include quote_info when quote is linked."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(
            buyer_id, supplier_id,
            quote_price=45.5,
            quote_delivery_days=14,
            quote_message='快速交货，品质保证',
        )

        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['quote_info'] is not None
        assert data['quote_info']['price'] == 45.5
        assert data['quote_info']['delivery_days'] == 14
        assert data['quote_info']['message'] == '快速交货，品质保证'

    def test_quote_info_null_when_not_linked(
        self, client, buyer_with_company, supplier_with_company, fabric_for_supplier
    ):
        """Order detail should have null quote_info for fabric-based orders."""
        buyer_tok, _ = buyer_with_company
        order_data = self._create_fabric_order(client, buyer_with_company, fabric_for_supplier)

        resp = client.get(f'/api/orders/{order_data["id"]}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['quote_info'] is None

    # --- Tracking number tests ---

    def test_tracking_no_in_response(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order detail should include tracking_no field."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(buyer_id, supplier_id)
        order.tracking_no = 'SF1234567890'
        _db.session.commit()

        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['tracking_no'] == 'SF1234567890'

    def test_tracking_no_null_when_not_set(
        self, client, buyer_with_company, supplier_with_company
    ):
        """Order detail should have null tracking_no when not set."""
        buyer_tok, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(buyer_id, supplier_id)

        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(buyer_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['tracking_no'] is None

    # --- Admin with demand/quote info ---

    def test_admin_sees_demand_and_quote_info(
        self, client, buyer_with_company, supplier_with_company, admin_token
    ):
        """Admin should see demand_info and quote_info in order detail."""
        _, buyer_id = buyer_with_company
        _, supplier_id = supplier_with_company
        order = self._create_demand_order(
            buyer_id, supplier_id,
            demand_title='管理员查看需求',
            quote_price=55.0,
            quote_delivery_days=10,
            quote_message='管理员测试报价',
        )

        admin_tok, _ = admin_token
        resp = client.get(f'/api/orders/{order.id}', headers=_auth_header(admin_tok))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['demand_info']['title'] == '管理员查看需求'
        assert data['quote_info']['price'] == 55.0
        assert data['quote_info']['delivery_days'] == 10
        assert data['quote_info']['message'] == '管理员测试报价'
