"""Unit tests for conversation and chat message endpoints.

Tests the GET /api/conversations endpoint:
- Role-based filtering (buyer, supplier, admin)
- Pagination
- Counterparty company_name inclusion
- Demand title inclusion
- Unread count per conversation
- Sorting by last_message_at descending

Tests the GET /api/conversations/<conv_id>/messages endpoint:
- Chronological order (oldest first)
- Pagination
- Auto-mark other party's messages as read
- Admin can view but messages not marked as read
- Access control (participant or admin only)
- Conversation not found

Tests the POST /api/conversations/<conv_id>/messages endpoint:
- Participants can send messages
- Admin cannot send messages
- Non-participants cannot send messages
- Empty content validation
- Conversation metadata updated on send
- last_message_preview truncated to 100 chars

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 9.1, 9.2
"""

import pytest
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.demand import Demand
from server.models.conversation import Conversation, ChatMessage


@pytest.fixture
def buyer(client):
    """Create a buyer user."""
    user = User(phone='13900000001', role='buyer', company_name='采购公司A')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def supplier(client):
    """Create a supplier user."""
    user = User(phone='13900000002', role='supplier', company_name='供应商公司B')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def another_supplier(client):
    """Create another supplier user."""
    user = User(phone='13900000003', role='supplier', company_name='供应商公司C')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def admin(client):
    """Create an admin user."""
    user = User(phone='13900000004', role='admin', company_name='管理员')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def another_buyer(client):
    """Create another buyer user."""
    user = User(phone='13900000005', role='buyer', company_name='采购公司D')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def demand(client, buyer):
    """Create a demand for the buyer."""
    d = Demand(
        buyer_id=buyer.id,
        title='高端棉布采购',
        quantity=1000,
        status='open',
    )
    _db.session.add(d)
    _db.session.commit()
    return d


@pytest.fixture
def demand2(client, another_buyer):
    """Create a second demand for another buyer."""
    d = Demand(
        buyer_id=another_buyer.id,
        title='丝绸面料采购',
        quantity=500,
        status='open',
    )
    _db.session.add(d)
    _db.session.commit()
    return d


def _make_token(user):
    """Create a JWT token for the given user."""
    return create_access_token(identity=str(user.id))


def _auth_header(user):
    """Return Authorization header dict for the given user."""
    return {'Authorization': f'Bearer {_make_token(user)}'}


