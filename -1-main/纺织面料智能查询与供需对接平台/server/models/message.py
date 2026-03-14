"""Message data model.

Defines the Message model for the notification system,
supporting different message types (match, logistics, review,
order, system) with read status tracking and business entity references.
"""

from datetime import datetime

from server.extensions import db


class Message(db.Model):
    """Message model for the textile fabric platform notification system.

    Represents a notification message sent to a user, with support for
    different message types and references to related business entities.

    Message types:
    - match: Supply-demand matching notifications
    - logistics: Logistics status update notifications
    - review: Review/audit result notifications
    - order: Order status change notifications
    - quote: Supplier quote notifications
    - system: System-level notifications
    """

    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(
        db.Enum(
            'match', 'logistics', 'review', 'order', 'quote', 'system',
            name='message_type',
            validate_strings=True,
        ),
        nullable=False,
    )
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    ref_id = db.Column(db.Integer, nullable=True)
    ref_type = db.Column(db.String(50), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('messages', lazy='dynamic'))

    def to_dict(self):
        """Serialize the message to a dictionary for JSON responses.

        Returns:
            Dictionary containing all message fields.
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'ref_id': self.ref_id,
            'ref_type': self.ref_type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Message {self.id} (type={self.type}, user={self.user_id})>'
