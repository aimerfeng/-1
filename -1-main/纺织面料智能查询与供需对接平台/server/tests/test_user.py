"""Property-based tests for user profile module.

**Feature: textile-fabric-platform**
**Validates: Requirements 2.6, 9.1**

Uses Hypothesis to verify:
- Property 5: Certification status transition after admin approval
- Property 20: User profile update round-trip
"""

import threading

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from server.extensions import db as _db
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
    # Format: 15XXXXXXXXX where X is zero-padded counter
    return f'15{counter:09d}'


# Hypothesis strategies for profile fields with valid constraints
# company_name: max 200 chars, non-empty
_company_name_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != '')

# contact_name: max 100 chars, non-empty
_contact_name_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != '')

# address: max 500 chars, non-empty
_address_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=500,
).filter(lambda s: s.strip() != '')


# ===========================================================================
# Property 20: 用户资料更新往返
# ===========================================================================


class TestUserProfileUpdateRoundTripProperty:
    """Property 20: 用户资料更新往返

    **Feature: textile-fabric-platform, Property 20: 用户资料更新往返**
    **Validates: Requirements 9.1**

    For any valid user profile update data, after updating via PUT /api/auth/profile,
    querying via GET /api/auth/profile should return the updated values.
    """

    @given(
        company_name=_company_name_st,
        contact_name=_contact_name_st,
        address=_address_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_profile_update_round_trip(
        self, app_context, client, company_name, contact_name, address
    ):
        """Updating profile fields and then reading them back should return the updated values.

        **Validates: Requirements 9.1**
        """
        phone = _unique_phone()
        password = 'testpass123'

        # 1. Create a user
        user = User(phone=phone, role='buyer')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # 2. Login to get JWT token
        login_resp = client.post('/api/auth/login', json={
            'phone': phone,
            'password': password,
        })
        assert login_resp.status_code == 200
        token = login_resp.get_json()['token']
        auth_header = {'Authorization': f'Bearer {token}'}

        # 3. PUT /api/auth/profile with random valid data
        update_data = {
            'company_name': company_name,
            'contact_name': contact_name,
            'address': address,
        }
        put_resp = client.put(
            '/api/auth/profile',
            json=update_data,
            headers=auth_header,
        )
        assert put_resp.status_code == 200

        # 4. GET /api/auth/profile and verify the returned values match
        get_resp = client.get('/api/auth/profile', headers=auth_header)
        assert get_resp.status_code == 200

        profile = get_resp.get_json()['user']
        assert profile['company_name'] == company_name
        assert profile['contact_name'] == contact_name
        assert profile['address'] == address

        # Clean up to avoid accumulation across iterations
        user = _db.session.get(User, user_id)
        if user:
            _db.session.delete(user)
            _db.session.commit()


# ---------------------------------------------------------------------------
# Additional imports for Property 21
# ---------------------------------------------------------------------------
from flask_jwt_extended import create_access_token
from server.models.fabric import Fabric, Favorite

# Hypothesis strategies for fabric data
_fabric_name_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != '')

_composition_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != '')

_craft_st = st.sampled_from(['平纹', '斜纹', '缎纹', '提花', '针织'])

_weight_st = st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
_width_st = st.floats(min_value=50.0, max_value=500.0, allow_nan=False, allow_infinity=False)
_price_st = st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)


# ===========================================================================
# Property 21: 收藏往返
# ===========================================================================


