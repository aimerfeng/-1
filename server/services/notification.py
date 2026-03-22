"""Notification service for the textile fabric platform.

Provides functions to create notification messages in the database
for various business events: matching results, logistics updates,
review outcomes, and order status changes.

Requirements: 8.1, 8.2, 8.3
"""

import logging

from server.extensions import db
from server.models.message import Message

logger = logging.getLogger(__name__)


def send_notification(user_id, notification_type, title, content, ref_id=None, ref_type=None):
    """Send a notification to a user by creating a Message record.

    Creates a Message record in the database and commits it.
    Falls back to logging only if called outside an application context.

    Args:
        user_id: The ID of the user to notify.
        notification_type: Type of notification (match/logistics/review/order/system).
        title: Notification title.
        content: Notification content text.
        ref_id: Optional ID of the related business entity.
        ref_type: Optional type of the related business entity.

    Returns:
        The created Message object, or True if falling back to logging only.
    """
    # Always log the notification for debugging
    logger.info(
        "Notification [%s] to user %s: %s - %s (ref: %s/%s)",
        notification_type,
        user_id,
        title,
        content,
        ref_type,
        ref_id,
    )

    try:
        message = Message(
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            ref_id=ref_id,
            ref_type=ref_type,
            is_read=False,
        )
        db.session.add(message)
        db.session.commit()
        logger.debug("Created message record id=%s for user %s", message.id, user_id)
        return message
    except RuntimeError:
        # Called outside an application context – fall back to logging only
        logger.warning(
            "No app context available; notification logged but not persisted "
            "(user_id=%s, type=%s)",
            user_id,
            notification_type,
        )
        return True


def create_notification(user_id, type, title, content, ref_id=None, ref_type=None):
    """Create a notification message record.

    This is an alias for send_notification, provided for API consistency
    with the task specification.

    Args:
        user_id: The ID of the user to notify.
        type: Type of notification (match/logistics/review/order/system).
        title: Notification title.
        content: Notification content text.
        ref_id: Optional ID of the related business entity.
        ref_type: Optional type of the related business entity.

    Returns:
        The created Message object, or True if falling back to logging only.
    """
    return send_notification(
        user_id=user_id,
        notification_type=type,
        title=title,
        content=content,
        ref_id=ref_id,
        ref_type=ref_type,
    )
