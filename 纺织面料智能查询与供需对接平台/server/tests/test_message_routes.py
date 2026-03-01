"""Unit tests for message notification routes.

Tests all message endpoints:
- GET /api/messages (list messages, paginated, filterable by is_read)
- PUT /api/messages/<id>/read (mark message as read)
- GET /api/messages/unread-count (get unread message count)

Validates: Requirements 8.4, 8.5
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.message import Message


@pytest.fixture
def user_token(client):
    """Create a buyer user and return their JWT token and user ID."""
    user = User(phone='13700137001', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def other_user_token(client):
    """Create another user and return their JWT token and user ID."""
    user = User(phone='13700137002', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


def _create_message(user_id, title='测试消息', msg_type='system',
                     content='测试内容', is_read=False, ref_id=None, ref_type=None):
    """Helper to create a message directly in the database."""
    msg = Message(
        user_id=user_id,
        type=msg_type,
        title=title,
        content=content,
        ref_id=ref_id,
        ref_type=ref_type,
        is_read=is_read,
    )
    _db.session.add(msg)
    _db.session.commit()
    return msg


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestListMessages:
    """Tests for GET /api/messages."""

    def test_list_messages_empty(self, client, user_token):
        """Empty message list returns zero items."""
        token, _ = user_token
        resp = client.get('/api/messages', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'] == []
        assert data['total'] == 0
        assert data['page'] == 1
        assert data['per_page'] == 20

    def test_list_messages_with_data(self, client, user_token):
        """Messages are returned for the current user."""
        token, user_id = user_token
        _create_message(user_id, title='消息1')
        _create_message(user_id, title='消息2')

        resp = client.get('/api/messages', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2
        assert len(data['items']) == 2

    def test_list_messages_descending_order(self, client, user_token):
        """Messages should be returned in descending creation time order."""
        from datetime import datetime, timedelta
        token, user_id = user_token

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(3):
            msg = Message(
                user_id=user_id,
                type='system',
                title=f'消息{i}',
                content='内容',
                is_read=False,
            )
            msg.created_at = base_time + timedelta(hours=i)
            _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/messages', headers=_auth_header(token))
        data = resp.get_json()
        items = data['items']
        assert len(items) == 3
        # Should be in descending order by created_at
        for i in range(len(items) - 1):
            assert items[i]['created_at'] >= items[i + 1]['created_at']

    def test_list_messages_only_own_messages(self, client, user_token, other_user_token):
        """Users should only see their own messages."""
        token, user_id = user_token
        _, other_id = other_user_token

        _create_message(user_id, title='我的消息')
        _create_message(other_id, title='别人的消息')

        resp = client.get('/api/messages', headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == '我的消息'

    def test_list_messages_pagination(self, client, user_token):
        """Pagination returns correct page and total."""
        token, user_id = user_token
        for i in range(5):
            _create_message(user_id, title=f'消息{i}')

        resp = client.get('/api/messages?page=1&per_page=2',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_list_messages_pagination_page2(self, client, user_token):
        """Second page returns remaining items."""
        token, user_id = user_token
        for i in range(5):
            _create_message(user_id, title=f'消息{i}')

        resp = client.get('/api/messages?page=2&per_page=2',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 2

    def test_list_messages_filter_unread(self, client, user_token):
        """Filter by is_read=false returns only unread messages."""
        token, user_id = user_token
        _create_message(user_id, title='未读', is_read=False)
        _create_message(user_id, title='已读', is_read=True)

        resp = client.get('/api/messages?is_read=false',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == '未读'
        assert data['items'][0]['is_read'] is False

    def test_list_messages_filter_read(self, client, user_token):
        """Filter by is_read=true returns only read messages."""
        token, user_id = user_token
        _create_message(user_id, title='未读', is_read=False)
        _create_message(user_id, title='已读', is_read=True)

        resp = client.get('/api/messages?is_read=true',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == '已读'
        assert data['items'][0]['is_read'] is True

    def test_list_messages_no_auth(self, client):
        """Unauthenticated request returns 401."""
        resp = client.get('/api/messages')
        assert resp.status_code == 401


class TestMarkAsRead:
    """Tests for PUT /api/messages/<id>/read."""

    def test_mark_as_read_success(self, client, user_token):
        """Marking an unread message as read sets is_read to True."""
        token, user_id = user_token
        msg = _create_message(user_id, title='未读消息', is_read=False)

        resp = client.put(f'/api/messages/{msg.id}/read',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_read'] is True
        assert data['id'] == msg.id

    def test_mark_as_read_already_read(self, client, user_token):
        """Marking an already-read message is idempotent."""
        token, user_id = user_token
        msg = _create_message(user_id, title='已读消息', is_read=True)

        resp = client.put(f'/api/messages/{msg.id}/read',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['is_read'] is True

    def test_mark_as_read_not_owner(self, client, user_token, other_user_token):
        """A user cannot mark another user's message as read."""
        _, other_id = other_user_token
        token, _ = user_token
        msg = _create_message(other_id, title='别人的消息')

        resp = client.put(f'/api/messages/{msg.id}/read',
                          headers=_auth_header(token))
        assert resp.status_code == 403

    def test_mark_as_read_not_found(self, client, user_token):
        """Marking a non-existent message returns 404."""
        token, _ = user_token
        resp = client.put('/api/messages/99999/read',
                          headers=_auth_header(token))
        assert resp.status_code == 404

    def test_mark_as_read_no_auth(self, client):
        """Unauthenticated request returns 401."""
        resp = client.put('/api/messages/1/read')
        assert resp.status_code == 401

    def test_mark_as_read_returns_full_message(self, client, user_token):
        """Response includes all message fields."""
        token, user_id = user_token
        msg = _create_message(
            user_id, title='完整消息', msg_type='order',
            content='订单更新', ref_id=42, ref_type='order',
        )

        resp = client.put(f'/api/messages/{msg.id}/read',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['title'] == '完整消息'
        assert data['type'] == 'order'
        assert data['content'] == '订单更新'
        assert data['ref_id'] == 42
        assert data['ref_type'] == 'order'
        assert data['is_read'] is True
        assert data['created_at'] is not None


class TestUnreadCount:
    """Tests for GET /api/messages/unread-count."""

    def test_unread_count_zero(self, client, user_token):
        """No messages returns count 0."""
        token, _ = user_token
        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 0

    def test_unread_count_with_unread(self, client, user_token):
        """Returns correct count of unread messages."""
        token, user_id = user_token
        _create_message(user_id, title='未读1', is_read=False)
        _create_message(user_id, title='未读2', is_read=False)
        _create_message(user_id, title='已读1', is_read=True)

        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 2

    def test_unread_count_only_own_messages(self, client, user_token, other_user_token):
        """Unread count only includes the current user's messages."""
        token, user_id = user_token
        _, other_id = other_user_token

        _create_message(user_id, title='我的未读', is_read=False)
        _create_message(other_id, title='别人的未读', is_read=False)

        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['count'] == 1

    def test_unread_count_all_read(self, client, user_token):
        """All read messages returns count 0."""
        token, user_id = user_token
        _create_message(user_id, title='已读1', is_read=True)
        _create_message(user_id, title='已读2', is_read=True)

        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['count'] == 0

    def test_unread_count_after_marking_read(self, client, user_token):
        """Unread count decreases after marking a message as read."""
        token, user_id = user_token
        msg1 = _create_message(user_id, title='未读1', is_read=False)
        _create_message(user_id, title='未读2', is_read=False)

        # Initially 2 unread
        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        assert resp.get_json()['count'] == 2

        # Mark one as read
        client.put(f'/api/messages/{msg1.id}/read',
                   headers=_auth_header(token))

        # Now 1 unread
        resp = client.get('/api/messages/unread-count',
                          headers=_auth_header(token))
        assert resp.get_json()['count'] == 1

    def test_unread_count_no_auth(self, client):
        """Unauthenticated request returns 401."""
        resp = client.get('/api/messages/unread-count')
        assert resp.status_code == 401
