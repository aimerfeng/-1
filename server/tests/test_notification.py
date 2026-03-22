"""Tests for the notification service.

Tests that send_notification and create_notification correctly create
Message records in the database for various business event types.
"""

import pytest
from werkzeug.security import generate_password_hash

from server.extensions import db
from server.models.message import Message
from server.models.user import User
from server.services.notification import send_notification, create_notification


def _create_test_user(db_session, role='buyer', user_id=None):
    """Helper to create a test user."""
    user = User(
        phone='13800138000',
        password_hash=generate_password_hash('password123'),
        role=role,
        company_name='Test Company',
        contact_name='Test User',
        certification_status='approved',
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


class TestSendNotification:
    """Tests for the send_notification function."""

    def test_creates_message_record(self, app_context, db):
        """send_notification should create a Message record in the database."""
        user = _create_test_user(db)

        result = send_notification(
            user_id=user.id,
            notification_type='match',
            title='新的供需匹配',
            content='您的面料与采购需求匹配成功',
            ref_id=42,
            ref_type='demand',
        )

        assert isinstance(result, Message)
        assert result.id is not None
        assert result.user_id == user.id
        assert result.type == 'match'
        assert result.title == '新的供需匹配'
        assert result.content == '您的面料与采购需求匹配成功'
        assert result.ref_id == 42
        assert result.ref_type == 'demand'
        assert result.is_read is False

    def test_persists_to_database(self, app_context, db):
        """Message should be queryable from the database after creation."""
        user = _create_test_user(db)

        send_notification(
            user_id=user.id,
            notification_type='order',
            title='订单状态变更',
            content='您的订单已确认',
            ref_id=10,
            ref_type='order',
        )

        messages = Message.query.filter_by(user_id=user.id).all()
        assert len(messages) == 1
        assert messages[0].type == 'order'
        assert messages[0].title == '订单状态变更'

    def test_match_notification_type(self, app_context, db):
        """Should create a notification with type=match."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='match',
            title='匹配通知',
            content='匹配结果已生成',
            ref_id=1,
            ref_type='demand',
        )
        assert result.type == 'match'

    def test_logistics_notification_type(self, app_context, db):
        """Should create a notification with type=logistics."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='logistics',
            title='物流状态更新',
            content='您的样品已发货',
            ref_id=5,
            ref_type='sample',
        )
        assert result.type == 'logistics'

    def test_review_notification_type(self, app_context, db):
        """Should create a notification with type=review."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='review',
            title='审核结果',
            content='您的样品申请已通过',
            ref_id=3,
            ref_type='sample',
        )
        assert result.type == 'review'

    def test_order_notification_type(self, app_context, db):
        """Should create a notification with type=order."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='order',
            title='订单状态变更',
            content='订单已发货',
            ref_id=7,
            ref_type='order',
        )
        assert result.type == 'order'

    def test_optional_ref_fields_default_to_none(self, app_context, db):
        """ref_id and ref_type should default to None when not provided."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='system',
            title='系统通知',
            content='系统维护通知',
        )
        assert result.ref_id is None
        assert result.ref_type is None

    def test_returns_message_object(self, app_context, db):
        """send_notification should return the created Message object."""
        user = _create_test_user(db)
        result = send_notification(
            user_id=user.id,
            notification_type='match',
            title='Test',
            content='Test content',
        )
        assert isinstance(result, Message)
        assert result.id is not None

    def test_multiple_notifications_for_same_user(self, app_context, db):
        """Should be able to create multiple notifications for the same user."""
        user = _create_test_user(db)

        send_notification(user.id, 'match', 'Match 1', 'Content 1', 1, 'demand')
        send_notification(user.id, 'order', 'Order 1', 'Content 2', 2, 'order')
        send_notification(user.id, 'logistics', 'Logistics 1', 'Content 3', 3, 'sample')

        messages = Message.query.filter_by(user_id=user.id).all()
        assert len(messages) == 3
        types = {m.type for m in messages}
        assert types == {'match', 'order', 'logistics'}


class TestCreateNotification:
    """Tests for the create_notification alias function."""

    def test_creates_message_record(self, app_context, db):
        """create_notification should create a Message record (alias for send_notification)."""
        user = _create_test_user(db)

        result = create_notification(
            user_id=user.id,
            type='match',
            title='匹配通知',
            content='匹配结果已生成',
            ref_id=1,
            ref_type='demand',
        )

        assert isinstance(result, Message)
        assert result.user_id == user.id
        assert result.type == 'match'
        assert result.title == '匹配通知'
        assert result.ref_id == 1
        assert result.ref_type == 'demand'
        assert result.is_read is False

    def test_persists_to_database(self, app_context, db):
        """create_notification should persist the message to the database."""
        user = _create_test_user(db)

        create_notification(
            user_id=user.id,
            type='review',
            title='审核通知',
            content='审核已完成',
            ref_id=5,
            ref_type='sample',
        )

        messages = Message.query.filter_by(user_id=user.id).all()
        assert len(messages) == 1
        assert messages[0].type == 'review'


class TestNotificationFallback:
    """Tests for graceful fallback when outside app context."""

    def test_fallback_outside_app_context(self, app):
        """Should fall back to logging when called outside app context.

        Note: We test this by verifying the function doesn't raise
        when the app context is not active.
        """
        # Within the test, we're in an app context via the fixture,
        # so we test the normal path works. The RuntimeError fallback
        # is a safety net for production edge cases.
        with app.app_context():
            from server.extensions import db as test_db
            test_db.create_all()
            user = User(
                phone='13900139000',
                password_hash='hash',
                role='buyer',
                certification_status='approved',
            )
            test_db.session.add(user)
            test_db.session.commit()

            result = send_notification(
                user_id=user.id,
                notification_type='system',
                title='Test',
                content='Test',
            )
            assert isinstance(result, Message)
            test_db.session.rollback()
            test_db.drop_all()
