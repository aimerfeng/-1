"""Seed test users into the dev database.

Run: python seed_users.py
"""
import os
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")
os.makedirs(_INSTANCE_DIR, exist_ok=True)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_INSTANCE_DIR, "dev.db"))

from server.app import create_app
from server.extensions import db
from server.models.user import User

app = create_app("development")

with app.app_context():
    accounts = [
        {"phone": "13800000001", "role": "admin",    "password": "admin123",    "company_name": "平台管理中心", "contact_name": "系统管理员", "certification_status": "approved"},
        {"phone": "13800000010", "role": "buyer",    "password": "buyer123",    "company_name": "杭州锦绣服饰有限公司", "contact_name": "张明", "certification_status": "approved"},
        {"phone": "13800000020", "role": "supplier", "password": "supplier123", "company_name": "绍兴柯桥恒丰纺织有限公司", "contact_name": "王建国", "certification_status": "approved"},
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
    print("  管理员  13800000001 / admin123")
    print("  采购方  13800000010 / buyer123")
    print("  供应商  13800000020 / supplier123")
