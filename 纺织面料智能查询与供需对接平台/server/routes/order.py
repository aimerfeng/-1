"""Order management routes for the textile fabric platform.

Provides endpoints for creating, listing, and managing purchase orders,
including order status transitions with validation.

Endpoints:
    POST   /api/orders              - Create an order (buyer only)
    GET    /api/orders              - List orders (role-based, paginated)
    GET    /api/orders/<id>         - Get order detail with items and fabric info
    PUT    /api/orders/<id>/status  - Update order status with transition validation
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.order import Order, OrderItem, generate_order_no, validate_status_transition
from server.models.fabric import Fabric
from server.models.user import User
from server.routes.auth import role_required
from server.services.notification import send_notification

order_bp = Blueprint('order', __name__)


@order_bp.route('', methods=['POST'])
@jwt_required()
@role_required('buyer')
def create_order():
    """Create a new purchase order.

    Only buyers can create orders. The request must contain items (array of
    {fabric_id, quantity}) and an address. For each item, the fabric's price
    is used as unit_price, and subtotal = quantity * unit_price. The supplier_id
    is derived from the first fabric's supplier. All items must belong to the
    same supplier.

    Request JSON:
        items (list, required): Array of {fabric_id: int, quantity: int}
        address (str, required): Delivery address

    Returns:
        201: Created order data with items
        400: Validation errors
        404: Fabric not found
    """
    data = request.get_json(silent=True) or {}

    errors = {}

    # Validate address
    address = data.get('address', '').strip() if isinstance(data.get('address'), str) else ''
    if not address:
        errors['address'] = '收货地址为必填项'

    # Validate items
    items = data.get('items')
    if items is None:
        errors['items'] = '订单项为必填项'
    elif not isinstance(items, list) or len(items) == 0:
        errors['items'] = '订单项不能为空'

    if errors:
        return jsonify({
            'code': 400,
            'message': '参数校验失败',
            'errors': errors,
        }), 400

    # Validate each item and look up fabrics
    item_errors = []
    fabric_records = []
    for i, item in enumerate(items):
        item_err = {}
        if not isinstance(item, dict):
            item_errors.append({f'item_{i}': '订单项格式错误'})
            continue

        fabric_id = item.get('fabric_id')
        if fabric_id is None:
            item_err['fabric_id'] = '面料ID为必填项'
        elif not isinstance(fabric_id, int):
            item_err['fabric_id'] = '面料ID必须为整数'

        quantity = item.get('quantity')
        if quantity is None:
            item_err['quantity'] = '数量为必填项'
        elif not isinstance(quantity, int) or quantity <= 0:
            item_err['quantity'] = '数量必须为正整数'

        if item_err:
            item_errors.append(item_err)
            continue

        # Look up fabric
        fabric = db.session.get(Fabric, fabric_id)
        if fabric is None:
            return jsonify({
                'code': 404,
                'message': f'面料(ID={fabric_id})不存在',
            }), 404

        fabric_records.append((fabric, quantity))
        item_errors.append(None)  # placeholder for no error

    # Check if there were item-level validation errors
    has_item_errors = any(e is not None for e in item_errors)
    if has_item_errors:
        actual_errors = {f'item_{i}': e for i, e in enumerate(item_errors) if e is not None}
        return jsonify({
            'code': 400,
            'message': '订单项校验失败',
            'errors': actual_errors,
        }), 400

    # All items must belong to the same supplier
    supplier_id = fabric_records[0][0].supplier_id
    for fabric, _ in fabric_records:
        if fabric.supplier_id != supplier_id:
            return jsonify({
                'code': 400,
                'message': '所有订单项必须来自同一供应商',
                'errors': {'items': '所有订单项必须来自同一供应商'},
            }), 400

    # Check stock availability
    for fabric, quantity in fabric_records:
        if fabric.stock_quantity < quantity:
            return jsonify({
                'code': 400,
                'message': f'面料「{fabric.name}」库存不足，当前库存 {fabric.stock_quantity} 米，需要 {quantity} 米',
            }), 400

    # Calculate totals and create order
    buyer_id = int(get_jwt_identity())
    order_no = generate_order_no()
    total_amount = 0.0

    order = Order(
        buyer_id=buyer_id,
        supplier_id=supplier_id,
        order_no=order_no,
        total_amount=0.0,  # will be updated
        address=address,
        status='pending',
    )
    db.session.add(order)
    db.session.flush()  # get order.id

    order_items = []
    for fabric, quantity in fabric_records:
        unit_price = fabric.price
        subtotal = quantity * unit_price
        total_amount += subtotal

        order_item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        )
        db.session.add(order_item)
        order_items.append(order_item)

    order.total_amount = total_amount

    # Deduct stock for each fabric
    for fabric, quantity in fabric_records:
        fabric.stock_quantity -= quantity

    db.session.commit()

    # Send notification to supplier
    send_notification(
        user_id=supplier_id,
        notification_type='order',
        title='新订单',
        content=f'您收到一个新订单，订单号: {order_no}，总金额: {total_amount:.2f}元',
        ref_id=order.id,
        ref_type='order',
    )

    # Send notification to buyer (order confirmation)
    send_notification(
        user_id=buyer_id,
        notification_type='order',
        title='订单已创建',
        content=f'您的订单已成功创建，订单号: {order_no}，总金额: {total_amount:.2f}元',
        ref_id=order.id,
        ref_type='order',
    )

    # Build response with items
    result = order.to_dict()
    result['items'] = [item.to_dict() for item in order_items]

    return jsonify(result), 201



@order_bp.route('', methods=['GET'])
@jwt_required()
def list_orders():
    """List orders with role-based filtering and pagination.

    Buyers see their own orders. Suppliers see orders addressed to them.
    Admins see all orders. Results are ordered by creation time descending.
    Optionally filter by status query parameter.

    Each order item includes demand_title, quote_price, and counterparty
    company_name (for buyer: supplier's company; for supplier: buyer's company;
    for admin: both buyer and supplier info).

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20
        status (str, optional): Filter by order status

    Returns:
        200: Paginated order list with total count and enhanced info
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401

    query = Order.query

    # Role-based filtering: admin sees all, buyer/supplier see their own
    if user.role == 'buyer':
        query = query.filter_by(buyer_id=user_id)
    elif user.role == 'supplier':
        query = query.filter_by(supplier_id=user_id)
    # admin: no filter, sees all orders

    # Optional status filter
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter_by(status=status_filter)

    # Order by creation time descending
    query = query.order_by(Order.created_at.desc())

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
    for order in pagination.items:
        order_dict = order.to_dict()

        # Include demand_title if demand is linked
        if order.demand_id and order.demand:
            order_dict['demand_title'] = order.demand.title
        else:
            order_dict['demand_title'] = None

        # Include quote_price if quote is linked
        if order.quote_id and order.quote:
            order_dict['quote_price'] = order.quote.price
        else:
            order_dict['quote_price'] = None

        # Include counterparty info based on viewer's role
        if user.role == 'admin':
            # Admin sees both buyer and supplier info
            buyer = db.session.get(User, order.buyer_id)
            supplier = db.session.get(User, order.supplier_id)
            order_dict['counterparty'] = {
                'buyer_company_name': buyer.company_name if buyer else None,
                'supplier_company_name': supplier.company_name if supplier else None,
            }
        elif user.role == 'buyer':
            # Buyer sees supplier as counterparty
            supplier = db.session.get(User, order.supplier_id)
            order_dict['counterparty'] = supplier.company_name if supplier else None
        elif user.role == 'supplier':
            # Supplier sees buyer as counterparty
            buyer = db.session.get(User, order.buyer_id)
            order_dict['counterparty'] = buyer.company_name if buyer else None

        items.append(order_dict)

    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200





