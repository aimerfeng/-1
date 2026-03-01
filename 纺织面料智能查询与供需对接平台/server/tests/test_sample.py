"""Property-based tests for sample management module.

**Feature: textile-fabric-platform**
**Validates: Requirements 6.1, 6.2**

Uses Hypothesis to verify:
- Property 15: 样品申请创建与状态转换
"""

import threading

from flask_jwt_extended import create_access_token
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from server.extensions import db as _db
from server.models.fabric import Fabric
from server.models.message import Message
from server.models.sample import Sample
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
    # Format: 17XXXXXXXXX where X is zero-padded counter
    return f'17{counter:09d}'


def _create_buyer_and_token(db_session):
    """Create a buyer user and return (user, access_token)."""
    phone = _unique_phone()
    buyer = User(phone=phone, role='buyer')
    db_session.add(buyer)
    db_session.commit()
    token = create_access_token(identity=str(buyer.id))
    return buyer, token


def _create_supplier_and_token(db_session):
    """Create a supplier user and return (user, access_token)."""
    phone = _unique_phone()
    supplier = User(phone=phone, role='supplier')
    db_session.add(supplier)
    db_session.commit()
    token = create_access_token(identity=str(supplier.id))
    return supplier, token


def _create_fabric(db_session, supplier_id):
    """Create a fabric record owned by the given supplier."""
    fabric = Fabric(
        supplier_id=supplier_id,
        name='PBT测试面料',
        composition='100%棉',
        weight=180.0,
        width=150.0,
        craft='平纹',
        color='白色',
        price=25.0,
        status='active',
    )
    db_session.add(fabric)
    db_session.commit()
    return fabric


# Hypothesis strategies for sample request fields
_quantity_st = st.integers(min_value=1, max_value=10000)

_address_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != '')

_reject_reason_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != '')


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


# ===========================================================================
# Property 15: 样品申请创建与状态转换
# ===========================================================================


class TestSampleRequestStatusTransitionProperty:
    """Property 15: 样品申请创建与状态转换

    **Feature: textile-fabric-platform, Property 15: 样品申请创建与状态转换**
    **Validates: Requirements 6.1, 6.2**

    For any sample request, after creation the status should be 'pending'.
    After supplier approval the status should change (approved or shipping
    due to logistics trigger). After rejection the status should be
    'rejected' and reject_reason should be set.
    """

    @given(
        quantity=_quantity_st,
        address=_address_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_created_sample_has_pending_status(self, client, quantity, address):
        """Creating a sample request should set status to 'pending'.

        **Validates: Requirements 6.1**
        """
        # Setup: create buyer, supplier, and fabric
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier, supplier_token = _create_supplier_and_token(_db.session)
        fabric = _create_fabric(_db.session, supplier.id)

        # Create sample via API
        resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': quantity,
            'address': address,
        }, headers=_auth_header(buyer_token))

        assert resp.status_code == 201, f"Create failed: {resp.get_json()}"
        data = resp.get_json()

        # Verify initial status is 'pending'
        assert data['status'] == 'pending', (
            f"Expected status 'pending' after creation, got '{data['status']}'"
        )
        assert data['fabric_id'] == fabric.id
        assert data['buyer_id'] == buyer.id
        assert data['supplier_id'] == supplier.id
        assert data['quantity'] == quantity
        assert data['address'] == address.strip()

        # Cleanup: delete messages first to avoid FK constraint violations
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        sample = _db.session.get(Sample, data['id'])
        if sample:
            _db.session.delete(sample)
        _db.session.delete(fabric)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()

    @given(
        quantity=_quantity_st,
        address=_address_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_approved_sample_status_changes(self, client, quantity, address):
        """Approving a sample should change status from 'pending' to 'approved'
        or 'shipping' (due to logistics trigger).

        **Validates: Requirements 6.2**
        """
        # Setup
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier, supplier_token = _create_supplier_and_token(_db.session)
        fabric = _create_fabric(_db.session, supplier.id)

        # Create sample
        create_resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': quantity,
            'address': address,
        }, headers=_auth_header(buyer_token))
        assert create_resp.status_code == 201
        sample_id = create_resp.get_json()['id']

        # Supplier approves the sample
        review_resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'approved',
        }, headers=_auth_header(supplier_token))
        assert review_resp.status_code == 200

        review_data = review_resp.get_json()
        # After approval, logistics creation is triggered, so status may be
        # 'approved' or 'shipping' depending on logistics success
        assert review_data['status'] in ('approved', 'shipping'), (
            f"Expected status 'approved' or 'shipping' after approval, "
            f"got '{review_data['status']}'"
        )

        # Cleanup: delete messages first to avoid FK constraint violations
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        sample = _db.session.get(Sample, sample_id)
        if sample:
            _db.session.delete(sample)
        _db.session.delete(fabric)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()

    @given(
        quantity=_quantity_st,
        address=_address_st,
        reject_reason=_reject_reason_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_rejected_sample_status_and_reason(self, client, quantity, address, reject_reason):
        """Rejecting a sample should set status to 'rejected' and record the
        reject_reason.

        **Validates: Requirements 6.2**
        """
        # Setup
        buyer, buyer_token = _create_buyer_and_token(_db.session)
        supplier, supplier_token = _create_supplier_and_token(_db.session)
        fabric = _create_fabric(_db.session, supplier.id)

        # Create sample
        create_resp = client.post('/api/samples', json={
            'fabric_id': fabric.id,
            'quantity': quantity,
            'address': address,
        }, headers=_auth_header(buyer_token))
        assert create_resp.status_code == 201
        sample_id = create_resp.get_json()['id']

        # Supplier rejects the sample
        review_resp = client.put(f'/api/samples/{sample_id}/review', json={
            'status': 'rejected',
            'reject_reason': reject_reason,
        }, headers=_auth_header(supplier_token))
        assert review_resp.status_code == 200

        review_data = review_resp.get_json()
        assert review_data['status'] == 'rejected', (
            f"Expected status 'rejected' after rejection, "
            f"got '{review_data['status']}'"
        )
        assert review_data['reject_reason'] == reject_reason.strip(), (
            f"Expected reject_reason '{reject_reason.strip()}', "
            f"got '{review_data['reject_reason']}'"
        )

        # Cleanup: delete messages first to avoid FK constraint violations
        Message.query.filter(
            Message.user_id.in_([buyer.id, supplier.id])
        ).delete(synchronize_session=False)
        sample = _db.session.get(Sample, sample_id)
        if sample:
            _db.session.delete(sample)
        _db.session.delete(fabric)
        _db.session.delete(buyer)
        _db.session.delete(supplier)
        _db.session.commit()
