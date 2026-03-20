"""Admin routes for the textile fabric platform.

Provides endpoints for admin-only operations such as user certification
review, user management, and platform statistics.

Endpoints:
    GET  /api/admin/users              - List users (filterable by certification status)
    PUT  /api/admin/users/<id>/certify - Approve or reject user certification
    GET  /api/admin/stats              - Platform statistics overview
"""

from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from server.extensions import db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.order import Order
from server.models.demand import Demand
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


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@role_required('admin')
def platform_stats():
    """Get platform-wide statistics for admin dashboard.

    Returns:
        JSON with overview counts, distribution data, and 7-day trends.
    """
    # --- Overview counts ---
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    total_fabrics = db.session.query(func.count(Fabric.id)).scalar() or 0
    total_orders = db.session.query(func.count(Order.id)).scalar() or 0
    total_demands = db.session.query(func.count(Demand.id)).scalar() or 0

    # --- User role distribution ---
    role_rows = db.session.query(
        User.role, func.count(User.id)
    ).group_by(User.role).all()
    role_dist = {r: c for r, c in role_rows}

    # --- User certification distribution ---
    cert_rows = db.session.query(
        User.certification_status, func.count(User.id)
    ).group_by(User.certification_status).all()
    cert_dist = {s: c for s, c in cert_rows}

    # --- Order status distribution ---
    order_rows = db.session.query(
        Order.status, func.count(Order.id)
    ).group_by(Order.status).all()
    order_dist = {s: c for s, c in order_rows}

    # --- Demand status distribution ---
    demand_rows = db.session.query(
        Demand.status, func.count(Demand.id)
    ).group_by(Demand.status).all()
    demand_dist = {s: c for s, c in demand_rows}

    # --- 7-day trends ---
    today = datetime.utcnow().date()
    days = []
    user_trend = []
    order_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(next_day, datetime.min.time())

        u_count = db.session.query(func.count(User.id)).filter(
            User.created_at >= day_start, User.created_at < day_end
        ).scalar() or 0

        o_count = db.session.query(func.count(Order.id)).filter(
            Order.created_at >= day_start, Order.created_at < day_end
        ).scalar() or 0

        days.append(day.strftime('%m-%d'))
        user_trend.append(u_count)
        order_trend.append(o_count)

    # --- Order total amount ---
    total_amount = db.session.query(
        func.coalesce(func.sum(Order.total_amount), 0)
    ).scalar() or 0

    return jsonify({
        'overview': {
            'total_users': total_users,
            'total_fabrics': total_fabrics,
            'total_orders': total_orders,
            'total_demands': total_demands,
            'total_amount': round(float(total_amount), 2),
        },
        'user_role_dist': {
            'buyer': role_dist.get('buyer', 0),
            'supplier': role_dist.get('supplier', 0),
            'admin': role_dist.get('admin', 0),
        },
        'user_cert_dist': {
            'pending': cert_dist.get('pending', 0),
            'approved': cert_dist.get('approved', 0),
            'rejected': cert_dist.get('rejected', 0),
        },
        'order_status_dist': {
            'pending': order_dist.get('pending', 0),
            'confirmed': order_dist.get('confirmed', 0),
            'producing': order_dist.get('producing', 0),
            'shipped': order_dist.get('shipped', 0),
            'received': order_dist.get('received', 0),
            'completed': order_dist.get('completed', 0),
        },
        'demand_status_dist': {
            'open': demand_dist.get('open', 0),
            'matched': demand_dist.get('matched', 0),
            'closed': demand_dist.get('closed', 0),
        },
        'trends': {
            'days': days,
            'new_users': user_trend,
            'new_orders': order_trend,
        },
    }), 200