@order_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_detail(order_id):
    """Get order detail including items, fabric info, and status timeline.

    The buyer, supplier, or admin can view order details. Admin can view
    any order. The response includes demand info and quote info when the
    order is linked to a demand/quote.

    Args:
        order_id: The order's database ID.

    Returns:
        200: Order detail with items, fabric info, buyer/supplier info,
             demand_info, quote_info, and timeline
        403: Not authorized to view this order
        404: Order not found
    """
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({
            'code': 404,
            'message': '订单不存在',
        }), 404

    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    # Allow buyer, supplier, or admin to view the order
    if user and user.role == 'admin':
        pass  # admin can view any order
    elif order.buyer_id != user_id and order.supplier_id != user_id:
        return jsonify({
            'code': 403,
            'message': '无权查看此订单',
        }), 403

    # Build order detail with items and fabric info
    result = order.to_dict()

    # Include items with fabric info
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    items_with_fabric = []
    for item in order_items:
        item_dict = item.to_dict()
        fabric = db.session.get(Fabric, item.fabric_id)
        if fabric:
            item_dict['fabric'] = fabric.to_dict()
        items_with_fabric.append(item_dict)
    result['items'] = items_with_fabric

    # Include buyer and supplier basic info
    buyer = db.session.get(User, order.buyer_id)
    supplier = db.session.get(User, order.supplier_id)
    if buyer:
        result['buyer'] = {
            'id': buyer.id,
            'company_name': buyer.company_name,
            'contact_name': buyer.contact_name,
            'phone': buyer.phone,
        }
    if supplier:
        result['supplier'] = {
            'id': supplier.id,
            'company_name': supplier.company_name,
            'contact_name': supplier.contact_name,
            'phone': supplier.phone,
        }

    # Include demand info if linked
    if order.demand_id and order.demand:
        result['demand_info'] = {
            'title': order.demand.title,
            'quantity': order.demand.quantity,
            'composition': order.demand.composition,
        }
    else:
        result['demand_info'] = None

    # Include quote info if linked
    if order.quote_id and order.quote:
        result['quote_info'] = {
            'price': order.quote.price,
            'delivery_days': order.quote.delivery_days,
            'message': order.quote.message,
        }
    else:
        result['quote_info'] = None

    # Include status timeline
    from server.models.order import ORDER_STATUSES
    current_index = ORDER_STATUSES.index(order.status) if order.status in ORDER_STATUSES else -1
    timeline = []
    for i, status in enumerate(ORDER_STATUSES):
        timeline.append({
            'status': status,
            'completed': i <= current_index,
            'current': i == current_index,
        })
    result['timeline'] = timeline

    return jsonify(result), 200




