"""Flask extensions initialization module.

Extensions are initialized here without binding to a specific app instance.
They are later bound to the app in the application factory (app.py).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()
