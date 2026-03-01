"""Demand management routes for the textile fabric platform.

Provides endpoints for creating, listing, and viewing purchase demands,
as well as retrieving matching results between demands and fabrics.

Endpoints:
    POST   /api/demands              - Create a new demand (buyer only)
    GET    /api/demands              - List demands (role-based filtering)
    GET    /api/demands/<id>         - Get demand detail
    GET    /api/demands/<id>/matches - Get match results for a demand
    POST   /api/demands/<id>/quotes  - Submit a quote (supplier only)
    GET    /api/demands/<id>/quotes  - List quotes for a demand
    PUT    /api/demands/<id>/quotes/<qid>/accept - Accept a quote (buyer only)
"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.conversation import Conversation, ChatMessage
from server.models.demand import Demand, MatchResult, Quote
from server.models.fabric import Fabric
from server.models.order import Order, generate_order_no
from server.models.user import User
from server.routes.auth import role_required
from server.services.matching import MatchingEngine
from server.services.notification import send_notification

demand_bp = Blueprint('demand', __name__)


def _run_matching_for_demand(demand):
    """Run matching engine for a demand against all active fabrics."""
    engine = MatchingEngine()
    active_fabrics = Fabric.query.filter_by(status='active').all()
    if not active_fabrics:
        return []
    match_results_data = engine.match(demand, active_fabrics)
    created_results = []
    for result_data in match_results_data:
        mr = MatchResult(
            demand_id=demand.id, fabric_id=result_data['fabric_id'],
            score=result_data['score'], score_detail=result_data['score_detail'],
        )
        db.session.add(mr)
        created_results.append(mr)
    db.session.commit()
    for mr in created_results:
        fabric = db.session.get(Fabric, mr.fabric_id)
        if fabric and fabric.supplier_id:
            send_notification(
                user_id=fabric.supplier_id, notification_type='match',
                title='\u65b0\u7684\u4f9b\u9700\u5339\u914d',
                content=f'\u60a8\u7684\u9762\u6599\u300c{fabric.name}\u300d\u4e0e\u91c7\u8d2d\u9700\u6c42\u300c{demand.title}\u300d\u5339\u914d\u6210\u529f\uff0c\u5339\u914d\u5ea6 {mr.score:.1f}%',
                ref_id=demand.id, ref_type='demand',
            )
    return created_results


def _run_matching_for_fabric(fabric):
    """Run matching engine for a new fabric against all open demands."""
    engine = MatchingEngine()
    open_demands = Demand.query.filter_by(status='open').all()
    if not open_demands:
        return []
    created_results = []
    for demand in open_demands:
        score, score_detail = engine.calculate_score(demand, fabric)
        mr = MatchResult(
            demand_id=demand.id, fabric_id=fabric.id,
            score=score, score_detail=score_detail,
        )
        db.session.add(mr)
        created_results.append(mr)
    db.session.commit()
    for mr in created_results:
        demand_obj = db.session.get(Demand, mr.demand_id)
        if demand_obj and demand_obj.buyer_id:
            send_notification(
                user_id=demand_obj.buyer_id, notification_type='match',
                title='\u65b0\u7684\u9762\u6599\u5339\u914d',
                content=f'\u65b0\u9762\u6599\u300c{fabric.name}\u300d\u4e0e\u60a8\u7684\u91c7\u8d2d\u9700\u6c42\u300c{demand_obj.title}\u300d\u5339\u914d\u6210\u529f\uff0c\u5339\u914d\u5ea6 {mr.score:.1f}%',
                ref_id=fabric.id, ref_type='fabric',
            )
    return created_results


def _get_or_create_conversation(demand_id, buyer_id, supplier_id):
    """Get an existing conversation or create a new one."""
    conv = Conversation.query.filter_by(
        demand_id=demand_id, buyer_id=buyer_id, supplier_id=supplier_id,
    ).first()
    if conv is None:
        conv = Conversation(
            demand_id=demand_id, buyer_id=buyer_id, supplier_id=supplier_id,
        )
        db.session.add(conv)
        db.session.commit()
    return conv


def _add_system_message(conversation, sender_id, content):
    """Add a system message to a conversation and update metadata."""
    now = datetime.utcnow()
    msg = ChatMessage(
        conversation_id=conversation.id, sender_id=sender_id,
        content=content, msg_type='system', is_read=False, created_at=now,
    )
    db.session.add(msg)
    conversation.last_message_at = now
    conversation.last_message_preview = content[:100]
    db.session.commit()
    return msg


@demand_bp.route('', methods=['POST'])
@jwt_required()
@role_required('buyer')
def create_demand():
    """Create a new purchase demand (buyer only)."""
    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip() if isinstance(data.get('title'), str) else ''
    if not title:
        return jsonify({
            'code': 400, 'message': '\u53c2\u6570\u6821\u9a8c\u5931\u8d25',
            'errors': {'title': '\u6807\u9898\u4e3a\u5fc5\u586b\u9879'},
        }), 400
    buyer_id = int(get_jwt_identity())
    demand = Demand(
        buyer_id=buyer_id, title=title,
        composition=data.get('composition'),
        weight_min=data.get('weight_min'), weight_max=data.get('weight_max'),
        width_min=data.get('width_min'), width_max=data.get('width_max'),
        craft=data.get('craft'), color=data.get('color'),
        price_min=data.get('price_min'), price_max=data.get('price_max'),
        quantity=data.get('quantity'), status='open',
    )
    db.session.add(demand)
    db.session.commit()
    match_results = _run_matching_for_demand(demand)
    result = demand.to_dict()
    result['match_count'] = len(match_results)
    return jsonify(result), 201


@demand_bp.route('', methods=['GET'])
@jwt_required()
def list_demands():
    """List demands with role-based filtering and pagination."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({'code': 401, 'message': '\u7528\u6237\u4e0d\u5b58\u5728'}), 401
    query = Demand.query
    if user.role == 'buyer':
        query = query.filter_by(buyer_id=user_id)
    else:
        query = query.filter_by(status='open')
    query = query.order_by(Demand.created_at.desc())
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
        'items': [d.to_dict() for d in pagination.items],
        'total': pagination.total, 'page': page, 'per_page': per_page,
    }), 200


