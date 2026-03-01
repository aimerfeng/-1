"""Property-based tests for authentication module.

**Feature: textile-fabric-platform**
**Validates: Requirements 1.2, 1.3, 1.4, 2.1, 2.5**

Uses Hypothesis to verify:
- Property 1: Phone number format validation
- Property 2: JWT token validity
- Property 3: User role constraints
- Property 4: Uncertified user access control
"""

import re
import threading

import jwt as pyjwt
import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st
from sqlalchemy.exc import StatementError

from server.extensions import db as _db
from server.models.user import User
from server.routes.auth import validate_phone

# The three valid roles defined in the User model's Enum
VALID_ROLES = {'buyer', 'supplier', 'admin'}

# Thread-safe counter for generating unique phone numbers within a test run
_phone_counter = 0
_phone_lock = threading.Lock()


def _unique_phone():
    """Generate a unique valid Chinese phone number for testing."""
    global _phone_counter
    with _phone_lock:
        _phone_counter += 1
        counter = _phone_counter
    # Format: 13XXXXXXXXX where X is zero-padded counter
    return f'13{counter:09d}'


# ===========================================================================
# Property 3: 用户角色约束
# ===========================================================================


class TestUserRoleConstraintProperty:
    """Property 3: 用户角色约束

    **Feature: textile-fabric-platform, Property 3: 用户角色约束**
    **Validates: Requirements 2.1**

    For any user record, the role field value must be one of
    buyer, supplier, or admin.
    """

    @given(role=st.sampled_from(list(VALID_ROLES)))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_roles_accepted(self, app_context, role):
        """Valid roles (buyer/supplier/admin) should be accepted by the model.

        **Validates: Requirements 2.1**
        """
        user = User(role=role)
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved is not None
        assert saved.role == role
        assert saved.role in VALID_ROLES

        # Clean up to avoid accumulation across iterations
        _db.session.delete(saved)
        _db.session.commit()

    @given(role=st.text(min_size=0, max_size=50))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_invalid_roles_rejected(self, app_context, role):
        """Random strings that are not buyer/supplier/admin should be rejected.

        **Validates: Requirements 2.1**
        """
        assume(role not in VALID_ROLES)

        user = User(role=role)
        _db.session.add(user)

        with pytest.raises((StatementError, ValueError)):
            _db.session.commit()

        _db.session.rollback()


# ===========================================================================
# Property 1: 手机号格式验证
# ===========================================================================


class TestPhoneValidationProperty:
    """Property 1: 手机号格式验证

    **Feature: textile-fabric-platform, Property 1: 手机号格式验证**
    **Validates: Requirements 1.2**

    For any string, if it matches the Chinese mainland phone number format
    (starts with 1, second digit 3-9, total 11 digits), validate_phone
    should return True; otherwise it should return False.
    """

    @given(phone=st.from_regex(r'^1[3-9]\d{9}$', fullmatch=True))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_phone_numbers_accepted(self, phone):
        """Valid Chinese phone numbers (1 + [3-9] + 9 digits) should return True.

        **Validates: Requirements 1.2**
        """
        assert validate_phone(phone) is True

    @given(text=st.text())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_random_strings_rejected_unless_valid(self, text):
        """Random strings that don't match the phone pattern should return False.

        **Validates: Requirements 1.2**
        """
        is_valid_format = bool(re.match(r'^1[3-9]\d{9}$', text))
        assert validate_phone(text) == is_valid_format


# ===========================================================================
# Property 2: JWT 令牌有效性
# ===========================================================================


