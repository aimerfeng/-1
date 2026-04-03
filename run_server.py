"""Local development server launcher.

Uses SQLite so you don't need MySQL installed.
Run: python run_server.py
"""

import os

# Use SQLite for local development (no MySQL needed)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_INSTANCE_DIR = os.path.join(_BASE_DIR, "instance")
os.makedirs(_INSTANCE_DIR, exist_ok=True)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(_INSTANCE_DIR, "dev.db"))

from server.app import create_app

app = create_app("development")

if __name__ == "__main__":
    print("=" * 50)
    print("  纺织面料平台后端服务启动中...")
    print("  地址: http://localhost:5000")
    print("  数据库: SQLite (instance/dev.db)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
