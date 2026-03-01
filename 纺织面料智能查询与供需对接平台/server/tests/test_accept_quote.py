"""Unit tests for accept quote endpoint and quote-conversation creation.

Tests:
- PUT /api/demands/<id>/quotes/<qid>/accept (accept quote, buyer only)
- POST /api/demands/<id>/quotes (create quote now creates conversation)

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.3
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.demand import Demand, Quote
from server.models.order import Order
from server.models.conversation import Conversation, ChatMessage


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def buyer(client):
    """Create a buyer user and return (token, user_id)."""
    user = User(phone='13900000001', role='buyer', company_name='BuyerCo')
    user.set_password('pass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def supplier(client):
    """Create a supplier user and return (token, user_id)."""
    user = User(phone='13900000002', role='supplier', company_name='SupplierCo')
    user.set_password('pass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_supplier(client):
    """Create another supplier user and return (token, user_id)."""
    user = User(phone='13900000003', role='supplier', company_name='SupplierCo2')
    user.set_password('pass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_buyer(client):
    """Create another buyer user and return (token, user_id)."""
    user = User(phone='13900000004', role='buyer', company_name='BuyerCo2')
    user.set_password('pass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def demand_with_quotes(client, buyer, supplier, another_supplier):
    """Create a demand with two quotes from different suppliers."""
    b_token, buyer_id = buyer
    s_token, supplier_id = supplier
    s2_token, supplier2_id = another_supplier

    # Create demand
    resp = client.post('/api/demands', json={
        'title': '采购纯棉面料',
        'quantity': 100,
    }, headers=_auth_header(b_token))
    demand_id = resp.get_json()['id']

    # Supplier 1 submits a quote
    resp1 = client.post(f'/api/demands/{demand_id}/quotes', json={
        'price': 25.0,
        'delivery_days': 7,
        'message': '优质棉料',
    }, headers=_auth_header(s_token))
    quote1_id = resp1.get_json()['id']

    # Supplier 2 submits a quote
    resp2 = client.post(f'/api/demands/{demand_id}/quotes', json={
        'price': 30.0,
        'delivery_days': 5,
    }, headers=_auth_header(s2_token))
    quote2_id = resp2.get_json()['id']

    return {
        'demand_id': demand_id,
        'quote1_id': quote1_id,
        'quote2_id': quote2_id,
        'buyer_id': buyer_id,
        'supplier_id': supplier_id,
        'supplier2_id': supplier2_id,
    }


class TestAcceptQuote:
    """Tests for PUT /api/demands/<id>/quotes/<qid>/accept."""

    def test_accept_quote_success(self, client, buyer, supplier, another_supplier,
                                   demand_with_quotes):
        """Accepting a quote creates an order and returns it."""
        b_token, _ = buyer
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 200
        result = resp.get_json()

        # Should return order and conversation_id
        assert 'order' in result
        assert 'conversation_id' in result

        order = result['order']
        assert order['status'] == 'pending'
        assert order['buyer_id'] == data['buyer_id']
        assert order['supplier_id'] == data['supplier_id']
        assert order['demand_id'] == data['demand_id']
        assert order['quote_id'] == data['quote1_id']
        assert order['total_amount'] == 25.0 * 100  # price * quantity
        assert order['order_no'].startswith('ORD')

    def test_accept_quote_sets_statuses(self, client, buyer, supplier, another_supplier,
                                         demand_with_quotes):
        """Accepting a quote sets accepted/rejected/closed statuses."""
        b_token, _ = buyer
        data = demand_with_quotes

        client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )

        # Verify quote statuses
        accepted_quote = _db.session.get(Quote, data['quote1_id'])
        rejected_quote = _db.session.get(Quote, data['quote2_id'])
        assert accepted_quote.status == 'accepted'
        assert rejected_quote.status == 'rejected'

        # Verify demand is closed
        demand = _db.session.get(Demand, data['demand_id'])
        assert demand.status == 'closed'

    def test_accept_quote_creates_conversation(self, client, buyer, supplier,
                                                another_supplier, demand_with_quotes):
        """Accepting a quote creates/reuses a conversation."""
        b_token, _ = buyer
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )
        result = resp.get_json()
        conv_id = result['conversation_id']

        conv = _db.session.get(Conversation, conv_id)
        assert conv is not None
        assert conv.demand_id == data['demand_id']
        assert conv.buyer_id == data['buyer_id']
        assert conv.supplier_id == data['supplier_id']

    def test_accept_quote_creates_system_message(self, client, buyer, supplier,
                                                   another_supplier, demand_with_quotes):
        """Accepting a quote adds a system message to the conversation."""
        b_token, _ = buyer
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )
        conv_id = resp.get_json()['conversation_id']

        # Find system messages about acceptance (not the quote submission ones)
        messages = ChatMessage.query.filter_by(
            conversation_id=conv_id,
            msg_type='system',
        ).all()
        # Should have at least one system message about acceptance
        accept_msgs = [m for m in messages if '报价已被接受' in m.content]
        assert len(accept_msgs) == 1
        assert '¥25.0/米' in accept_msgs[0].content

    def test_accept_quote_demand_not_found(self, client, buyer):
        """Accepting a quote on non-existent demand returns 404."""
        b_token, _ = buyer
        resp = client.put(
            '/api/demands/99999/quotes/1/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 404

    def test_accept_quote_not_owner(self, client, buyer, supplier, another_buyer,
                                     another_supplier, demand_with_quotes):
        """Non-owner buyer cannot accept a quote."""
        other_token, _ = another_buyer
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(other_token),
        )
        assert resp.status_code == 403

    def test_accept_quote_demand_not_open(self, client, buyer, supplier,
                                           another_supplier, demand_with_quotes):
        """Cannot accept a quote on a closed demand."""
        b_token, _ = buyer
        data = demand_with_quotes

        # Accept first quote (closes the demand)
        client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )

        # Try to accept second quote on now-closed demand
        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote2_id"]}/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 400

    def test_accept_quote_not_found(self, client, buyer, supplier,
                                     another_supplier, demand_with_quotes):
        """Accepting a non-existent quote returns 404."""
        b_token, _ = buyer
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/99999/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 404

    def test_accept_quote_wrong_demand(self, client, buyer, supplier,
                                        another_supplier, demand_with_quotes):
        """Accepting a quote that belongs to a different demand returns 404."""
        b_token, _ = buyer
        s_token, _ = supplier
        data = demand_with_quotes

        # Create another demand
        resp = client.post('/api/demands', json={
            'title': '另一个需求',
        }, headers=_auth_header(b_token))
        other_demand_id = resp.get_json()['id']

        # Try to accept quote1 under the wrong demand
        resp = client.put(
            f'/api/demands/{other_demand_id}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 404

    def test_accept_quote_supplier_forbidden(self, client, buyer, supplier,
                                              another_supplier, demand_with_quotes):
        """Supplier cannot accept a quote (buyer-only endpoint)."""
        s_token, _ = supplier
        data = demand_with_quotes

        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
            headers=_auth_header(s_token),
        )
        assert resp.status_code == 403

    def test_accept_quote_no_auth(self, client, buyer, supplier,
                                   another_supplier, demand_with_quotes):
        """Unauthenticated request returns 401."""
        data = demand_with_quotes
        resp = client.put(
            f'/api/demands/{data["demand_id"]}/quotes/{data["quote1_id"]}/accept',
        )
        assert resp.status_code == 401

    def test_accept_quote_quantity_none_defaults_to_1(self, client, buyer, supplier):
        """When demand quantity is None, total_amount = price * 1."""
        b_token, buyer_id = buyer
        s_token, supplier_id = supplier

        # Create demand without quantity
        resp = client.post('/api/demands', json={
            'title': '无数量需求',
        }, headers=_auth_header(b_token))
        demand_id = resp.get_json()['id']

        # Submit quote
        resp = client.post(f'/api/demands/{demand_id}/quotes', json={
            'price': 50.0,
        }, headers=_auth_header(s_token))
        quote_id = resp.get_json()['id']

        # Accept quote
        resp = client.put(
            f'/api/demands/{demand_id}/quotes/{quote_id}/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 200
        order = resp.get_json()['order']
        assert order['total_amount'] == 50.0  # price * 1

    def test_accept_quote_single_quote(self, client, buyer, supplier):
        """Accepting the only quote on a demand works correctly."""
        b_token, _ = buyer
        s_token, _ = supplier

        resp = client.post('/api/demands', json={
            'title': '单报价需求',
            'quantity': 10,
        }, headers=_auth_header(b_token))
        demand_id = resp.get_json()['id']

        resp = client.post(f'/api/demands/{demand_id}/quotes', json={
            'price': 20.0,
        }, headers=_auth_header(s_token))
        quote_id = resp.get_json()['id']

        resp = client.put(
            f'/api/demands/{demand_id}/quotes/{quote_id}/accept',
            headers=_auth_header(b_token),
        )
        assert resp.status_code == 200
        order = resp.get_json()['order']
        assert order['total_amount'] == 200.0  # 20 * 10


class TestCreateQuoteConversation:
    """Tests that creating a quote also creates a conversation (Req 6.1, 6.3)."""

    def test_create_quote_creates_conversation(self, client, buyer, supplier):
        """Submitting a quote creates a conversation."""
        b_token, buyer_id = buyer
        s_token, supplier_id = supplier

        resp = client.post('/api/demands', json={
            'title': '测试需求',
        }, headers=_auth_header(b_token))
        demand_id = resp.get_json()['id']

        resp = client.post(f'/api/demands/{demand_id}/quotes', json={
            'price': 15.0,
            'delivery_days': 3,
        }, headers=_auth_header(s_token))
        assert resp.status_code == 201
        result = resp.get_json()
        assert 'conversation_id' in result

        conv = _db.session.get(Conversation, result['conversation_id'])
        assert conv is not None
        assert conv.demand_id == demand_id
        assert conv.buyer_id == buyer_id
        assert conv.supplier_id == supplier_id

    def test_create_quote_adds_system_message(self, client, buyer, supplier):
        """Submitting a quote adds a system message to the conversation."""
        b_token, _ = buyer
        s_token, _ = supplier

        resp = client.post('/api/demands', json={
            'title': '测试需求',
        }, headers=_auth_header(b_token))
        demand_id = resp.get_json()['id']

        resp = client.post(f'/api/demands/{demand_id}/quotes', json={
            'price': 15.0,
            'delivery_days': 3,
        }, headers=_auth_header(s_token))
        conv_id = resp.get_json()['conversation_id']

        messages = ChatMessage.query.filter_by(
            conversation_id=conv_id,
            msg_type='system',
        ).all()
        assert len(messages) == 1
        assert '¥15.0/米' in messages[0].content
        assert '交货 3 天' in messages[0].content

    def test_create_quote_system_message_no_delivery_days(self, client, buyer, supplier):
        """System message omits delivery info when not provided."""
        b_token, _ = buyer
        s_token, _ = supplier

        resp = client.post('/api/demands', json={
            'title': '测试需求',
        }, headers=_auth_header(b_token))
        demand_id = resp.get_json()['id']

        resp = client.post(f'/api/demands/{demand_id}/quotes', json={
            'price': 20.0,
        }, headers=_auth_header(s_token))
        conv_id = resp.get_json()['conversation_id']

        messages = ChatMessage.query.filter_by(
            conversation_id=conv_id,
            msg_type='system',
        ).all()
        assert len(messages) == 1
        assert '¥20.0/米' in messages[0].content
        assert '交货' not in messages[0].content
