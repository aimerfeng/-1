"""Message notification routes for the textile fabric platform.

Provides endpoints for listing, reading, and counting user messages,
supporting pagination and read/unread filtering.

Endpoints:
    GET    /api/messages              - List messages (paginated, filterable by read status)
    PUT    /api/messages/<id>/read    - Mark a message as read
    GET    /api/messages/unread-count - Get unread message count
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.message import Message

message_bp = Blueprint('message', __name__)


@message_bp.route('', methods=['GET'])
@jwt_required()
def list_messages():
    """List messages for the current user with pagination and filtering.

    Returns messages ordered by creation time descending. Supports
    filtering by read status via the is_read query parameter.

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20
        is_read (str, optional): Filter by read status ('true' or 'false')

    Returns:
        200: Paginated message list with total count
    """
    user_id = int(get_jwt_identity())

    query = Message.query.filter_by(user_id=user_id)

    # Optional is_read filter
    is_read_param = request.args.get('is_read')
    if is_read_param is not None:
        if is_read_param.lower() == 'true':
            query = query.filter_by(is_read=True)
        elif is_read_param.lower() == 'false':
            query = query.filter_by(is_read=False)

    # Order by creation time descending
    query = query.order_by(Message.created_at.desc())

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

    return jsonify({
        'items': [m.to_dict() for m in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@message_bp.route('/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(message_id):
    """Mark a specific message as read.

    Only the message's owner can mark it as read. If the message
    is already read, it is returned as-is (idempotent operation).

    Args:
        message_id: The message's database ID.

    Returns:
        200: Updated message data
        403: Not the message's owner
        404: Message not found
    """
    message = db.session.get(Message, message_id)
    if message is None:
        return jsonify({
            'code': 404,
            'message': '消息不存在',
        }), 404

    user_id = int(get_jwt_identity())
    if message.user_id != user_id:
        return jsonify({
            'code': 403,
            'message': '无权操作此消息',
        }), 403

    # Idempotent: set is_read to True regardless of current state
    if not message.is_read:
        message.is_read = True
        db.session.commit()

    return jsonify(message.to_dict()), 200


@message_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def unread_count():
    """Get the count of unread messages for the current user.

    Used for displaying badge counts on the tabBar.

    Returns:
        200: { count: int }
    """
    user_id = int(get_jwt_identity())

    count = Message.query.filter_by(
        user_id=user_id,
        is_read=False,
    ).count()

    return jsonify({'count': count}), 200
