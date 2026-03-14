"""Admin routes for the textile fabric platform.

Provides endpoints for admin-only operations such as user certification
review and user management.

Endpoints:
    GET  /api/admin/users              - List users (filterable by certification status)
    PUT  /api/admin/users/<id>/certify - Approve or reject user certification
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.user import User
from server.routes.auth import role_required
from server.services.notification import send_notification

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_users():
    """List users with optional certification status filter.

    Query Parameters:
        status (str, optional): Filter by certification_status
            (pending/approved/rejected). Defaults to 'pending'.
        page (int, optional): Page number, defaults to 1.
        per_page (int, optional): Items per page, defaults to 20.

    Returns:
        JSON with paginated user list.
    """
    status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate status parameter
    valid_statuses = ('pending', 'approved', 'rejected', 'all')
    if status not in valid_statuses:
        return jsonify({
            'code': 400,
            'message': f'无效的状态参数，有效值为: {", ".join(valid_statuses)}',
        }), 400

    # Clamp per_page to reasonable bounds
    per_page = max(1, min(per_page, 100))
    page = max(1, page)

    query = User.query
    if status != 'all':
        query = query.filter_by(certification_status=status)
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False,
    )

    users = []
    for user in pagination.items:
        users.append({
            'id': user.id,
            'company_name': user.company_name,
            'contact_name': user.contact_name,
            'phone': user.phone,
            'role': user.role,
            'certification_status': user.certification_status,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        })

    return jsonify({
        'items': users,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
    }), 200


@admin_bp.route('/users/<int:user_id>/certify', methods=['PUT'])
@jwt_required()
@role_required('admin')
def certify_user(user_id):
    """Approve or reject a user's certification.

    Path Parameters:
        user_id (int): The ID of the user to certify.

    Request JSON:
        status (str, required): 'approved' or 'rejected'.
        reason (str, optional): Rejection reason (used when status is 'rejected').

    Returns:
        JSON with updated user info.
    """
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    reason = data.get('reason', '')

    if new_status not in ('approved', 'rejected'):
        return jsonify({
            'code': 400,
            'message': '状态必须为 approved 或 rejected',
        }), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({
            'code': 404,
            'message': '用户不存在',
        }), 404

    user.certification_status = new_status
    db.session.commit()

    # Send review notification to the user
    if new_status == 'approved':
        title = '资质审核通过'
        content = '恭喜！您的资质审核已通过，现在可以使用平台全部功能。'
    else:
        title = '资质审核未通过'
        content = f'很抱歉，您的资质审核未通过。'
        if reason:
            content += f'原因：{reason}'

    send_notification(
        user_id=user.id,
        notification_type='review',
        title=title,
        content=content,
        ref_id=user.id,
        ref_type='user',
    )

    return jsonify({
        'user': user.to_dict(),
    }), 200
