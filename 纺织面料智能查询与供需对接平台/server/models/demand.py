"""Demand and MatchResult data models.

Defines the Demand model for buyer purchase requirements and the
MatchResult model for storing supply-demand matching results with
scoring details.
"""

from datetime import datetime

from server.extensions import db


class Demand(db.Model):
    """Demand model for buyer purchase requirements.

    Represents a purchase demand published by a buyer, specifying
    desired fabric parameters such as composition, weight range,
    width range, craft, color, price range, and quantity.
    Status can be open, matched, or closed.
    """

    __tablename__ = 'demands'

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    composition = db.Column(db.String(200), nullable=True)
    weight_min = db.Column(db.Float, nullable=True)
    weight_max = db.Column(db.Float, nullable=True)
    width_min = db.Column(db.Float, nullable=True)
    width_max = db.Column(db.Float, nullable=True)
    craft = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(100), nullable=True)
    price_min = db.Column(db.Float, nullable=True)
    price_max = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.Enum('open', 'matched', 'closed', name='demand_status', validate_strings=True),
        default='open',
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    buyer = db.relationship('User', backref=db.backref('demands', lazy='dynamic'))
    match_results = db.relationship(
        'MatchResult', backref='demand', lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def to_dict(self):
        """Serialize the demand to a dictionary for JSON responses.

        Returns:
            Dictionary containing all demand fields.
        """
        return {
            'id': self.id,
            'buyer_id': self.buyer_id,
            'title': self.title,
            'composition': self.composition,
            'weight_min': self.weight_min,
            'weight_max': self.weight_max,
            'width_min': self.width_min,
            'width_max': self.width_max,
            'craft': self.craft,
            'color': self.color,
            'price_min': self.price_min,
            'price_max': self.price_max,
            'quantity': self.quantity,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Demand {self.id} ({self.title})>'


class MatchResult(db.Model):
    """MatchResult model for supply-demand matching results.

    Stores the matching score between a demand and a fabric,
    along with detailed scoring breakdown per dimension.
    Score ranges from 0 to 100.
    """

    __tablename__ = 'match_results'

    id = db.Column(db.Integer, primary_key=True)
    demand_id = db.Column(db.Integer, db.ForeignKey('demands.id'), nullable=False)
    fabric_id = db.Column(db.Integer, db.ForeignKey('fabrics.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # 匹配度评分 0-100
    score_detail = db.Column(db.JSON, default=dict)  # 各维度得分明细
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    fabric = db.relationship('Fabric', backref=db.backref('match_results', lazy='dynamic'))

    def to_dict(self):
        """Serialize the match result to a dictionary for JSON responses.

        Returns:
            Dictionary containing all match result fields.
        """
        return {
            'id': self.id,
            'demand_id': self.demand_id,
            'fabric_id': self.fabric_id,
            'score': self.score,
            'score_detail': self.score_detail if self.score_detail is not None else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<MatchResult {self.id} (demand={self.demand_id}, fabric={self.fabric_id}, score={self.score})>'


class Quote(db.Model):
    """Quote model for supplier responses to buyer demands.

    A supplier can submit a quote for a demand, including price,
    delivery time, and a message to the buyer.
    """

    __tablename__ = 'quotes'

    id = db.Column(db.Integer, primary_key=True)
    demand_id = db.Column(db.Integer, db.ForeignKey('demands.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)  # 报价（元/米）
    delivery_days = db.Column(db.Integer, nullable=True)  # 交货天数
    message = db.Column(db.Text, nullable=True)  # 报价说明
    status = db.Column(
        db.Enum('pending', 'accepted', 'rejected', name='quote_status', validate_strings=True),
        default='pending',
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    demand = db.relationship('Demand', backref=db.backref('quotes', lazy='dynamic'))
    supplier = db.relationship('User', backref=db.backref('quotes', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'demand_id': self.demand_id,
            'supplier_id': self.supplier_id,
            'price': self.price,
            'delivery_days': self.delivery_days,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Quote {self.id} (demand={self.demand_id}, supplier={self.supplier_id})>'
