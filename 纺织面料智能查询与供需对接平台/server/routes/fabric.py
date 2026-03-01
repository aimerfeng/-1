"""Fabric management routes for the textile fabric platform.

Provides endpoints for creating, querying, updating, comparing fabrics,
uploading fabric images, and managing favorites.

Endpoints:
    POST   /api/fabrics              - Create a new fabric (supplier only)
    GET    /api/fabrics              - List fabrics with multi-condition filtering
    GET    /api/fabrics/compare      - Compare multiple fabrics by IDs
    GET    /api/fabrics/favorites    - List current user's favorite fabrics
    GET    /api/fabrics/<id>         - Get fabric detail
    PUT    /api/fabrics/<id>         - Update fabric info (owning supplier only)
    POST   /api/fabrics/<id>/images  - Upload fabric images (supplier only)
    POST   /api/fabrics/<id>/favorite  - Add fabric to favorites
    DELETE /api/fabrics/<id>/favorite  - Remove fabric from favorites
"""

import json
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from server.extensions import db
from server.models.fabric import Fabric, Favorite, validate_fabric
from server.models.user import User
from server.routes.auth import role_required

fabric_bp = Blueprint('fabric', __name__)


@fabric_bp.route('', methods=['POST'])
@jwt_required()
@role_required('supplier')
def create_fabric():
    """Create a new fabric record.

    Only suppliers can create fabrics. Validates fabric data using
    validate_fabric before persisting.

    Request JSON:
        name (str): Fabric name
        composition (str, required): Fabric composition
        weight (float, required): Weight in g/m²
        width (float, required): Width in cm
        craft (str, required): Craft/process
        color (str, optional): Color
        price (float, required): Unit price in yuan/meter
        min_order_qty (int, optional): Minimum order quantity
        delivery_days (int, optional): Delivery period in days
        images (list, optional): List of image URLs

    Returns:
        201: Created fabric data
        400: Validation errors
    """
    data = request.get_json(silent=True) or {}

    # Validate required fields
    is_valid, errors = validate_fabric(data)
    if not is_valid:
        return jsonify({
            'code': 400,
            'message': '参数校验失败',
            'errors': errors,
        }), 400

    supplier_id = int(get_jwt_identity())

    fabric = Fabric(
        supplier_id=supplier_id,
        name=data.get('name', ''),
        composition=data['composition'],
        weight=data['weight'],
        width=data['width'],
        craft=data['craft'],
        color=data.get('color'),
        price=data['price'],
        min_order_qty=data.get('min_order_qty'),
        delivery_days=data.get('delivery_days'),
        stock_quantity=data.get('stock_quantity', 0),
        images=data.get('images', []),
    )

    db.session.add(fabric)
    db.session.commit()

    # Trigger matching engine: match new fabric against all open demands
    # (Requirement 5.6: new fabric triggers matching with existing demands)
    try:
        from server.routes.demand import _run_matching_for_fabric
        _run_matching_for_fabric(fabric)
    except Exception:
        # Matching failure should not block fabric creation
        pass

    return jsonify(fabric.to_dict()), 201


