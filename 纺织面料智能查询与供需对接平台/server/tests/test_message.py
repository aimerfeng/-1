"""Property-based tests for message notification module.

**Feature: textile-fabric-platform**
**Validates: Requirements 5.4, 8.1, 8.2, 8.3, 8.5, 8.6**

Uses Hypothesis to verify:
- Property 14: 事件触发通知创建
- Property 18: 消息已读标记
- Property 19: 消息字段完整性
"""

import threading
from datetime import datetime

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from server.extensions import db as _db
from server.models.message import Message
from server.models.user import User
from server.services.notification import send_notification


# ---------------------------------------------------------------------------
# Thread-safe unique phone counter (same pattern as other PBT test files)
# ---------------------------------------------------------------------------

_phone_counter = 0
_phone_lock = threading.Lock()


def _unique_phone():
    """Generate a unique valid Chinese phone number for testing."""
    global _phone_counter
    with _phone_lock:
        _phone_counter += 1
        counter = _phone_counter
    # Format: 16XXXXXXXXX where X is zero-padded counter
    return f'16{counter:09d}'


def _create_user(db_session, role='buyer'):
    """Create a test user and return the User object."""
    phone = _unique_phone()
    user = User(phone=phone, role=role, certification_status='approved')
    db_session.add(user)
    db_session.commit()
    return user


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_notification_type_st = st.sampled_from(['match', 'logistics', 'review', 'order', 'system'])

_title_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != '')

_content_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=200,
).filter(lambda s: s.strip() != '')

_ref_id_st = st.integers(min_value=1, max_value=999999)

_ref_type_st = st.sampled_from(['demand', 'sample', 'order'])


# ===========================================================================
# Property 14: 事件触发通知创建
# ===========================================================================