@demand_bp.route('/<int:demand_id>', methods=['GET'])
@jwt_required()
def get_demand(demand_id):
    """Get demand detail by ID, including buyer info and quote count."""
    demand = db.session.get(Demand, demand_id)
    if demand is None:
        return jsonify({'code': 404, 'message': '\u9700\u6c42\u4e0d\u5b58\u5728'}), 404
    result = demand.to_dict()
    buyer = db.session.get(User, demand.buyer_id)
    if buyer:
        result['buyer_info'] = {
            'company_name': buyer.company_name,
            'contact_name': buyer.contact_name,
            'phone': buyer.phone,
            'certification_status': buyer.certification_status,
        }
    result['quote_count'] = Quote.query.filter_by(demand_id=demand_id).count()
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user and user.role == 'supplier':
        my_quote = Quote.query.filter_by(
            demand_id=demand_id, supplier_id=user_id,
        ).first()
        result['my_quote'] = my_quote.to_dict() if my_quote else None
    return jsonify(result), 200


@demand_bp.route('/<int:demand_id>/matches', methods=['GET'])
@jwt_required()
def get_demand_matches(demand_id):
    """Get match results for a demand, sorted by score descending."""
    demand = db.session.get(Demand, demand_id)
    if demand is None:
        return jsonify({'code': 404, 'message': '\u9700\u6c42\u4e0d\u5b58\u5728'}), 404
    match_results = (
        MatchResult.query.filter_by(demand_id=demand_id)
        .order_by(MatchResult.score.desc()).all()
    )
    items = []
    for mr in match_results:
        rd = mr.to_dict()
        rd['fabric'] = mr.fabric.to_dict() if mr.fabric else None
        items.append(rd)
    return jsonify({'items': items, 'total': len(items)}), 200


@demand_bp.route('/<int:demand_id>/quotes', methods=['POST'])
@jwt_required()
@role_required('supplier')
def create_quote(demand_id):
    """Submit a quote for a demand (supplier only).

    Also creates a Conversation and initial system message.
    """
    demand = db.session.get(Demand, demand_id)
    if demand is None:
        return jsonify({'code': 404, 'message': '\u9700\u6c42\u4e0d\u5b58\u5728'}), 404
    if demand.status != 'open':
        return jsonify({'code': 400, 'message': '\u8be5\u9700\u6c42\u5df2\u5173\u95ed\uff0c\u65e0\u6cd5\u62a5\u4ef7'}), 400
    supplier_id = int(get_jwt_identity())
    existing = Quote.query.filter_by(
        demand_id=demand_id, supplier_id=supplier_id,
    ).first()
    if existing:
        return jsonify({'code': 409, 'message': '\u60a8\u5df2\u5bf9\u8be5\u9700\u6c42\u63d0\u4ea4\u8fc7\u62a5\u4ef7'}), 409
    data = request.get_json(silent=True) or {}
    price = data.get('price')
    if price is None or not isinstance(price, (int, float)) or price <= 0:
        return jsonify({
            'code': 400, 'message': '\u53c2\u6570\u6821\u9a8c\u5931\u8d25',
            'errors': {'price': '\u8bf7\u8f93\u5165\u6709\u6548\u7684\u62a5\u4ef7\u91d1\u989d'},
        }), 400
    quote = Quote(
        demand_id=demand_id, supplier_id=supplier_id,
        price=float(price), delivery_days=data.get('delivery_days'),
        message=data.get('message', ''), status='pending',
    )
    db.session.add(quote)
    db.session.commit()
    conversation = _get_or_create_conversation(
        demand_id=demand_id, buyer_id=demand.buyer_id, supplier_id=supplier_id,
    )
    delivery_info = f'\uff0c\u4ea4\u8d27 {quote.delivery_days} \u5929' if quote.delivery_days else ''
    system_content = f'\u4f9b\u5e94\u5546\u63d0\u4ea4\u4e86\u62a5\u4ef7\uff1a\xA5{quote.price}/\u7c73{delivery_info}'
    _add_system_message(conversation, supplier_id, system_content)
    send_notification(
        user_id=demand.buyer_id, notification_type='quote',
        title='\u6536\u5230\u65b0\u62a5\u4ef7',
        content=f'\u60a8\u7684\u9700\u6c42\u300c{demand.title}\u300d\u6536\u5230\u4e86\u4e00\u4e2a\u65b0\u7684\u4f9b\u5e94\u5546\u62a5\u4ef7\uff0c\u62a5\u4ef7 \xA5{price}/\u7c73',
        ref_id=demand.id, ref_type='demand',
    )
    result = quote.to_dict()
    result['conversation_id'] = conversation.id
    return jsonify(result), 201


