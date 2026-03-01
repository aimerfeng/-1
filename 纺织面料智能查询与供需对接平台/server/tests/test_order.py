"""Property-based tests for order management module.

**Feature: textile-fabric-platform**
**Validates: Requirements 7.3, 7.6**

Uses Hypothesis to verify:
- Property 17: 订单状态机合法性
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from server.models.order import ORDER_STATUSES, validate_status_transition


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy that draws a valid status from the ORDER_STATUSES list
_valid_status_st = st.sampled_from(ORDER_STATUSES)

# Strategy that generates arbitrary strings (including potentially invalid ones)
_arbitrary_string_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
    min_size=0,
    max_size=50,
)


# ===========================================================================
# Property 17: 订单状态机合法性
# ===========================================================================


class TestOrderStatusMachineProperty:
    """Property 17: 订单状态机合法性

    **Feature: textile-fabric-platform, Property 17: 订单状态机合法性**
    **Validates: Requirements 7.3, 7.6**

    For any order, status transitions may only follow the sequence:
    pending → confirmed → producing → shipped → received → completed.
    Any jump or reverse transition must be rejected.
    """

    # -----------------------------------------------------------------------
    # Sub-property 1: Adjacent (index+1) transitions are the ONLY valid ones
    # -----------------------------------------------------------------------

    @given(current=_valid_status_st, next_status=_valid_status_st)
    @settings(max_examples=100, deadline=None)
    def test_only_sequential_transitions_are_valid(self, current, next_status):
        """For any pair of valid statuses, validate_status_transition returns
        True if and only if next_status is the immediate successor of current.

        **Validates: Requirements 7.3, 7.6**
        """
        current_idx = ORDER_STATUSES.index(current)
        next_idx = ORDER_STATUSES.index(next_status)

        result = validate_status_transition(current, next_status)

        if next_idx == current_idx + 1:
            assert result is True, (
                f"Expected transition {current!r} → {next_status!r} to be VALID "
                f"(indices {current_idx} → {next_idx})"
            )
        else:
            assert result is False, (
                f"Expected transition {current!r} → {next_status!r} to be INVALID "
                f"(indices {current_idx} → {next_idx})"
            )

    # -----------------------------------------------------------------------
    # Sub-property 2: Invalid / unknown statuses are always rejected
    # -----------------------------------------------------------------------

    @given(current=_arbitrary_string_st, next_status=_arbitrary_string_st)
    @settings(max_examples=100, deadline=None)
    def test_invalid_statuses_are_rejected(self, current, next_status):
        """For any pair of arbitrary strings where at least one is not a
        recognised status, the transition must be rejected.

        **Validates: Requirements 7.3, 7.6**
        """
        if current not in ORDER_STATUSES or next_status not in ORDER_STATUSES:
            result = validate_status_transition(current, next_status)
            assert result is False, (
                f"Expected transition with invalid status to be rejected: "
                f"{current!r} → {next_status!r}"
            )

    # -----------------------------------------------------------------------
    # Sub-property 3: Walking a random sequence through the state machine
    # -----------------------------------------------------------------------

    @given(
        transition_sequence=st.lists(
            _valid_status_st,
            min_size=2,
            max_size=20,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_random_transition_sequences(self, transition_sequence):
        """For any random sequence of statuses, each consecutive pair is valid
        only when it follows the strict sequential order.

        **Validates: Requirements 7.3, 7.6**
        """
        for i in range(len(transition_sequence) - 1):
            current = transition_sequence[i]
            next_status = transition_sequence[i + 1]

            current_idx = ORDER_STATUSES.index(current)
            next_idx = ORDER_STATUSES.index(next_status)

            result = validate_status_transition(current, next_status)
            expected = next_idx == current_idx + 1

            assert result == expected, (
                f"Sequence step {i}: {current!r} → {next_status!r} "
                f"returned {result}, expected {expected} "
                f"(indices {current_idx} → {next_idx})"
            )


# ===========================================================================
# Property 16: 订单创建往返
# ===========================================================================

import threading

from flask_jwt_extended import create_access_token
from hypothesis import HealthCheck

from server.extensions import db as _db
from server.models.fabric import Fabric
from server.models.message import Message
from server.models.order import Order, OrderItem
from server.models.user import User


# Thread-safe counter for generating unique phone numbers within a test run
_phone_counter = 0
_phone_lock = threading.Lock()


def _unique_phone():
    """Generate a unique valid Chinese phone number for testing."""
    global _phone_counter
    with _phone_lock:
        _phone_counter += 1
        counter = _phone_counter
    # Format: 18XXXXXXXXX where X is zero-padded counter
    return f'18{counter:09d}'


def _create_buyer_and_token(db_session):
    """Create a buyer user and return (user, access_token)."""
    phone = _unique_phone()
    buyer = User(phone=phone, role='buyer')
    db_session.add(buyer)
    db_session.commit()
    token = create_access_token(identity=str(buyer.id))
    return buyer, token


def _create_supplier(db_session):
    """Create a supplier user and return user."""
    phone = _unique_phone()
    supplier = User(phone=phone, role='supplier')
    db_session.add(supplier)
    db_session.commit()
    return supplier


def _create_fabric(db_session, supplier_id, price=25.0):
    """Create a fabric record owned by the given supplier."""
    fabric = Fabric(
        supplier_id=supplier_id,
        name='PBT测试面料',
        composition='100%棉',
        weight=180.0,
        width=150.0,
        craft='平纹',
        color='白色',
        price=price,
        stock_quantity=100000,
        status='active',
    )
    db_session.add(fabric)
    db_session.commit()
    return fabric


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


def _cleanup_order(db_session, order_id):
    """Delete order items, related messages, and order by order id."""
    OrderItem.query.filter_by(order_id=order_id).delete()
    order = db_session.get(Order, order_id)
    if order:
        # Delete messages related to this order
        Message.query.filter_by(ref_id=order_id, ref_type='order').delete()
        db_session.delete(order)
    db_session.commit()


# Hypothesis strategies for order creation fields
_quantity_st = st.integers(min_value=1, max_value=10000)

_price_st = st.floats(
    min_value=0.01,
    max_value=99999.0,
    allow_nan=False,
    allow_infinity=False,
).map(lambda x: round(x, 2))

_address_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != '')

_num_items_st = st.integers(min_value=1, max_value=5)


class TestOrderCreationRoundTripProperty:
    """Property 16: 订单创建往返

    **Feature: textile-fabric-platform, Property 16: 订单创建往返**
    **Validates: Requirements 7.1, 7.2**

    For any valid order data (containing fabrics, quantities, price, and
    delivery address), creating an order and then querying by ID should
    return consistent information. For data missing required fields,
    creation should fail.
    """

    # -----------------------------------------------------------------------
    # Sub-property 1: Valid order creation round-trip
    # -----------------------------------------------------------------------

    @given(
        quantity=_quantity_st,
        price=_price_st,
        address=_address_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_created_order_can_be_retrieved_with_consistent_data(
        self, client, quantity, price, address,
    ):
        """For any valid order data, creating an order and then retrieving it
        by ID should return consistent information (address, items, amounts).

        **Validates: Requirements 7.1, 7.2**
        """
        # Setup: create buyer, supplier, and fabric
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier = _create_supplier(_db.session)
        fabric = _create_fabric(_db.session, supplier.id, price=price)

        # Create order via API
        create_resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': quantity}],
            'address': address,
        }, headers=_auth_header(buyer_token))

        assert create_resp.status_code == 201, (
            f"Order creation failed: {create_resp.get_json()}"
        )
        create_data = create_resp.get_json()
        order_id = create_data['id']

        # The server strips whitespace from address
        expected_address = address.strip()

        # Verify creation response fields
        assert create_data['buyer_id'] == buyer.id
        assert create_data['supplier_id'] == supplier.id
        assert create_data['address'] == expected_address
        assert create_data['status'] == 'pending'
        assert len(create_data['items']) == 1
        assert create_data['items'][0]['fabric_id'] == fabric.id
        assert create_data['items'][0]['quantity'] == quantity

        # Verify total_amount = quantity * price
        expected_total = quantity * price
        assert abs(create_data['total_amount'] - expected_total) < 0.01, (
            f"Expected total_amount ~{expected_total}, got {create_data['total_amount']}"
        )

        # Retrieve order via GET /api/orders/<id>
        get_resp = client.get(
            f'/api/orders/{order_id}',
            headers=_auth_header(buyer_token),
        )
        assert get_resp.status_code == 200, (
            f"Order retrieval failed: {get_resp.get_json()}"
        )
        get_data = get_resp.get_json()

        # Verify round-trip consistency
        assert get_data['id'] == order_id
        assert get_data['buyer_id'] == buyer.id
        assert get_data['supplier_id'] == supplier.id
        assert get_data['address'] == expected_address
        assert get_data['status'] == 'pending'
        assert abs(get_data['total_amount'] - expected_total) < 0.01

        # Verify items in detail response
        assert len(get_data['items']) == 1
        item = get_data['items'][0]
        assert item['fabric_id'] == fabric.id
        assert item['quantity'] == quantity
        assert abs(item['unit_price'] - price) < 0.01
        assert abs(item['subtotal'] - expected_total) < 0.01

        # Cleanup
        _cleanup_order(_db.session, order_id)
        _db.session.delete(fabric)
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()

    # -----------------------------------------------------------------------
    # Sub-property 2: Multi-item order round-trip
    # -----------------------------------------------------------------------

    @given(
        quantities=st.lists(
            _quantity_st,
            min_size=2,
            max_size=4,
        ),
        address=_address_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_multi_item_order_round_trip(self, client, quantities, address):
        """For any valid multi-item order (all from same supplier), creating
        and retrieving should return consistent items and total amount.

        **Validates: Requirements 7.1, 7.2**
        """
        # Setup: create buyer, supplier, and multiple fabrics
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier = _create_supplier(_db.session)

        fabrics = []
        items_payload = []
        expected_total = 0.0
        for qty in quantities:
            fabric = _create_fabric(_db.session, supplier.id, price=25.0)
            fabrics.append(fabric)
            items_payload.append({
                'fabric_id': fabric.id,
                'quantity': qty,
            })
            expected_total += qty * 25.0

        # Create order via API
        create_resp = client.post('/api/orders', json={
            'items': items_payload,
            'address': address,
        }, headers=_auth_header(buyer_token))

        assert create_resp.status_code == 201, (
            f"Multi-item order creation failed: {create_resp.get_json()}"
        )
        create_data = create_resp.get_json()
        order_id = create_data['id']

        assert len(create_data['items']) == len(quantities)
        assert abs(create_data['total_amount'] - expected_total) < 0.01

        # Retrieve and verify
        get_resp = client.get(
            f'/api/orders/{order_id}',
            headers=_auth_header(buyer_token),
        )
        assert get_resp.status_code == 200
        get_data = get_resp.get_json()

        assert len(get_data['items']) == len(quantities)
        assert abs(get_data['total_amount'] - expected_total) < 0.01

        # Verify each item matches
        retrieved_items = sorted(get_data['items'], key=lambda x: x['fabric_id'])
        expected_items = sorted(
            zip(fabrics, quantities),
            key=lambda x: x[0].id,
        )
        for (fabric, qty), item in zip(expected_items, retrieved_items):
            assert item['fabric_id'] == fabric.id
            assert item['quantity'] == qty

        # Cleanup
        _cleanup_order(_db.session, order_id)
        for f in fabrics:
            _db.session.delete(f)
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()

    # -----------------------------------------------------------------------
    # Sub-property 3: Missing required fields should fail
    # -----------------------------------------------------------------------

    @given(address=_address_st)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_missing_items_field_fails(self, client, address):
        """Creating an order without the 'items' field should return 400.

        **Validates: Requirements 7.2**
        """
        buyer, buyer_token = _create_buyer_and_token(_db.session)

        resp = client.post('/api/orders', json={
            'address': address,
        }, headers=_auth_header(buyer_token))

        assert resp.status_code == 400, (
            f"Expected 400 for missing items, got {resp.status_code}"
        )

        # Cleanup
        Message.query.filter_by(user_id=buyer.id).delete()
        _db.session.delete(buyer)
        _db.session.commit()

    @given(quantity=_quantity_st)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_missing_address_field_fails(self, client, quantity):
        """Creating an order without the 'address' field should return 400.

        **Validates: Requirements 7.2**
        """
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier = _create_supplier(_db.session)
        fabric = _create_fabric(_db.session, supplier.id)

        resp = client.post('/api/orders', json={
            'items': [{'fabric_id': fabric.id, 'quantity': quantity}],
        }, headers=_auth_header(buyer_token))

        assert resp.status_code == 400, (
            f"Expected 400 for missing address, got {resp.status_code}"
        )

        # Cleanup
        _db.session.delete(fabric)
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()

    @given(address=_address_st)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_empty_items_list_fails(self, client, address):
        """Creating an order with an empty items list should return 400.

        **Validates: Requirements 7.2**
        """
        buyer, buyer_token = _create_buyer_and_token(_db.session)

        resp = client.post('/api/orders', json={
            'items': [],
            'address': address,
        }, headers=_auth_header(buyer_token))

        assert resp.status_code == 400, (
            f"Expected 400 for empty items, got {resp.status_code}"
        )

        # Cleanup
        Message.query.filter_by(user_id=buyer.id).delete()
        _db.session.delete(buyer)
        _db.session.commit()