class TestEventTriggeredNotificationProperty:
    """Property 14: 事件触发通知创建

    **Feature: textile-fabric-platform, Property 14: 事件触发通知创建**
    **Validates: Requirements 5.4, 8.1, 8.2, 8.3**

    For any business event (match/logistics/review/order/system), the system
    should create a notification message for the relevant user containing the
    correct type and associated business ID.
    """

    @given(
        notification_type=_notification_type_st,
        title=_title_st,
        content=_content_st,
        ref_id=_ref_id_st,
        ref_type=_ref_type_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_send_notification_creates_correct_message(
        self, app_context, notification_type, title, content, ref_id, ref_type,
    ):
        """For any business event, send_notification should create a Message
        with the correct type, ref_id, ref_type, and user_id, and the message
        should be persisted in the database.

        **Validates: Requirements 5.4, 8.1, 8.2, 8.3**
        """
        user = _create_user(_db.session)

        # Call send_notification
        result = send_notification(
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            content=content,
            ref_id=ref_id,
            ref_type=ref_type,
        )

        # Verify the returned Message object has correct fields
        assert isinstance(result, Message), (
            f"Expected Message instance, got {type(result)}"
        )
        assert result.id is not None, "Message should have an ID after persistence"
        assert result.user_id == user.id, (
            f"Expected user_id={user.id}, got {result.user_id}"
        )
        assert result.type == notification_type, (
            f"Expected type='{notification_type}', got '{result.type}'"
        )
        assert result.title == title, (
            f"Expected title='{title}', got '{result.title}'"
        )
        assert result.content == content, (
            f"Expected content='{content}', got '{result.content}'"
        )
        assert result.ref_id == ref_id, (
            f"Expected ref_id={ref_id}, got {result.ref_id}"
        )
        assert result.ref_type == ref_type, (
            f"Expected ref_type='{ref_type}', got '{result.ref_type}'"
        )
        assert result.is_read is False, (
            "Newly created notification should be unread"
        )

        # Verify persistence in the database
        db_message = _db.session.get(Message, result.id)
        assert db_message is not None, "Message should be persisted in the database"
        assert db_message.user_id == user.id
        assert db_message.type == notification_type
        assert db_message.ref_id == ref_id
        assert db_message.ref_type == ref_type

        # Cleanup
        _db.session.delete(db_message)
        _db.session.delete(user)
        _db.session.commit()


# ===========================================================================
# Property 18: 消息已读标记
# ===========================================================================


class TestMessageReadMarkProperty:
    """Property 18: 消息已读标记

    **Feature: textile-fabric-platform, Property 18: 消息已读标记**
    **Validates: Requirements 8.5**

    For any unread message, marking it as read should set is_read to True.
    For an already-read message, marking it as read again should be idempotent
    (is_read remains True).
    """

    @given(
        notification_type=_notification_type_st,
        title=_title_st,
        content=_content_st,
        ref_id=_ref_id_st,
        ref_type=_ref_type_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_mark_unread_message_as_read(
        self, app_context, notification_type, title, content, ref_id, ref_type,
    ):
        """For any unread message, setting is_read=True and committing should
        result in is_read being True. Repeating the operation should be
        idempotent.

        **Validates: Requirements 8.5**
        """
        user = _create_user(_db.session)

        # Create a message with is_read=False
        message = Message(
            user_id=user.id,
            type=notification_type,
            title=title,
            content=content,
            ref_id=ref_id,
            ref_type=ref_type,
            is_read=False,
        )
        _db.session.add(message)
        _db.session.commit()

        # Verify initial state is unread
        assert message.is_read is False, "Message should start as unread"

        # Mark as read
        message.is_read = True
        _db.session.commit()

        # Verify it's now read
        refreshed = _db.session.get(Message, message.id)
        assert refreshed.is_read is True, (
            "Message should be read after marking as read"
        )

        # Mark as read again (idempotent)
        refreshed.is_read = True
        _db.session.commit()

        # Verify it's still read
        refreshed_again = _db.session.get(Message, message.id)
        assert refreshed_again.is_read is True, (
            "Message should remain read after idempotent re-mark"
        )

        # Cleanup
        _db.session.delete(refreshed_again)
        _db.session.delete(user)
        _db.session.commit()


# ===========================================================================
# Property 19: 消息字段完整性
# ===========================================================================


class TestMessageFieldCompletenessProperty:
    """Property 19: 消息字段完整性

    **Feature: textile-fabric-platform, Property 19: 消息字段完整性**
    **Validates: Requirements 8.6**

    For any message record, to_dict() should contain all required fields:
    type, title, content, ref_id, created_at, is_read.
    """

    @given(
        notification_type=_notification_type_st,
        title=_title_st,
        content=_content_st,
        ref_id=_ref_id_st,
        ref_type=_ref_type_st,
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_message_to_dict_contains_all_required_fields(
        self, app_context, notification_type, title, content, ref_id, ref_type,
    ):
        """For any message record, to_dict() should contain all required
        fields: type, title, content, ref_id, created_at, is_read.

        **Validates: Requirements 8.6**
        """
        user = _create_user(_db.session)

        # Create a message
        message = Message(
            user_id=user.id,
            type=notification_type,
            title=title,
            content=content,
            ref_id=ref_id,
            ref_type=ref_type,
            is_read=False,
        )
        _db.session.add(message)
        _db.session.commit()

        # Get the dict representation
        msg_dict = message.to_dict()

        # Verify all required fields are present
        required_fields = ['type', 'title', 'content', 'ref_id', 'created_at', 'is_read']
        for field in required_fields:
            assert field in msg_dict, (
                f"Required field '{field}' missing from to_dict() output. "
                f"Keys present: {list(msg_dict.keys())}"
            )

        # Verify field values match what was set
        assert msg_dict['type'] == notification_type, (
            f"Expected type='{notification_type}', got '{msg_dict['type']}'"
        )
        assert msg_dict['title'] == title, (
            f"Expected title='{title}', got '{msg_dict['title']}'"
        )
        assert msg_dict['content'] == content, (
            f"Expected content='{content}', got '{msg_dict['content']}'"
        )
        assert msg_dict['ref_id'] == ref_id, (
            f"Expected ref_id={ref_id}, got {msg_dict['ref_id']}"
        )
        assert msg_dict['is_read'] is False, (
            f"Expected is_read=False, got {msg_dict['is_read']}"
        )
        assert msg_dict['created_at'] is not None, (
            "created_at should not be None"
        )

        # Cleanup
        _db.session.delete(message)
        _db.session.delete(user)
        _db.session.commit()