class TestFavoriteRoundTripProperty:
    """Property 21: 收藏往返

    **Feature: textile-fabric-platform, Property 21: 收藏往返**
    **Validates: Requirements 9.2, 9.3**

    For any user and fabric, after adding a favorite the favorites list should
    contain that fabric; after removing the favorite the list should not contain it.
    """

    @given(
        fabric_name=_fabric_name_st,
        composition=_composition_st,
        craft=_craft_st,
        weight=_weight_st,
        width=_width_st,
        price=_price_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_favorite_round_trip(
        self, app_context, client,
        fabric_name, composition, craft, weight, width, price,
    ):
        """Adding a favorite then listing should include the fabric;
        removing it then listing should exclude the fabric.

        **Validates: Requirements 9.2, 9.3**
        """
        # 1. Create a buyer user
        phone = _unique_phone()
        buyer = User(phone=phone, role='buyer')
        buyer.set_password('testpass123')
        _db.session.add(buyer)
        _db.session.commit()
        buyer_id = buyer.id

        # 2. Create a supplier user for the fabric
        supplier_phone = _unique_phone()
        supplier = User(phone=supplier_phone, role='supplier')
        supplier.set_password('testpass123')
        _db.session.add(supplier)
        _db.session.commit()
        supplier_id = supplier.id

        # 3. Create a fabric via direct DB insertion
        fabric = Fabric(
            supplier_id=supplier_id,
            name=fabric_name,
            composition=composition,
            weight=weight,
            width=width,
            craft=craft,
            price=price,
            status='active',
        )
        _db.session.add(fabric)
        _db.session.commit()
        fabric_id = fabric.id

        # 4. Get JWT token for the buyer
        token = create_access_token(identity=str(buyer_id))
        auth_header = {'Authorization': f'Bearer {token}'}

        # 5. POST /api/fabrics/<id>/favorite → should succeed (201 or 200)
        fav_resp = client.post(
            f'/api/fabrics/{fabric_id}/favorite',
            headers=auth_header,
        )
        assert fav_resp.status_code in (200, 201), (
            f'Expected 200 or 201 when adding favorite, got {fav_resp.status_code}'
        )

        # 6. GET /api/fabrics/favorites → fabric should be in the list
        list_resp = client.get('/api/fabrics/favorites', headers=auth_header)
        assert list_resp.status_code == 200
        items = list_resp.get_json()['items']
        fabric_ids_in_list = [item['fabric_id'] for item in items]
        assert fabric_id in fabric_ids_in_list, (
            f'Fabric {fabric_id} should be in favorites after adding'
        )

        # 7. DELETE /api/fabrics/<id>/favorite → should succeed (200)
        del_resp = client.delete(
            f'/api/fabrics/{fabric_id}/favorite',
            headers=auth_header,
        )
        assert del_resp.status_code == 200, (
            f'Expected 200 when removing favorite, got {del_resp.status_code}'
        )

        # 8. GET /api/fabrics/favorites → fabric should NOT be in the list
        list_resp2 = client.get('/api/fabrics/favorites', headers=auth_header)
        assert list_resp2.status_code == 200
        items2 = list_resp2.get_json()['items']
        fabric_ids_after = [item['fabric_id'] for item in items2]
        assert fabric_id not in fabric_ids_after, (
            f'Fabric {fabric_id} should NOT be in favorites after removing'
        )

        # 9. Clean up to avoid accumulation across iterations
        # Delete favorites first (in case any remain)
        Favorite.query.filter_by(user_id=buyer_id).delete()
        _db.session.commit()

        fabric_obj = _db.session.get(Fabric, fabric_id)
        if fabric_obj:
            _db.session.delete(fabric_obj)
            _db.session.commit()

        buyer_obj = _db.session.get(User, buyer_id)
        if buyer_obj:
            _db.session.delete(buyer_obj)
            _db.session.commit()

        supplier_obj = _db.session.get(User, supplier_id)
        if supplier_obj:
            _db.session.delete(supplier_obj)
            _db.session.commit()


# ---------------------------------------------------------------------------
# Additional imports for Property 5
# ---------------------------------------------------------------------------
from server.models.message import Message

# Hypothesis strategies for Property 5
_role_st = st.sampled_from(['buyer', 'supplier'])


# ===========================================================================
# Property 5: 用户资质审核状态转换
# ===========================================================================


class TestCertificationStatusTransitionProperty:
    """Property 5: 用户资质审核状态转换

    **Feature: textile-fabric-platform, Property 5: 用户资质审核状态转换**
    **Validates: Requirements 2.6**

    For any pending user, after admin approval the certification_status
    should become 'approved' and a review notification message should be
    created for that user.
    """

    @given(
        role=_role_st,
        company_name=_company_name_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_admin_approval_transitions_to_approved_with_notification(
        self, app_context, client, role, company_name,
    ):
        """For any pending user, admin approval sets certification_status to
        'approved' and generates a review notification message.

        **Validates: Requirements 2.6**
        """
        # 1. Create an admin user
        admin_phone = _unique_phone()
        admin = User(
            phone=admin_phone,
            role='admin',
            certification_status='approved',
        )
        admin.set_password('adminpass')
        _db.session.add(admin)
        _db.session.commit()
        admin_id = admin.id

        # 2. Create a pending user with random role and company_name
        user_phone = _unique_phone()
        user = User(
            phone=user_phone,
            role=role,
            company_name=company_name,
            certification_status='pending',
        )
        user.set_password('testpass')
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # Verify user starts as pending
        assert user.certification_status == 'pending'

        # 3. Admin approves the user via PUT /api/admin/users/<id>/certify
        admin_token = create_access_token(identity=str(admin_id))
        resp = client.put(
            f'/api/admin/users/{user_id}/certify',
            json={'status': 'approved'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200

        # 4. Verify certification_status is now 'approved'
        data = resp.get_json()
        assert data['user']['certification_status'] == 'approved'

        # Also verify directly in the database
        updated_user = _db.session.get(User, user_id)
        assert updated_user.certification_status == 'approved'

        # 5. Verify a review notification message was created for the user
        notification = Message.query.filter_by(
            user_id=user_id,
            type='review',
        ).first()
        assert notification is not None, (
            f'Expected a review notification for user {user_id} after approval'
        )
        assert notification.is_read is False
        assert notification.ref_id == user_id
        assert notification.ref_type == 'user'

        # 6. Clean up to avoid accumulation across iterations
        Message.query.filter_by(user_id=user_id).delete()
        _db.session.commit()

        user_obj = _db.session.get(User, user_id)
        if user_obj:
            _db.session.delete(user_obj)
            _db.session.commit()

        admin_obj = _db.session.get(User, admin_id)
        if admin_obj:
            _db.session.delete(admin_obj)
            _db.session.commit()