@demand_bp.route('/<int:demand_id>/quotes', methods=['GET'])
@jwt_required()
def list_quotes(demand_id):
    """List all quotes for a demand."""
    demand = db.session.get(Demand, demand_id)
    if demand is None:
        return jsonify({'code': 404, 'message': '\u9700\u6c42\u4e0d\u5b58\u5728'}), 404
    quotes = (
        Quote.query.filter_by(demand_id=demand_id)
        .order_by(Quote.created_at.desc()).all()
    )
    items = []
    for q in quotes:
        qd = q.to_dict()
        supplier = db.session.get(User, q.supplier_id)
        if supplier:
            qd['supplier_info'] = {
                'company_name': supplier.company_name,
                'contact_name': supplier.contact_name,
                'certification_status': supplier.certification_status,
            }
        items.append(qd)
    return jsonify({'items': items, 'total': len(items)}), 200


@demand_bp.route('/<int:demand_id>/quotes/<int:quote_id>/accept', methods=['PUT'])
@jwt_required()
@role_required('buyer')
def accept_quote(demand_id, quote_id):
    """Accept a quote on a demand, creating an order and conversation.

    Only the buyer who owns the demand can accept a quote. The demand
    must be in "open" status and the quote must belong to the demand.
    """
    buyer_id = int(get_jwt_identity())
    demand = db.session.get(Demand, demand_id)
    if demand is None:
        return jsonify({'code': 404, 'message': '\u9700\u6c42\u4e0d\u5b58\u5728'}), 404
    if demand.buyer_id != buyer_id:
        return jsonify({'code': 403, 'message': '\u65e0\u6743\u64cd\u4f5c\u6b64\u62a5\u4ef7'}), 403
    if demand.status != 'open':
        return jsonify({'code': 400, 'message': '\u8be5\u9700\u6c42\u5df2\u5173\u95ed\uff0c\u65e0\u6cd5\u63a5\u53d7\u62a5\u4ef7'}), 400
    quote = db.session.get(Quote, quote_id)
    if quote is None or quote.demand_id != demand_id:
        return jsonify({'code': 404, 'message': '\u62a5\u4ef7\u4e0d\u5b58\u5728'}), 404
    # Accept the quote, reject all others, close the demand
    quote.status = 'accepted'
    other_quotes = Quote.query.filter(
        Quote.demand_id == demand_id, Quote.id != quote_id,
    ).all()
    for other in other_quotes:
        other.status = 'rejected'
    demand.status = 'closed'
    # Calculate total amount
    quantity = demand.quantity if demand.quantity is not None else 1
    total_amount = quote.price * quantity
    buyer = db.session.get(User, buyer_id)
    address = buyer.address if buyer and buyer.address else ''
    order = Order(
        buyer_id=buyer_id, supplier_id=quote.supplier_id,
        order_no=generate_order_no(), total_amount=total_amount,
        address=address, status='pending',
        demand_id=demand_id, quote_id=quote_id,
    )
    db.session.add(order)
    db.session.commit()
    conversation = _get_or_create_conversation(
        demand_id=demand_id, buyer_id=buyer_id, supplier_id=quote.supplier_id,
    )
    delivery_info = f'\uff0c\u4ea4\u8d27 {quote.delivery_days} \u5929' if quote.delivery_days else ''
    system_content = (
        f'\u62a5\u4ef7\u5df2\u88ab\u63a5\u53d7\uff1a\xA5{quote.price}/\u7c73{delivery_info}\uff0c'
        f'\u8ba2\u5355\u5df2\u521b\u5efa\uff08\u8ba2\u5355\u53f7\uff1a{order.order_no}\uff09'
    )
    _add_system_message(conversation, buyer_id, system_content)
    send_notification(
        user_id=quote.supplier_id, notification_type='order',
        title='\u62a5\u4ef7\u5df2\u88ab\u63a5\u53d7',
        content=(
            f'\u60a8\u5bf9\u9700\u6c42\u300c{demand.title}\u300d\u7684\u62a5\u4ef7\u5df2\u88ab\u63a5\u53d7\uff0c'
            f'\u8ba2\u5355\u5df2\u521b\u5efa\uff08\u8ba2\u5355\u53f7\uff1a{order.order_no}\uff09'
        ),
        ref_id=order.id, ref_type='order',
    )
    return jsonify({
        'order': order.to_dict(),
        'conversation_id': conversation.id,
    }), 200