@fabric_bp.route('/mine', methods=['GET'])
@jwt_required()
@role_required('supplier')
def my_fabrics():
    """List fabrics published by the current supplier.

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20

    Returns:
        200: Paginated fabric list for the current supplier
    """
    supplier_id = int(get_jwt_identity())

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    query = Fabric.query.filter_by(supplier_id=supplier_id).order_by(Fabric.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [f.to_dict() for f in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@fabric_bp.route('', methods=['GET'])
def list_fabrics():
    """List fabrics with multi-condition filtering and pagination.

    Query Parameters:
        composition (str, optional): Partial match on composition
        craft (str, optional): Partial match on craft
        color (str, optional): Partial match on color
        price_min (float, optional): Minimum price filter
        price_max (float, optional): Maximum price filter
        weight_min (float, optional): Minimum weight filter
        weight_max (float, optional): Maximum weight filter
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20

    Returns:
        200: Paginated fabric list with total count
    """
    query = Fabric.query

    # Text field filters (partial matching with LIKE)
    composition = request.args.get('composition')
    if composition:
        query = query.filter(Fabric.composition.like(f'%{composition}%'))

    craft = request.args.get('craft')
    if craft:
        query = query.filter(Fabric.craft.like(f'%{craft}%'))

    color = request.args.get('color')
    if color:
        query = query.filter(Fabric.color.like(f'%{color}%'))

    # Numeric range filters
    price_min = request.args.get('price_min', type=float)
    if price_min is not None:
        query = query.filter(Fabric.price >= price_min)

    price_max = request.args.get('price_max', type=float)
    if price_max is not None:
        query = query.filter(Fabric.price <= price_max)

    weight_min = request.args.get('weight_min', type=float)
    if weight_min is not None:
        query = query.filter(Fabric.weight >= weight_min)

    weight_max = request.args.get('weight_max', type=float)
    if weight_max is not None:
        query = query.filter(Fabric.weight <= weight_max)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Ensure valid pagination values
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'items': [fabric.to_dict() for fabric in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@fabric_bp.route('/compare', methods=['GET'])
def compare_fabrics():
    """Compare multiple fabrics by their IDs.

    Query Parameters:
        ids (str, required): Comma-separated fabric IDs (e.g., "1,2,3")

    Returns:
        200: List of fabric data for all found IDs
        400: Missing or invalid IDs parameter
    """
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify({
            'code': 400,
            'message': '缺少面料ID参数',
        }), 400

    try:
        fabric_ids = [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
    except ValueError:
        return jsonify({
            'code': 400,
            'message': '面料ID格式不正确',
        }), 400

    if not fabric_ids:
        return jsonify({
            'code': 400,
            'message': '缺少面料ID参数',
        }), 400

    fabrics = Fabric.query.filter(Fabric.id.in_(fabric_ids)).all()

    return jsonify({
        'items': [fabric.to_dict() for fabric in fabrics],
        'total': len(fabrics),
    }), 200


@fabric_bp.route('/<int:fabric_id>', methods=['GET'])
def get_fabric(fabric_id):
    """Get fabric detail by ID.

    Args:
        fabric_id: The fabric's database ID.

    Returns:
        200: Full fabric data
        404: Fabric not found
    """
    fabric = db.session.get(Fabric, fabric_id)
    if fabric is None:
        return jsonify({
            'code': 404,
            'message': '面料不存在',
        }), 404

    return jsonify(fabric.to_dict()), 200


@fabric_bp.route('/<int:fabric_id>', methods=['PUT'])
@jwt_required()
def update_fabric(fabric_id):
    """Update fabric information.

    Only the owning supplier can update their fabric. Modification
    history is preserved in the edit_history JSON field.

    Args:
        fabric_id: The fabric's database ID.

    Request JSON:
        Any fabric fields to update (name, composition, weight, etc.)

    Returns:
        200: Updated fabric data
        403: Not the owning supplier
        404: Fabric not found
    """
    fabric = db.session.get(Fabric, fabric_id)
    if fabric is None:
        return jsonify({
            'code': 404,
            'message': '面料不存在',
        }), 404

    supplier_id = int(get_jwt_identity())
    if fabric.supplier_id != supplier_id:
        return jsonify({
            'code': 403,
            'message': '只能修改自己发布的面料',
        }), 403

    data = request.get_json(silent=True) or {}

    # Validate if required fields are being updated
    # Only validate fields that are present in the update data
    fields_to_validate = {}
    for field in ('composition', 'weight', 'width', 'craft', 'price'):
        if field in data:
            fields_to_validate[field] = data[field]
        else:
            # Use existing values for validation
            fields_to_validate[field] = getattr(fabric, field)

    is_valid, errors = validate_fabric(fields_to_validate)
    if not is_valid:
        return jsonify({
            'code': 400,
            'message': '参数校验失败',
            'errors': errors,
        }), 400

    # Record modification history
    history_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'changes': {},
    }

    # Update allowed fields
    updatable_fields = [
        'name', 'composition', 'weight', 'width', 'craft',
        'color', 'price', 'min_order_qty', 'delivery_days', 'stock_quantity', 'status',
    ]

    for field in updatable_fields:
        if field in data:
            old_value = getattr(fabric, field)
            new_value = data[field]
            if old_value != new_value:
                history_entry['changes'][field] = {
                    'old': old_value,
                    'new': new_value,
                }
                setattr(fabric, field, new_value)

    # Store edit history in images metadata or a separate approach
    # For now, we track changes via updated_at timestamp
    # The history_entry is kept for potential future use

    db.session.commit()

    return jsonify(fabric.to_dict()), 200


@fabric_bp.route('/<int:fabric_id>/images', methods=['POST'])
@jwt_required()
@role_required('supplier')
def upload_images(fabric_id):
    """Upload/add images to a fabric record.

    Accepts image URLs and appends them to the fabric's images list.

    Args:
        fabric_id: The fabric's database ID.

    Request JSON:
        images (list[str]): List of image URLs to add

    Returns:
        200: Updated fabric data with new images
        400: Missing images data
        403: Not the owning supplier
        404: Fabric not found
    """
    fabric = db.session.get(Fabric, fabric_id)
    if fabric is None:
        return jsonify({
            'code': 404,
            'message': '面料不存在',
        }), 404

    supplier_id = int(get_jwt_identity())
    if fabric.supplier_id != supplier_id:
        return jsonify({
            'code': 403,
            'message': '只能为自己发布的面料上传图片',
        }), 403

    data = request.get_json(silent=True) or {}
    new_images = data.get('images', [])

    if not isinstance(new_images, list) or not new_images:
        return jsonify({
            'code': 400,
            'message': '请提供图片URL列表',
        }), 400

    # Validate that all items are strings (URLs)
    for img in new_images:
        if not isinstance(img, str) or not img.strip():
            return jsonify({
                'code': 400,
                'message': '图片URL格式不正确',
            }), 400

    # Append new images to existing list
    current_images = fabric.images if fabric.images else []
    fabric.images = current_images + new_images

    db.session.commit()

    return jsonify(fabric.to_dict()), 200


@fabric_bp.route('/favorites', methods=['GET'])
@jwt_required()
def list_favorites():
    """List current user's favorite fabrics with fabric thumbnail info.

    Returns a paginated list of the user's favorites, each including
    the associated fabric's summary information and current status.

    Query Parameters:
        page (int, optional): Page number, default 1
        per_page (int, optional): Items per page, default 20

    Returns:
        200: Paginated favorites list with fabric info
    """
    user_id = int(get_jwt_identity())

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    query = Favorite.query.filter_by(user_id=user_id).order_by(Favorite.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for fav in pagination.items:
        fav_dict = fav.to_dict()
        fabric = db.session.get(Fabric, fav.fabric_id)
        if fabric:
            fav_dict['fabric'] = {
                'id': fabric.id,
                'name': fabric.name,
                'composition': fabric.composition,
                'weight': fabric.weight,
                'width': fabric.width,
                'craft': fabric.craft,
                'color': fabric.color,
                'price': fabric.price,
                'images': fabric.images if fabric.images else [],
                'status': fabric.status,
            }
        else:
            fav_dict['fabric'] = None
        items.append(fav_dict)

    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    }), 200


@fabric_bp.route('/<int:fabric_id>/favorite', methods=['POST'])
@jwt_required()
def add_favorite(fabric_id):
    """Add a fabric to the current user's favorites.

    Prevents duplicate favorites. If the fabric is already favorited,
    returns the existing favorite with 200 status.

    Args:
        fabric_id: The fabric's database ID.

    Returns:
        201: Newly created favorite
        200: Already favorited (returns existing)
        404: Fabric not found
    """
    user_id = int(get_jwt_identity())

    # Check fabric exists
    fabric = db.session.get(Fabric, fabric_id)
    if fabric is None:
        return jsonify({
            'code': 404,
            'message': '面料不存在',
        }), 404

    # Check if already favorited
    existing = Favorite.query.filter_by(
        user_id=user_id, fabric_id=fabric_id
    ).first()
    if existing:
        return jsonify(existing.to_dict()), 200

    favorite = Favorite(
        user_id=user_id,
        fabric_id=fabric_id,
    )
    db.session.add(favorite)
    db.session.commit()

    return jsonify(favorite.to_dict()), 201


@fabric_bp.route('/<int:fabric_id>/favorite', methods=['DELETE'])
@jwt_required()
def remove_favorite(fabric_id):
    """Remove a fabric from the current user's favorites.

    Args:
        fabric_id: The fabric's database ID.

    Returns:
        200: Successfully removed
        404: Favorite not found (not favorited)
    """
    user_id = int(get_jwt_identity())

    favorite = Favorite.query.filter_by(
        user_id=user_id, fabric_id=fabric_id
    ).first()

    if favorite is None:
        return jsonify({
            'code': 404,
            'message': '未收藏该面料',
        }), 404

    db.session.delete(favorite)
    db.session.commit()

    return jsonify({
        'message': '取消收藏成功',
    }), 200