@order_bp.route('/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    """Update order status with transition validation.

    Only the supplier can advance the status, except the buyer can
    confirm 'received' and 'completed'. When transitioning to 'shipped',
    an optional tracking_no can be provided. After status change, a
    notification is sent to the other party.

    Args:
        order_id: The order's database ID.

    Request JSON:
        status (str, required): The new status to transition to
        tracking_no (str, optional): Tracking number (only used when status is 'shipped')

    Returns:
        200: Updated order data
        400: Invalid status transition
        403: Not authorized to update this order's status
        404: Order not found
    """
    order = db.session.get(Order, order_id)
    if order is None:
        return jsonify({
            'code': 404,
            'message': '订单不存在',
        }), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get('status')

    if not new_status:
        return jsonify({
            'code': 400,
            'message': '缺少目标状态',
        }), 400

    # Validate status transition
    if not validate_status_transition(order.status, new_status):
        return jsonify({
            'code': 400,
            'message': f'不允许从 {order.status} 转换到 {new_status}',
        }), 400

    # Check authorization: supplier can advance status, buyer can confirm 'received' and 'completed'
    user_id = int(get_jwt_identity())
    if new_status in ('received', 'completed'):
        # Buyer can confirm received and mark completed
        if order.buyer_id != user_id:
            return jsonify({
                'code': 403,
                'message': '只有采购方可以确认收货或完成订单',
            }), 403
    else:
        # Only supplier can advance other statuses (confirmed, producing, shipped)
        if order.supplier_id != user_id:
            return jsonify({
                'code': 403,
                'message': '只有供应商可以更新订单状态',
            }), 403

    # Store tracking number when transitioning to shipped
    if new_status == 'shipped':
        tracking_no = data.get('tracking_no')
        if tracking_no and isinstance(tracking_no, str):
            order.tracking_no = tracking_no.strip() or None

    order.status = new_status
    db.session.commit()

    # Send notification to the other party
    if user_id == order.buyer_id:
        notify_user_id = order.supplier_id
    else:
        notify_user_id = order.buyer_id

    status_labels = {
        'confirmed': '已确认',
        'producing': '生产中',
        'shipped': '已发货',
        'received': '已签收',
        'completed': '已完成',
    }
    status_label = status_labels.get(new_status, new_status)

    send_notification(
        user_id=notify_user_id,
        notification_type='order',
        title='订单状态更新',
        content=f'订单 {order.order_no} 状态已更新为: {status_label}',
        ref_id=order.id,
        ref_type='order',
    )

    return jsonify(order.to_dict()), 200