class TestJWTTokenValidityProperty:
    """Property 2: JWT 令牌有效性

    **Feature: textile-fabric-platform, Property 2: JWT 令牌有效性**
    **Validates: Requirements 1.3, 1.4**

    For any valid user credentials, login should return a decodable JWT
    whose identity matches the user's ID. For invalid credentials, login
    should return an error (not a token).
    """

    @given(
        password=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=6,
            max_size=20,
        ),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_valid_credentials_return_decodable_jwt(self, app_context, client, password):
        """Valid credentials should produce a JWT whose identity matches the user ID.

        **Validates: Requirements 1.3**
        """
        phone = _unique_phone()

        # Create user directly in DB
        user = User(phone=phone, role='buyer')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # Login with valid credentials
        login_resp = client.post('/api/auth/login', json={
            'phone': phone,
            'password': password,
        })
        assert login_resp.status_code == 200

        data = login_resp.get_json()
        assert 'token' in data
        assert 'user' in data

        # Decode the JWT directly using PyJWT and verify identity matches user ID
        token = data['token']
        jwt_secret = app_context.config['JWT_SECRET_KEY']
        decoded = pyjwt.decode(
            token,
            jwt_secret,
            algorithms=['HS256'],
            options={'verify_sub': False},
        )
        assert str(decoded['sub']) == str(user_id)
        assert str(decoded['sub']) == str(data['user']['id'])

        # Clean up
        user = _db.session.get(User, user_id)
        if user:
            _db.session.delete(user)
            _db.session.commit()

    @given(
        wrong_password=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=6,
            max_size=20,
        ),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_invalid_credentials_return_error(self, app_context, client, wrong_password):
        """Invalid credentials should return an error, not a token.

        **Validates: Requirements 1.4**
        """
        known_password = 'correct_password_123'
        assume(wrong_password != known_password)

        phone = _unique_phone()

        # Create user directly in DB
        user = User(phone=phone, role='buyer')
        user.set_password(known_password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # Attempt login with wrong password
        login_resp = client.post('/api/auth/login', json={
            'phone': phone,
            'password': wrong_password,
        })
        assert login_resp.status_code == 401

        data = login_resp.get_json()
        assert 'token' not in data
        assert data['code'] == 401

        # Clean up
        user = _db.session.get(User, user_id)
        if user:
            _db.session.delete(user)
            _db.session.commit()


# ===========================================================================
# Property 4: 未认证用户访问控制
# ===========================================================================


class TestUncertifiedUserAccessControlProperty:
    """Property 4: 未认证用户访问控制

    **Feature: textile-fabric-platform, Property 4: 未认证用户访问控制**
    **Validates: Requirements 2.5**

    For any user whose certification_status is not 'approved',
    accessing a certification-required endpoint should return 403.
    The test endpoint /api/test-cert-required is registered in conftest.py.
    """

    @given(
        cert_status=st.sampled_from(['pending', 'rejected']),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_non_approved_users_get_403(self, app_context, client, cert_status):
        """Users with certification_status != 'approved' should get 403 on restricted endpoints.

        **Validates: Requirements 2.5**
        """
        phone = _unique_phone()
        password = 'testpass123'

        # Create user directly in DB with specific certification_status
        user = User(phone=phone, role='buyer', certification_status=cert_status)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # Login to get a token
        login_resp = client.post('/api/auth/login', json={
            'phone': phone,
            'password': password,
        })
        assert login_resp.status_code == 200

        token = login_resp.get_json()['token']

        # Access the certification-required test endpoint
        resp = client.get(
            '/api/test-cert-required',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403

        data = resp.get_json()
        assert data['code'] == 403

        # Clean up
        user = _db.session.get(User, user_id)
        if user:
            _db.session.delete(user)
            _db.session.commit()

    @given(data=st.just(True))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_approved_users_can_access(self, app_context, client, data):
        """Users with certification_status == 'approved' should access restricted endpoints.

        **Validates: Requirements 2.5**
        """
        phone = _unique_phone()
        password = 'testpass123'

        # Create user with approved certification
        user = User(phone=phone, role='buyer', certification_status='approved')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

        # Login to get a token
        login_resp = client.post('/api/auth/login', json={
            'phone': phone,
            'password': password,
        })
        assert login_resp.status_code == 200

        token = login_resp.get_json()['token']

        # Access the certification-required test endpoint
        resp = client.get(
            '/api/test-cert-required',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200

        # Clean up
        user = _db.session.get(User, user_id)
        if user:
            _db.session.delete(user)
            _db.session.commit()
