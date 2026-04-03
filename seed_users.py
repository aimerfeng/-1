"""Seed test users into the dev database.

Run: python seed_users.py
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///instance/dev.db")

from server.app import create_app
from server.extensions import db
from server.models.user import User

app = create_app("development")

with app.app_context():
    accounts = [
        {"phone": "13800000001", "role": "admin",    "password": "admin123",    "company_name": "平台管理", "contact_name": "管理员",  "certification_status": "approved"},
        {"phone": "13800000002", "role": "buyer",    "password": "buyer123",    "company_name": "测试采购公司", "contact_name": "张采购", "certification_status": "approved"},
        {"phone": "13800000003", "role": "supplier", "password": "supplier123", "company_name": "测试供应公司", "contact_name": "李供应", "certification_status": "approved"},
    ]

    for acc in accounts:
        existing = User.query.filter_by(phone=acc["phone"]).first()
        if existing:
            print(f"  已存在: {acc['phone']} ({acc['role']}), 跳过")
            continue
        user = User(
            phone=acc["phone"],
            role=acc["role"],
            company_name=acc["company_name"],
            contact_name=acc["contact_name"],
            certification_status=acc["certification_status"],
        )
        user.set_password(acc["password"])
        db.session.add(user)
        print(f"  创建: {acc['phone']} ({acc['role']})")

    db.session.commit()
    print("\n测试账号就绪！用手机号+密码登录即可。")
