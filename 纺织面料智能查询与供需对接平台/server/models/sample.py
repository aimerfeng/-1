"""Sample data model.

Defines the Sample model for managing fabric sample requests
between buyers and suppliers, including logistics tracking
and review workflow.
"""

from datetime import datetime

from server.extensions import db


class Sample(db.Model):
    """Sample model for fabric sample request management.

    Represents a sample request from a buyer to a supplier for a specific
    fabric. Tracks the full lifecycle from request creation through
    supplier review, shipping, and receipt.

    Status flow: pending → approved/rejected → shipping → received
    """

    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True)
    fabric_id = db.Column(db.Integer, db.ForeignKey('fabrics.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(
            'pending', 'approved', 'rejected', 'shipping', 'received',
            name='sample_status',
            validate_strings=True,
        ),
        default='pending',
        nullable=False,
    )
    logistics_no = db.Column(db.String(100), nullable=True)
    logistics_info = db.Column(db.JSON, nullable=True)
    reject_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    fabric = db.relationship('Fabric', backref=db.backref('samples', lazy='dynamic'))
    buyer = db.relationship(
        'User',
        foreign_keys=[buyer_id],
        backref=db.backref('sample_requests', lazy='dynamic'),
    )
    supplier = db.relationship(
        'User',
        foreign_keys=[supplier_id],
        backref=db.backref('sample_reviews', lazy='dynamic'),
    )

    def to_dict(self):
        """Serialize the sample to a dictionary for JSON responses.

        Returns:
            Dictionary containing all sample fields.
        """
        return {
            'id': self.id,
            'fabric_id': self.fabric_id,
            'buyer_id': self.buyer_id,
            'supplier_id': self.supplier_id,
            'quantity': self.quantity,
            'address': self.address,
            'status': self.status,
            'logistics_no': self.logistics_no,
            'logistics_info': self.logistics_info,
            'reject_reason': self.reject_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Sample {self.id} (fabric={self.fabric_id}, status={self.status})>'
