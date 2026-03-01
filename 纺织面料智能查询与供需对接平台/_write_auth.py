#!/usr/bin/env python3
"""Helper script to write auth.py."""
import os

content = r'''"""Authentication routes for the textile fabric platform.

Provides endpoints for WeChat login, phone registration, phone/password login,
and decorators for role-based and certification-based access control.

Endpoints:
    POST /api/auth/wx-login   - WeChat authorization login
    POST /api/auth/register   - Phone + verification code registration
    POST /api/auth/login      - Phone + password login
"""

import re
from functools import wraps

import requests as http_requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from server.extensions import db
from server.models.user import User


def validate_phone(phone: str) -> bool:
    """Validate a Chinese mainland mobile phone number.

    Rules: starts with 1, second digit 3-9, total 11 digits.
    """
    if not isinstance(phone, str):
        return False
    return bool(re.fullmatch(r'1[3-9]\d{9}', phone))


def role_required(roles):
    """Restrict access to users with specific roles.

    Use after @jwt_required().
    """
    if isinstance(roles, str):
        roles = [roles]

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)
            if user is None:
                return jsonify({'code': 401, 'message': '\u7528\u6237\u4e0d\u5b58\u5728'}), 401
            if user.role not in roles:
                return jsonify({'code': 403, 'message': '\u6743\u9650\u4e0d\u8db3'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def certification_required(fn):
    """Restrict access to users with approved certification.

    Use after @jwt_required(). Returns 403 if certification_status != approved.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if user is None:
            return jsonify({'code': 401, 'message': '\u7528\u6237\u4e0d\u5b58\u5728'}), 401
        if user.certification_status != 'approved':
            return jsonify({
                'code': 403,
                'message': '\u8bf7\u5148\u5b8c\u6210\u8d44\u8d28\u8ba4\u8bc1',
            }), 403
        return fn(*args, **kwargs)
    return wrapper


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/wx-login', methods=['POST'])
def wx_login():
    """WeChat mini-program login."""
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    if not code:
        return jsonify({'code': 400, 'message': '\u7f3a\u5c11\u5fae\u4fe1\u767b\u5f55code'}), 400

    appid = current_app.config.get('WX_APPID', '')
    secret = current_app.config.get('WX_SECRET', '')
    wx_url = (
        'https://api.weixin.qq.com/sns/jscode2session'
        f'?appid={appid}&secret={secret}&js_code={code}'
        '&grant_type=authorization_code'
    )

    try:
        resp = http_requests.get(wx_url, timeout=10)
        wx_data = resp.json()
    except Exception:
        return jsonify({'code': 500, 'message': '\u5fae\u4fe1\u63a5\u53e3\u8c03\u7528\u5931\u8d25'}), 500

    openid = wx_data.get('openid')
    if not openid:
        err_msg = wx_data.get('errmsg', '\u672a\u77e5\u9519\u8bef')
        return jsonify({'code': 400, 'message': f'\u5fae\u4fe1\u767b\u5f55\u5931\u8d25: {err_msg}'}), 400

    user = User.query.filter_by(openid=openid).first()
    is_new = user is None
    if is_new:
        user = User(openid=openid, role='buyer')
        db.session.add(user)
        db.session.commit()

    token = create_access_token(identity=user.id)
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'is_new': is_new,
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register with phone + verification code."""
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '')
    sms_code = data.get('code', '')
    password = data.get('password', '')
    role = data.get('role', 'buyer')

    if not validate_phone(phone):
        return jsonify({'code': 400, 'message': '\u624b\u673a\u53f7\u683c\u5f0f\u4e0d\u6b63\u786e'}), 400
    if not sms_code:
        return jsonify({'code': 400, 'message': '\u7f3a\u5c11\u9a8c\u8bc1\u7801'}), 400
    if not password:
        return jsonify({'code': 400, 'message': '\u7f3a\u5c11\u5bc6\u7801'}), 400
    if role not in ('buyer', 'supplier'):
        return jsonify({'code': 400, 'message': '\u89d2\u8272\u5fc5\u987b\u4e3a buyer \u6216 supplier'}), 400

    existing = User.query.filter_by(phone=phone).first()
    if existing:
        return jsonify({'code': 400, 'message': '\u8be5\u624b\u673a\u53f7\u5df2\u6ce8\u518c'}), 400

    user = User(phone=phone, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=user.id)
    return jsonify({
        'token': token,
        'user': user.to_dict(),
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with phone + password."""
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '')
    password = data.get('password', '')

    if not phone:
        return jsonify({'code': 400, 'message': '\u7f3a\u5c11\u624b\u673a\u53f7'}), 400
    if not password:
        return jsonify({'code': 400, 'message': '\u7f3a\u5c11\u5bc6\u7801'}), 400

    user = User.query.filter_by(phone=phone).first()
    if user is None:
        return jsonify({'code': 401, 'message': '\u624b\u673a\u53f7\u672a\u6ce8\u518c'}), 401

    if not user.check_password(password):
        return jsonify({'code': 401, 'message': '\u5bc6\u7801\u9519\u8bef'}), 401

    token = create_access_token(identity=user.id)
    return jsonify({
        'token': token,
        'user': user.to_dict(),
    }), 200
'''

path = os.path.join('server', 'routes', 'auth.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Written {os.path.getsize(path)} bytes to {path}")
