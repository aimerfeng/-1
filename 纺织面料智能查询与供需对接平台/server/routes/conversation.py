"""Conversation and chat message routes for the textile fabric platform.

Provides endpoints for listing conversations with role-based filtering,
including counterparty info, demand title, and unread message counts.

Endpoints:
    GET /api/conversations - List conversations (role-based, paginated)
    GET /api/conversations/<conv_id>/messages - List messages (paginated, chronological)
    POST /api/conversations/<conv_id>/messages - Send a message (participants only)
"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.conversation import Conversation, ChatMessage
from server.models.demand import Demand
from server.models.user import User

conversation_bp = Blueprint('conversation', __name__)


@conversation_bp.route('', methods=['GET'])
@jwt_required()
def list_conversations():
    """List conversations with role-based filtering and pagination.

    Buyers see conversations where they are the buyer.
    Suppliers see conversations where they are the supplier.
    Admins see all conversations.

    Each conversation includes counterparty company_name, demand_title,
    last_message_preview, last_message_at, and unread_count.

    Results are sorted by last_message_at descending (nulls last).

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20

    Returns:
        200: Paginated conversation list with enhanced info
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    query = Conversation.query

    # Role-based filtering
    if user.role == 'buyer':
        query = query.filter(Conversation.buyer_id == user_id)
    elif user.role == 'supplier':
        query = query.filter(Conversation.supplier_id == user_id)
    # admin: no filter, sees all conversations

    # Sort by last_message_at descending, nulls last
    query = query.order_by(
        Conversation.last_message_at.desc().nulls_last(),
        Conversation.created_at.desc(),
    )

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Build enhanced response items
    items = []
    for conv in pagination.items:
        conv_dict = conv.to_dict()

        # Include demand_title
        demand = db.session.get(Demand, conv.demand_id)
        conv_dict['demand_title'] = demand.title if demand else None

        # Include counterparty info based on viewer's role
        if user.role == 'admin':
            buyer = db.session.get(User, conv.buyer_id)
            supplier = db.session.get(User, conv.supplier_id)
            conv_dict['counterparty'] = {
                'buyer_company_name': buyer.company_name if buyer else None,
                'supplier_company_name': supplier.company_name if supplier else None,
            }
        elif user.role == 'buyer':
            supplier = db.session.get(User, conv.supplier_id)
            conv_dict['counterparty'] = supplier.company_name if supplier else None
        elif user.role == 'supplier':
            buyer = db.session.get(User, conv.buyer_id)
            conv_dict['counterparty'] = buyer.company_name if buyer else None

        # Calculate unread_count per conversation
        if user.role == 'admin':
            conv_dict['unread_count'] = 0
        else:
            unread_count = ChatMessage.query.filter(
                ChatMessage.conversation_id == conv.id,
                ChatMessage.sender_id != user_id,
                ChatMessage.is_read == False,  # noqa: E712
            ).count()
            conv_dict['unread_count'] = unread_count

        items.append(conv_dict)

    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@conversation_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def unread_count():
    """Get total unread message count across all conversations.

    Counts all ChatMessages where the current user is a participant
    in the conversation, the sender is the other party, and is_read
    is False.

    Returns:
        200: { "count": int }
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    # Find all conversations where user is a participant
    user_conversations = Conversation.query.filter(
        db.or_(
            Conversation.buyer_id == user_id,
            Conversation.supplier_id == user_id,
        )
    ).all()

    conv_ids = [c.id for c in user_conversations]

    if not conv_ids:
        return jsonify({'count': 0}), 200

    # Count unread messages from other parties in those conversations
    count = ChatMessage.query.filter(
        ChatMessage.conversation_id.in_(conv_ids),
        ChatMessage.sender_id != user_id,
        ChatMessage.is_read == False,  # noqa: E712
    ).count()

    return jsonify({'count': count}), 200


@conversation_bp.route('/<int:conv_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(conv_id):
    """Get messages for a conversation with pagination.

    Returns messages in chronological order (oldest first).
    Auto-marks messages from the other party as read (not for admin).

    Only participants (buyer/supplier) and admin can view messages.

    Args:
        conv_id: The conversation ID.

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 30

    Returns:
        200: Paginated message list in chronological order
        403: User is not a participant or admin
        404: Conversation not found
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    conv = db.session.get(Conversation, conv_id)
    if conv is None:
        return jsonify({'code': 404, 'message': '会话不存在'}), 404

    # Check access: must be participant or admin
    is_participant = user_id in (conv.buyer_id, conv.supplier_id)
    is_admin = user.role == 'admin'

    if not is_participant and not is_admin:
        return jsonify({'code': 403, 'message': '无权查看此会话'}), 403

    # Auto-mark other party's messages as read (only for participants, not admin)
    if is_participant:
        ChatMessage.query.filter(
            ChatMessage.conversation_id == conv_id,
            ChatMessage.sender_id != user_id,
            ChatMessage.is_read == False,  # noqa: E712
        ).update({'is_read': True})
        db.session.commit()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    # Query messages in chronological order (oldest first)
    query = ChatMessage.query.filter(
        ChatMessage.conversation_id == conv_id,
    ).order_by(ChatMessage.created_at.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [msg.to_dict() for msg in pagination.items]

    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@conversation_bp.route('/<int:conv_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conv_id):
    """Send a message in a conversation.

    Only participants (buyer/supplier) can send messages.
    Admin can view but NOT send messages (returns 403).

    Creates a ChatMessage with msg_type='text' and updates the
    conversation's last_message_at and last_message_preview.

    Args:
        conv_id: The conversation ID.

    Request Body:
        content (str): The message content (non-empty).

    Returns:
        201: Created message
        400: Empty content
        403: Admin or non-participant
        404: Conversation not found
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    conv = db.session.get(Conversation, conv_id)
    if conv is None:
        return jsonify({'code': 404, 'message': '会话不存在'}), 404

    # Admin can view but not send
    if user.role == 'admin':
        return jsonify({'code': 403, 'message': '管理员仅可查看会话'}), 403

    # Must be a participant
    is_participant = user_id in (conv.buyer_id, conv.supplier_id)
    if not is_participant:
        return jsonify({'code': 403, 'message': '无权在此会话中发送消息'}), 403

    # Validate content
    data = request.get_json(silent=True) or {}
    content = data.get('content', '').strip() if data.get('content') else ''

    if not content:
        return jsonify({'code': 400, 'message': '消息内容不能为空'}), 400

    # Create the message
    now = datetime.utcnow()
    message = ChatMessage(
        conversation_id=conv_id,
        sender_id=user_id,
        content=content,
        msg_type='text',
        is_read=False,
        created_at=now,
    )
    db.session.add(message)

    # Update conversation metadata
    conv.last_message_at = now
    conv.last_message_preview = content[:100]

    db.session.commit()

    return jsonify(message.to_dict()), 201
