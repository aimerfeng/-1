"""Conversation and ChatMessage data models.

Defines the Conversation model for buyer-supplier chat sessions
linked to demands, and the ChatMessage model for individual messages
within conversations. Supports text and system message types.
"""

from datetime import datetime

from server.extensions import db


class Conversation(db.Model):
    """Conversation model for buyer-supplier chat sessions.

    Represents a chat conversation between a buyer and a supplier
    regarding a specific demand. Each (demand, buyer, supplier) triple
    is unique, ensuring one conversation per demand per pair.
    """

    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    demand_id = db.Column(db.Integer, db.ForeignKey('demands.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_message_at = db.Column(db.DateTime, nullable=True)
    last_message_preview = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'demand_id', 'buyer_id', 'supplier_id',
            name='uq_conversation',
        ),
    )

    demand = db.relationship(
        'Demand',
        backref=db.backref('conversations', lazy='dynamic'),
    )
    buyer = db.relationship(
        'User',
        foreign_keys=[buyer_id],
        backref=db.backref('buyer_conversations', lazy='dynamic'),
    )
    supplier = db.relationship(
        'User',
        foreign_keys=[supplier_id],
        backref=db.backref('supplier_conversations', lazy='dynamic'),
    )
    messages = db.relationship(
        'ChatMessage',
        backref='conversation',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def to_dict(self):
        """Serialize the conversation to a dictionary for JSON responses.

        Returns:
            Dictionary containing all conversation fields.
        """
        return {
            'id': self.id,
            'demand_id': self.demand_id,
            'buyer_id': self.buyer_id,
            'supplier_id': self.supplier_id,
            'last_message_at': (
                self.last_message_at.isoformat() if self.last_message_at else None
            ),
            'last_message_preview': self.last_message_preview,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f'<Conversation {self.id} '
            f'(demand={self.demand_id}, buyer={self.buyer_id}, '
            f'supplier={self.supplier_id})>'
        )


class ChatMessage(db.Model):
    """ChatMessage model for individual messages within a conversation.

    Represents a single chat message sent by a participant in a
    conversation. Supports text messages and system-generated messages.
    Tracks read status per message for unread count calculations.
    """

    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey('conversations.id'), nullable=False,
    )
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(
        db.Enum(
            'text', 'system',
            name='chat_msg_type',
            validate_strings=True,
        ),
        default='text',
        nullable=False,
    )
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship(
        'User',
        backref=db.backref('chat_messages', lazy='dynamic'),
    )

    def to_dict(self):
        """Serialize the chat message to a dictionary for JSON responses.

        Returns:
            Dictionary containing all chat message fields.
        """
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f'<ChatMessage {self.id} '
            f'(conversation={self.conversation_id}, sender={self.sender_id}, '
            f'type={self.msg_type})>'
        )
