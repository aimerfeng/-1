"""Fabric and Favorite data models.

Defines the Fabric model for textile fabric information management,
including standardized parameter validation for composition, weight,
width, craft, and price fields. Also defines the Favorite model for
user fabric bookmarks.
"""

from datetime import datetime

from server.extensions import db


class Fabric(db.Model):
    """Fabric model for the textile fabric platform.

    Represents a fabric product published by a supplier, with standardized
    parameters including composition, weight, width, craft, color, and price.
    Status can be active or inactive.
    """

    __tablename__ = 'fabrics'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    composition = db.Column(db.String(200), nullable=False)
    weight = db.Column(db.Float, nullable=False)        # 克重 g/m²
    width = db.Column(db.Float, nullable=False)          # 幅宽 cm
    craft = db.Column(db.String(100), nullable=False)    # 工艺
    color = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=False)          # 单价 元/米
    min_order_qty = db.Column(db.Integer, nullable=True)
    delivery_days = db.Column(db.Integer, nullable=True)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)  # 库存量（米）
    images = db.Column(db.JSON, default=list)
    status = db.Column(
        db.Enum('active', 'inactive', name='fabric_status', validate_strings=True),
        default='active',
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    supplier = db.relationship('User', backref=db.backref('fabrics', lazy='dynamic'))

    def to_dict(self):
        """Serialize the fabric to a dictionary for JSON responses.

        Returns:
            Dictionary containing all fabric fields.
        """
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'name': self.name,
            'composition': self.composition,
            'weight': self.weight,
            'width': self.width,
            'craft': self.craft,
            'color': self.color,
            'price': self.price,
            'min_order_qty': self.min_order_qty,
            'delivery_days': self.delivery_days,
            'stock_quantity': self.stock_quantity,
            'images': self.images if self.images is not None else [],
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Fabric {self.id} ({self.name})>'


class Favorite(db.Model):
    """Favorite model for user fabric bookmarks.

    Represents a user's favorite/bookmarked fabric. Each user can only
    favorite a fabric once (enforced by unique constraint on user_id + fabric_id).
    """

    __tablename__ = 'favorites'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'fabric_id', name='uq_user_fabric_favorite'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fabric_id = db.Column(db.Integer, db.ForeignKey('fabrics.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic'))
    fabric = db.relationship('Fabric', backref=db.backref('favorites', lazy='dynamic'))

    def to_dict(self):
        """Serialize the favorite to a dictionary for JSON responses.

        Returns:
            Dictionary containing all favorite fields.
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'fabric_id': self.fabric_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Favorite user={self.user_id} fabric={self.fabric_id}>'


def validate_fabric(data: dict) -> tuple:
    """Validate fabric submission data.

    Checks that all required fields are present and have valid formats:
    - composition: must be a non-empty string
    - weight: must be a positive number
    - width: must be a positive number
    - craft: must be a non-empty string
    - price: must be a positive number

    Args:
        data: Dictionary containing fabric field values.

    Returns:
        A tuple of (is_valid, errors) where is_valid is True if all
        validations pass, and errors is a dict mapping field names
        to error messages.
    """
    errors = {}

    # Required string fields
    for field in ('composition', 'craft'):
        value = data.get(field)
        if value is None:
            errors[field] = f'{field}为必填项'
        elif not isinstance(value, str) or not value.strip():
            errors[field] = f'{field}必须为非空字符串'

    # Required positive number fields
    for field in ('weight', 'width', 'price'):
        value = data.get(field)
        if value is None:
            errors[field] = f'{field}为必填项'
        elif not isinstance(value, (int, float)):
            errors[field] = f'{field}必须为数字'
        elif value <= 0:
            errors[field] = f'{field}必须大于0'

    is_valid = len(errors) == 0
    return (is_valid, errors)