class TestListConversations:
    """Tests for GET /api/conversations."""

    def test_buyer_sees_own_conversations(self, client, buyer, supplier, another_supplier, demand):
        """Buyer should only see conversations where they are the buyer."""
        now = datetime.utcnow()
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
            last_message_preview='你好',
        )
        conv2 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now - timedelta(hours=1),
            last_message_preview='报价已提交',
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2
        assert len(data['items']) == 2
        # All conversations should belong to this buyer
        for item in data['items']:
            assert item['buyer_id'] == buyer.id

    def test_supplier_sees_own_conversations(self, client, buyer, supplier, another_buyer, demand, demand2):
        """Supplier should only see conversations where they are the supplier."""
        now = datetime.utcnow()
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
            last_message_preview='你好',
        )
        # Conversation with another buyer - supplier is still the same
        conv2 = Conversation(
            demand_id=demand2.id,
            buyer_id=another_buyer.id,
            supplier_id=supplier.id,
            last_message_at=now - timedelta(hours=1),
            last_message_preview='报价已提交',
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(supplier))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2
        for item in data['items']:
            assert item['supplier_id'] == supplier.id

    def test_admin_sees_all_conversations(self, client, buyer, supplier, another_buyer, another_supplier, admin, demand, demand2):
        """Admin should see all conversations across all users."""
        now = datetime.utcnow()
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        conv2 = Conversation(
            demand_id=demand2.id,
            buyer_id=another_buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now - timedelta(hours=1),
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(admin))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 2

    def test_buyer_does_not_see_other_conversations(self, client, buyer, supplier, another_buyer, another_supplier, demand, demand2):
        """Buyer should not see conversations belonging to other buyers."""
        now = datetime.utcnow()
        # Conversation for buyer
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        # Conversation for another_buyer
        conv2 = Conversation(
            demand_id=demand2.id,
            buyer_id=another_buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now,
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['buyer_id'] == buyer.id

    def test_counterparty_for_buyer(self, client, buyer, supplier, demand):
        """Buyer should see supplier's company_name as counterparty."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['items'][0]['counterparty'] == '供应商公司B'

    def test_counterparty_for_supplier(self, client, buyer, supplier, demand):
        """Supplier should see buyer's company_name as counterparty."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(supplier))
        data = resp.get_json()
        assert data['items'][0]['counterparty'] == '采购公司A'

    def test_counterparty_for_admin(self, client, buyer, supplier, admin, demand):
        """Admin should see both buyer and supplier company names."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(admin))
        data = resp.get_json()
        cp = data['items'][0]['counterparty']
        assert cp['buyer_company_name'] == '采购公司A'
        assert cp['supplier_company_name'] == '供应商公司B'

    def test_demand_title_included(self, client, buyer, supplier, demand):
        """Each conversation should include the demand_title."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['items'][0]['demand_title'] == '高端棉布采购'

    def test_unread_count_for_buyer(self, client, buyer, supplier, demand):
        """Buyer should see unread count of messages from supplier."""
        now = datetime.utcnow()
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        _db.session.add(conv)
        _db.session.commit()

        # 3 unread messages from supplier
        for i in range(3):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=supplier.id,
                content=f'消息{i}',
                is_read=False,
            )
            _db.session.add(msg)
        # 1 read message from supplier
        msg_read = ChatMessage(
            conversation_id=conv.id,
            sender_id=supplier.id,
            content='已读消息',
            is_read=True,
        )
        _db.session.add(msg_read)
        # 2 messages from buyer (should not count)
        for i in range(2):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=buyer.id,
                content=f'买家消息{i}',
                is_read=False,
            )
            _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['items'][0]['unread_count'] == 3

    def test_unread_count_for_admin_is_zero(self, client, buyer, supplier, admin, demand):
        """Admin should always have unread_count = 0."""
        now = datetime.utcnow()
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        _db.session.add(conv)
        _db.session.commit()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=supplier.id,
            content='消息',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(admin))
        data = resp.get_json()
        assert data['items'][0]['unread_count'] == 0

    def test_sorted_by_last_message_at_descending(self, client, buyer, supplier, another_supplier, demand):
        """Conversations should be sorted by last_message_at descending."""
        now = datetime.utcnow()
        conv_old = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now - timedelta(hours=2),
            last_message_preview='旧消息',
        )
        conv_new = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now,
            last_message_preview='新消息',
        )
        _db.session.add_all([conv_old, conv_new])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        items = data['items']
        assert len(items) == 2
        # Newest first
        assert items[0]['last_message_preview'] == '新消息'
        assert items[1]['last_message_preview'] == '旧消息'

    def test_null_last_message_at_sorted_last(self, client, buyer, supplier, another_supplier, demand):
        """Conversations with null last_message_at should appear last."""
        now = datetime.utcnow()
        conv_with_msg = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
            last_message_preview='有消息',
        )
        conv_no_msg = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=None,
            last_message_preview=None,
        )
        _db.session.add_all([conv_with_msg, conv_no_msg])
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        items = data['items']
        assert len(items) == 2
        assert items[0]['last_message_preview'] == '有消息'
        assert items[1]['last_message_at'] is None

    def test_pagination(self, client, buyer, supplier, another_supplier, demand):
        """Pagination should work correctly."""
        now = datetime.utcnow()
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        conv2 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now - timedelta(hours=1),
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        # Page 1, per_page 1
        resp = client.get('/api/conversations?page=1&per_page=1', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['total'] == 2
        assert data['page'] == 1
        assert data['per_page'] == 1
        assert len(data['items']) == 1

        # Page 2, per_page 1
        resp = client.get('/api/conversations?page=2&per_page=1', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['total'] == 2
        assert data['page'] == 2
        assert len(data['items']) == 1

    def test_empty_conversation_list(self, client, buyer):
        """User with no conversations should get empty list."""
        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []
        assert data['page'] == 1

    def test_last_message_preview_included(self, client, buyer, supplier, demand):
        """last_message_preview and last_message_at should be in response."""
        now = datetime.utcnow()
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
            last_message_preview='最新消息预览',
        )
        _db.session.add(conv)
        _db.session.commit()

        resp = client.get('/api/conversations', headers=_auth_header(buyer))
        data = resp.get_json()
        item = data['items'][0]
        assert item['last_message_preview'] == '最新消息预览'
        assert item['last_message_at'] is not None

    def test_unauthenticated_request(self, client):
        """Request without JWT should be rejected."""
        resp = client.get('/api/conversations')
        assert resp.status_code == 401


@pytest.fixture
def conversation(client, buyer, supplier, demand):
    """Create a conversation between buyer and supplier for the demand."""
    conv = Conversation(
        demand_id=demand.id,
        buyer_id=buyer.id,
        supplier_id=supplier.id,
        last_message_at=datetime.utcnow(),
        last_message_preview='初始消息',
    )
    _db.session.add(conv)
    _db.session.commit()
    return conv


@pytest.fixture
def outsider(client):
    """Create a user who is not a participant in any conversation."""
    user = User(phone='13900000099', role='buyer', company_name='外部公司')
    user.set_password('testpass')
    _db.session.add(user)
    _db.session.commit()
    return user


class TestGetMessages:
    """Tests for GET /api/conversations/<conv_id>/messages."""

    def test_buyer_gets_messages_chronological(self, client, buyer, supplier, conversation):
        """Buyer should see messages in chronological order (oldest first)."""
        now = datetime.utcnow()
        msg1 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='第一条消息',
            created_at=now - timedelta(hours=2),
        )
        msg2 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=buyer.id,
            content='第二条消息',
            created_at=now - timedelta(hours=1),
        )
        msg3 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='第三条消息',
            created_at=now,
        )
        _db.session.add_all([msg3, msg1, msg2])  # Add out of order
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 3
        assert len(data['items']) == 3
        # Chronological order: oldest first
        assert data['items'][0]['content'] == '第一条消息'
        assert data['items'][1]['content'] == '第二条消息'
        assert data['items'][2]['content'] == '第三条消息'

    def test_supplier_gets_messages(self, client, buyer, supplier, conversation):
        """Supplier should be able to view messages."""
        msg = ChatMessage(
            conversation_id=conversation.id,
            sender_id=buyer.id,
            content='买家消息',
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(supplier),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['content'] == '买家消息'

    def test_auto_mark_read_for_buyer(self, client, buyer, supplier, conversation):
        """When buyer fetches messages, supplier's unread messages should be marked as read."""
        msg1 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='供应商消息1',
            is_read=False,
        )
        msg2 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='供应商消息2',
            is_read=False,
        )
        # Buyer's own message should NOT be affected
        msg3 = ChatMessage(
            conversation_id=conversation.id,
            sender_id=buyer.id,
            content='买家消息',
            is_read=False,
        )
        _db.session.add_all([msg1, msg2, msg3])
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 200

        # Verify supplier's messages are now marked as read
        updated_msg1 = _db.session.get(ChatMessage, msg1.id)
        updated_msg2 = _db.session.get(ChatMessage, msg2.id)
        updated_msg3 = _db.session.get(ChatMessage, msg3.id)
        assert updated_msg1.is_read is True
        assert updated_msg2.is_read is True
        # Buyer's own message should remain unread
        assert updated_msg3.is_read is False

    def test_auto_mark_read_for_supplier(self, client, buyer, supplier, conversation):
        """When supplier fetches messages, buyer's unread messages should be marked as read."""
        msg = ChatMessage(
            conversation_id=conversation.id,
            sender_id=buyer.id,
            content='买家消息',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(supplier),
        )
        assert resp.status_code == 200

        updated_msg = _db.session.get(ChatMessage, msg.id)
        assert updated_msg.is_read is True

    def test_admin_can_view_messages(self, client, buyer, supplier, admin, conversation):
        """Admin should be able to view messages in any conversation."""
        msg = ChatMessage(
            conversation_id=conversation.id,
            sender_id=buyer.id,
            content='买家消息',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(admin),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1

    def test_admin_does_not_mark_messages_as_read(self, client, buyer, supplier, admin, conversation):
        """Admin viewing messages should NOT mark them as read."""
        msg = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='供应商消息',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(admin),
        )
        assert resp.status_code == 200

        # Message should still be unread
        updated_msg = _db.session.get(ChatMessage, msg.id)
        assert updated_msg.is_read is False

    def test_non_participant_cannot_view(self, client, buyer, supplier, outsider, conversation):
        """Non-participant (not buyer, supplier, or admin) should get 403."""
        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(outsider),
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['message'] == '无权查看此会话'

    def test_conversation_not_found(self, client, buyer):
        """Non-existent conversation should return 404."""
        resp = client.get(
            '/api/conversations/99999/messages',
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['message'] == '会话不存在'

    def test_pagination(self, client, buyer, supplier, conversation):
        """Pagination should work correctly for messages."""
        now = datetime.utcnow()
        for i in range(5):
            msg = ChatMessage(
                conversation_id=conversation.id,
                sender_id=supplier.id,
                content=f'消息{i}',
                created_at=now + timedelta(minutes=i),
            )
            _db.session.add(msg)
        _db.session.commit()

        # Page 1, per_page 2
        resp = client.get(
            f'/api/conversations/{conversation.id}/messages?page=1&per_page=2',
            headers=_auth_header(buyer),
        )
        data = resp.get_json()
        assert data['total'] == 5
        assert data['page'] == 1
        assert data['per_page'] == 2
        assert len(data['items']) == 2
        # First page should have oldest messages
        assert data['items'][0]['content'] == '消息0'
        assert data['items'][1]['content'] == '消息1'

        # Page 3, per_page 2 (last page with 1 item)
        resp = client.get(
            f'/api/conversations/{conversation.id}/messages?page=3&per_page=2',
            headers=_auth_header(buyer),
        )
        data = resp.get_json()
        assert len(data['items']) == 1
        assert data['items'][0]['content'] == '消息4'

    def test_default_pagination(self, client, buyer, supplier, conversation):
        """Default pagination should be page=1, per_page=30."""
        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        data = resp.get_json()
        assert data['page'] == 1
        assert data['per_page'] == 30

    def test_empty_messages(self, client, buyer, supplier, conversation):
        """Conversation with no messages should return empty list."""
        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_unauthenticated_request(self, client, conversation):
        """Request without JWT should be rejected."""
        resp = client.get(f'/api/conversations/{conversation.id}/messages')
        assert resp.status_code == 401

    def test_message_fields_in_response(self, client, buyer, supplier, conversation):
        """Each message should include all expected fields."""
        msg = ChatMessage(
            conversation_id=conversation.id,
            sender_id=supplier.id,
            content='测试消息',
            msg_type='text',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()

        resp = client.get(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        data = resp.get_json()
        item = data['items'][0]
        assert 'id' in item
        assert 'conversation_id' in item
        assert 'sender_id' in item
        assert 'content' in item
        assert 'msg_type' in item
        assert 'is_read' in item
        assert 'created_at' in item
        assert item['msg_type'] == 'text'


class TestSendMessage:
    """Tests for POST /api/conversations/<conv_id>/messages."""

    def test_buyer_sends_message(self, client, buyer, supplier, conversation):
        """Buyer should be able to send a message."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '你好，我想了解报价详情'},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['content'] == '你好，我想了解报价详情'
        assert data['sender_id'] == buyer.id
        assert data['conversation_id'] == conversation.id
        assert data['msg_type'] == 'text'
        assert data['is_read'] is False

    def test_supplier_sends_message(self, client, buyer, supplier, conversation):
        """Supplier should be able to send a message."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '报价已更新'},
            headers=_auth_header(supplier),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['content'] == '报价已更新'
        assert data['sender_id'] == supplier.id

    def test_updates_conversation_last_message_at(self, client, buyer, supplier, conversation):
        """Sending a message should update conversation's last_message_at."""
        old_last_message_at = conversation.last_message_at

        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '新消息'},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 201

        _db.session.refresh(conversation)
        assert conversation.last_message_at is not None
        assert conversation.last_message_at >= old_last_message_at

    def test_updates_conversation_last_message_preview(self, client, buyer, supplier, conversation):
        """Sending a message should update conversation's last_message_preview."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '这是最新的消息内容'},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 201

        _db.session.refresh(conversation)
        assert conversation.last_message_preview == '这是最新的消息内容'

    def test_last_message_preview_truncated_to_100_chars(self, client, buyer, supplier, conversation):
        """last_message_preview should be truncated to 100 characters."""
        long_content = '这' * 150  # 150 characters
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': long_content},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 201

        _db.session.refresh(conversation)
        assert len(conversation.last_message_preview) == 100
        assert conversation.last_message_preview == long_content[:100]

    def test_admin_cannot_send_message(self, client, buyer, supplier, admin, conversation):
        """Admin should NOT be able to send messages (read-only)."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '管理员消息'},
            headers=_auth_header(admin),
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['message'] == '管理员仅可查看会话'

    def test_non_participant_cannot_send(self, client, buyer, supplier, outsider, conversation):
        """Non-participant should NOT be able to send messages."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '外部消息'},
            headers=_auth_header(outsider),
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['message'] == '无权在此会话中发送消息'

    def test_empty_content_rejected(self, client, buyer, supplier, conversation):
        """Empty message content should be rejected."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': ''},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['message'] == '消息内容不能为空'

    def test_whitespace_only_content_rejected(self, client, buyer, supplier, conversation):
        """Whitespace-only content should be rejected."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '   \n\t  '},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['message'] == '消息内容不能为空'

    def test_missing_content_field_rejected(self, client, buyer, supplier, conversation):
        """Missing content field should be rejected."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['message'] == '消息内容不能为空'

    def test_conversation_not_found(self, client, buyer):
        """Non-existent conversation should return 404."""
        resp = client.post(
            '/api/conversations/99999/messages',
            json={'content': '消息'},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['message'] == '会话不存在'

    def test_message_persisted_in_db(self, client, buyer, supplier, conversation):
        """Sent message should be persisted in the database."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '持久化测试'},
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 201
        data = resp.get_json()

        # Verify in database
        msg = _db.session.get(ChatMessage, data['id'])
        assert msg is not None
        assert msg.content == '持久化测试'
        assert msg.sender_id == buyer.id
        assert msg.conversation_id == conversation.id
        assert msg.msg_type == 'text'
        assert msg.is_read is False

    def test_unauthenticated_request(self, client, conversation):
        """Request without JWT should be rejected."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            json={'content': '消息'},
        )
        assert resp.status_code == 401

    def test_no_json_body_rejected(self, client, buyer, supplier, conversation):
        """Request without JSON body should be rejected."""
        resp = client.post(
            f'/api/conversations/{conversation.id}/messages',
            headers=_auth_header(buyer),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['message'] == '消息内容不能为空'


class TestUnreadCount:
    """Tests for GET /api/conversations/unread-count.

    Validates: Requirements 8.4
    """

    def test_buyer_unread_count(self, client, buyer, supplier, demand):
        """Buyer should see count of unread messages from suppliers."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        # 3 unread messages from supplier
        for i in range(3):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=supplier.id,
                content=f'供应商消息{i}',
                is_read=False,
            )
            _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 3

    def test_supplier_unread_count(self, client, buyer, supplier, demand):
        """Supplier should see count of unread messages from buyers."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        # 2 unread messages from buyer
        for i in range(2):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=buyer.id,
                content=f'买家消息{i}',
                is_read=False,
            )
            _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(supplier))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 2

    def test_own_messages_not_counted(self, client, buyer, supplier, demand):
        """User's own unread messages should not be counted."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        # Buyer's own messages (should not count)
        for i in range(3):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=buyer.id,
                content=f'买家消息{i}',
                is_read=False,
            )
            _db.session.add(msg)
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 0

    def test_read_messages_not_counted(self, client, buyer, supplier, demand):
        """Already-read messages should not be counted."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        # 2 read messages from supplier
        for i in range(2):
            msg = ChatMessage(
                conversation_id=conv.id,
                sender_id=supplier.id,
                content=f'已读消息{i}',
                is_read=True,
            )
            _db.session.add(msg)
        # 1 unread message from supplier
        msg_unread = ChatMessage(
            conversation_id=conv.id,
            sender_id=supplier.id,
            content='未读消息',
            is_read=False,
        )
        _db.session.add(msg_unread)
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 1

    def test_count_across_multiple_conversations(self, client, buyer, supplier, another_supplier, demand):
        """Unread count should aggregate across all user's conversations."""
        now = datetime.utcnow()
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        conv2 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now,
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        # 2 unread from supplier in conv1
        for i in range(2):
            _db.session.add(ChatMessage(
                conversation_id=conv1.id,
                sender_id=supplier.id,
                content=f'消息{i}',
                is_read=False,
            ))
        # 3 unread from another_supplier in conv2
        for i in range(3):
            _db.session.add(ChatMessage(
                conversation_id=conv2.id,
                sender_id=another_supplier.id,
                content=f'消息{i}',
                is_read=False,
            ))
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 5

    def test_zero_count_when_no_conversations(self, client, buyer):
        """User with no conversations should get count 0."""
        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 0

    def test_zero_count_when_all_read(self, client, buyer, supplier, demand):
        """User with all messages read should get count 0."""
        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime.utcnow(),
        )
        _db.session.add(conv)
        _db.session.commit()

        for i in range(3):
            _db.session.add(ChatMessage(
                conversation_id=conv.id,
                sender_id=supplier.id,
                content=f'消息{i}',
                is_read=True,
            ))
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 0

    def test_unauthenticated_request(self, client):
        """Request without JWT should be rejected."""
        resp = client.get('/api/conversations/unread-count')
        assert resp.status_code == 401

    def test_does_not_count_messages_from_other_conversations(self, client, buyer, supplier, another_buyer, another_supplier, demand, demand2):
        """Should not count unread messages from conversations user is not part of."""
        now = datetime.utcnow()
        # Buyer's conversation
        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
        )
        # Another buyer's conversation
        conv2 = Conversation(
            demand_id=demand2.id,
            buyer_id=another_buyer.id,
            supplier_id=another_supplier.id,
            last_message_at=now,
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        # 1 unread in buyer's conversation
        _db.session.add(ChatMessage(
            conversation_id=conv1.id,
            sender_id=supplier.id,
            content='消息',
            is_read=False,
        ))
        # 5 unread in another buyer's conversation (should not count for buyer)
        for i in range(5):
            _db.session.add(ChatMessage(
                conversation_id=conv2.id,
                sender_id=another_supplier.id,
                content=f'消息{i}',
                is_read=False,
            ))
        _db.session.commit()

        resp = client.get('/api/conversations/unread-count', headers=_auth_header(buyer))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] == 1
