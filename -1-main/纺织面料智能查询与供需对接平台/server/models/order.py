"""Order and OrderItem data models.

Defines the Order and OrderItem models for managing purchase orders
between buyers and suppliers, including order number generation
and status transition validation.
"""

import random
import time
from datetime import datetime

from server.extensions import db


# Valid order statuses in their required transition order
ORDER_STATUSES = ['pending', 'confirmed', 'producing', 'shipped', 'received', 'completed']


def generate_order_no() -> str:
    """Generate a unique order number using timestamp and random digits.

    Format: ORD{timestamp_ms}{random_4_digits}
    Example: ORD17199876543211234

    Returns:
        A unique order number string.
    """
    timestamp = int(time.time() * 1000)
    rand_part = random.randint(1000, 9999)
    return f'ORD{timestamp}{rand_part}'


def validate_status_transition(current: str, next_status: str) -> bool:
    """Validate whether an order status transition is allowed.

    Only sequential transitions are permitted:
    pending → confirmed → producing → shipped → received → completed

    Args:
        current: The current order status.
        next_status: The desired next order status.

    Returns:
        True if the transition is valid, False otherwise.
    """
    if current not in ORDER_STATUSES or next_status not in ORDER_STATUSES:
        return False

    current_index = ORDER_STATUSES.index(current)
    next_index = ORDER_STATUSES.index(next_status)

    return next_index == current_index + 1


class Order(db.Model):
    """Order model for the textile fabric platform.

    Represents a purchase order from a buyer to a supplier.
    Tracks the full lifecycle from creation through completion.

    Status flow: pending → confirmed → producing → shipped → received → completed
    """

    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(
            'pending', 'confirmed', 'producing', 'shipped', 'received', 'completed',
            name='order_status',
            validate_strings=True,
        ),
        default='pending',
        nullable=False,
    )
    demand_id = db.Column(db.Integer, db.ForeignKey('demands.id'), nullable=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=True)
    tracking_no = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    buyer = db.relationship(
        'User',
        foreign_keys=[buyer_id],
        backref=db.backref('buyer_orders', lazy='dynamic'),
    )
    supplier = db.relationship(
        'User',
        foreign_keys=[supplier_id],
        backref=db.backref('supplier_orders', lazy='dynamic'),
    )
    demand = db.relationship('Demand', backref=db.backref('orders', lazy='dynamic'))
    quote = db.relationship('Quote', backref=db.backref('order', uselist=False))
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')

    def to_dict(self):
        """Serialize the order to a dictionary for JSON responses.

        Returns:
            Dictionary containing all order fields.
        """
        return {
            'id': self.id,
            'buyer_id': self.buyer_id,
            'supplier_id': self.supplier_id,
            'order_no': self.order_no,
            'total_amount': self.total_amount,
            'address': self.address,
            'status': self.status,
            'demand_id': self.demand_id,
            'quote_id': self.quote_id,
            'tracking_no': self.tracking_no,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Order {self.id} ({self.order_no}, status={self.status})>'


class OrderItem(db.Model):
    """OrderItem model for individual line items within an order.

    Represents a specific fabric and quantity within a purchase order,
    including unit price and calculated subtotal.
    """

    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    fabric_id = db.Column(db.Integer, db.ForeignKey('fabrics.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    fabric = db.relationship('Fabric', backref=db.backref('order_items', lazy='dynamic'))

    def to_dict(self):
        """Serialize the order item to a dictionary for JSON responses.

        Returns:
            Dictionary containing all order item fields.
        """
        return {
            'id': self.id,
            'order_id': self.order_id,
            'fabric_id': self.fabric_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal,
        }

    def __repr__(self):
        return f'<OrderItem {self.id} (order={self.order_id}, fabric={self.fabric_id})>'
