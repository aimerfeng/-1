"""Sample management routes for the textile fabric platform.

Provides endpoints for creating, listing, and reviewing sample requests,
as well as querying sample logistics status.

Endpoints:
    POST   /api/samples              - Create a sample request (buyer only)
    GET    /api/samples              - List samples (role-based filtering)
    PUT    /api/samples/<id>/review  - Review sample request (supplier only)
    PUT    /api/samples/<id>/receive - Buyer confirms sample received
    GET    /api/samples/<id>/logistics - Query sample logistics status
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.sample import Sample
from server.models.fabric import Fabric
from server.models.user import User
from server.routes.auth import role_required
from server.services.logistics import create_logistics, query_logistics, sync_logistics_status
from server.services.notification import send_notification

sample_bp = Blueprint('sample', __name__)


@sample_bp.route('', methods=['POST'])
@jwt_required()
@role_required('buyer')
def create_sample():
    """Create a new sample request.

    Only buyers can create sample requests. The supplier_id is derived
    from the fabric's supplier. After creation, a notification is sent
    to the corresponding supplier.

    Request JSON:
        fabric_id (int, required): ID of the fabric to sample
        quantity (int, required): Quantity of samples requested
        address (str, required): Delivery address for the sample

    Returns:
        201: Created sample data
        400: Validation errors
        404: Fabric not found
    """
    data = request.get_json(silent=True) or {}

    errors = {}

    # Validate fabric_id
    fabric_id = data.get('fabric_id')
    if fabric_id is None:
        errors['fabric_id'] = '面料ID为必填项'
    elif not isinstance(fabric_id, int):
        errors['fabric_id'] = '面料ID必须为整数'

    # Validate quantity
    quantity = data.get('quantity')
    if quantity is None:
        errors['quantity'] = '数量为必填项'
    elif not isinstance(quantity, int) or quantity <= 0:
        errors['quantity'] = '数量必须为正整数'

    # Validate address
    address = data.get('address', '').strip() if isinstance(data.get('address'), str) else ''
    if not address:
        errors['address'] = '收货地址为必填项'

    if errors:
        return jsonify({
            'code': 400,
            'message': '参数校验失败',
            'errors': errors,
        }), 400

    # Check fabric exists
    fabric = db.session.get(Fabric, fabric_id)
    if fabric is None:
        return jsonify({
            'code': 404,
            'message': '面料不存在',
        }), 404

    buyer_id = int(get_jwt_identity())

    sample = Sample(
        fabric_id=fabric_id,
        buyer_id=buyer_id,
        supplier_id=fabric.supplier_id,
        quantity=quantity,
        address=address,
        status='pending',
    )

    db.session.add(sample)
    db.session.commit()

    # Notify the supplier about the new sample request
    send_notification(
        user_id=fabric.supplier_id,
        notification_type='review',
        title='新样品申请',
        content=f'您收到一个新的样品申请，面料: {fabric.name}，数量: {quantity}',
        ref_id=sample.id,
        ref_type='sample',
    )

    return jsonify(sample.to_dict()), 201


@sample_bp.route('', methods=['GET'])
@jwt_required()
def list_samples():
    """List samples with role-based filtering and pagination.

    Buyers see only their own sample requests. Suppliers see sample
    requests sent to them.

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20

    Returns:
        200: Paginated sample list with total count
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    query = Sample.query

    if user.role == 'buyer':
        query = query.filter_by(buyer_id=user_id)
    elif user.role == 'supplier':
        query = query.filter_by(supplier_id=user_id)

    # Order by creation time descending
    query = query.order_by(Sample.created_at.desc())

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
        'items': [s.to_dict() for s in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@sample_bp.route('/<int:sample_id>/review', methods=['PUT'])
@jwt_required()
@role_required('supplier')
def review_sample(sample_id):
    """Review a sample request (supplier only).

    Suppliers can approve or reject sample requests sent to them.
    Approving triggers logistics creation. Rejecting requires a reason.
    After updating the status, a notification is sent to the buyer.

    Args:
        sample_id: The sample's database ID.

    Request JSON:
        status (str, required): 'approved' or 'rejected'
        reject_reason (str, required if rejected): Reason for rejection

    Returns:
        200: Updated sample data
        400: Validation errors
        403: Not the sample's supplier
        404: Sample not found
    """
    data = request.get_json(silent=True) or {}

    new_status = data.get('status')
    if new_status not in ('approved', 'rejected'):
        return jsonify({
            'code': 400,
            'message': '状态必须为 approved 或 rejected',
        }), 400

    sample = db.session.get(Sample, sample_id)
    if sample is None:
        return jsonify({
            'code': 404,
            'message': '样品申请不存在',
        }), 404

    # Verify the current user is the sample's supplier
    supplier_id = int(get_jwt_identity())
    if sample.supplier_id != supplier_id:
        return jsonify({
            'code': 403,
            'message': '无权审核此样品申请',
        }), 403

    # Only pending samples can be reviewed
    if sample.status != 'pending':
        return jsonify({
            'code': 400,
            'message': '该样品申请已审核，不能重复审核',
        }), 400

    if new_status == 'rejected':
        reject_reason = data.get('reject_reason', '').strip() if isinstance(data.get('reject_reason'), str) else ''
        if not reject_reason:
            return jsonify({
                'code': 400,
                'message': '拒绝时必须填写拒绝原因',
                'errors': {'reject_reason': '拒绝原因为必填项'},
            }), 400
        sample.status = 'rejected'
        sample.reject_reason = reject_reason
        db.session.commit()

        # Notify buyer about rejection
        send_notification(
            user_id=sample.buyer_id,
            notification_type='review',
            title='样品申请被拒绝',
            content=f'您的样品申请已被拒绝，原因: {reject_reason}',
            ref_id=sample.id,
            ref_type='sample',
        )

    elif new_status == 'approved':
        sample.status = 'approved'
        db.session.commit()

        # Trigger logistics creation
        create_logistics(sample.id, sample.address)

        # Notify buyer about approval
        send_notification(
            user_id=sample.buyer_id,
            notification_type='review',
            title='样品申请已通过',
            content='您的样品申请已通过审核，样品即将发出',
            ref_id=sample.id,
            ref_type='sample',
        )

    return jsonify(sample.to_dict()), 200


@sample_bp.route('/<int:sample_id>/receive', methods=['PUT'])
@jwt_required()
@role_required('buyer')
def receive_sample(sample_id):
    """Buyer confirms a shipped sample has been received.

    This endpoint is the only place that transitions a sample from
    shipping -> received. Logistics sync updates tracking details only.

    Args:
        sample_id: The sample's database ID.

    Returns:
        200: Updated sample data
        400: Sample not in shipping status
        403: Not the sample's buyer
        404: Sample not found
    """
    sample = db.session.get(Sample, sample_id)
    if sample is None:
        return jsonify({
            'code': 404,
            'message': 'Sample not found',
        }), 404

    buyer_id = int(get_jwt_identity())
    if sample.buyer_id != buyer_id:
        return jsonify({
            'code': 403,
            'message': 'Only the sample buyer can confirm receipt',
        }), 403

    if sample.status != 'shipping':
        return jsonify({
            'code': 400,
            'message': 'Only shipping samples can be received',
        }), 400

    sample.status = 'received'
    db.session.commit()

    send_notification(
        user_id=sample.supplier_id,
        notification_type='logistics',
        title='Sample received',
        content=f'Sample request #{sample.id} has been confirmed as received.',
        ref_id=sample.id,
        ref_type='sample',
    )

    return jsonify(sample.to_dict()), 200


@sample_bp.route('/<int:sample_id>/logistics', methods=['GET'])
@jwt_required()
def get_sample_logistics(sample_id):
    """Query logistics status for a sample.

    Returns the logistics tracking information for a sample,
    including the tracking number and status details.

    Args:
        sample_id: The sample's database ID.

    Returns:
        200: Logistics status data
        404: Sample not found or no logistics info
    """
    sample = db.session.get(Sample, sample_id)
    if sample is None:
        return jsonify({
            'code': 404,
            'message': '样品申请不存在',
        }), 404

    # Verify the current user is the buyer or supplier of this sample
    user_id = int(get_jwt_identity())
    if sample.buyer_id != user_id and sample.supplier_id != user_id:
        return jsonify({
            'code': 403,
            'message': '无权查看此样品物流信息',
        }), 403

    # Trigger a best-effort sync before returning logistics details so the
    # buyer can see the latest status without waiting for a background job.
    sync_logistics_status(sample.id)
    db.session.refresh(sample)

    if not sample.logistics_no:
        return jsonify({
            'code': 404,
            'message': '暂无物流信息',
            'logistics': None,
        }), 404

    # Prefer already-synced DB data, fallback to direct query if unavailable.
    logistics_data = sample.logistics_info or query_logistics(sample.logistics_no)

    # Normalize tracking list shape for frontend timeline rendering.
    if isinstance(logistics_data, dict):
        details = logistics_data.get('details')
        if logistics_data.get('traces') is None and isinstance(details, list):
            logistics_data['traces'] = details

    return jsonify({
        'sample_id': sample.id,
        'logistics_no': sample.logistics_no,
        'logistics': logistics_data,
    }), 200
