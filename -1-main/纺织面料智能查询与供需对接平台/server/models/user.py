"""User data model.

Defines the User model with role-based access control and
password hashing for secure authentication.
"""

from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from server.extensions import db


class User(db.Model):
    """User model for the textile fabric platform.

    Supports three roles: buyer, supplier, and admin.
    Includes certification status tracking and password hashing.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(128), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(
        db.Enum('buyer', 'supplier', 'admin', name='user_role', validate_strings=True),
        nullable=False
    )
    company_name = db.Column(db.String(200), nullable=True)
    contact_name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    certification_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name='certification_status'),
        default='pending',
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def set_password(self, password):
        """Hash and store the user's password.

        Args:
            password: The plaintext password to hash and store.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a plaintext password against the stored hash.

        Args:
            password: The plaintext password to verify.

        Returns:
            True if the password matches, False otherwise.
        """
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize the user to a dictionary for JSON responses.

        Returns:
            Dictionary containing user fields (excludes password_hash).
        """
        return {
            'id': self.id,
            'openid': self.openid,
            'phone': self.phone,
            'role': self.role,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'address': self.address,
            'avatar': self.avatar,
            'certification_status': self.certification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<User {self.id} ({self.role})>'
