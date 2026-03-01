"""Logistics service for sample shipment tracking.

Provides functions to create logistics orders, query logistics status,
and synchronize logistics status updates. Uses a mock/stub implementation
that simulates third-party logistics API behavior for development.

In production, the mock functions would be replaced with real API calls
via the requests library.
"""

import logging
import random
import time

import requests

from server.extensions import db
from server.models.sample import Sample
from server.services.notification import send_notification

logger = logging.getLogger(__name__)

# --- Mock logistics API configuration ---
# In production, these would point to a real third-party logistics API.
LOGISTICS_API_BASE_URL = "https://api.mock-logistics.example.com"
LOGISTICS_API_KEY = "mock-api-key"
LOGISTICS_API_TIMEOUT = 10  # seconds

# Simulated status progression for mock implementation
_MOCK_STATUS_FLOW = ["collected", "in_transit", "out_for_delivery", "delivered"]


class LogisticsAPIError(Exception):
    """Raised when a logistics API call fails."""

    pass


def _generate_tracking_number():
    """Generate a mock tracking number in SF{timestamp}{random} format.

    Returns:
        A string tracking number like 'SF17001234565678'.
    """
    timestamp_part = str(int(time.time()))
    random_part = str(random.randint(1000, 9999))
    return f"SF{timestamp_part}{random_part}"


def _call_logistics_api_create(address):
    """Call the third-party logistics API to create a shipment (mock).

    In production, this would make a real HTTP POST request via requests.
    The mock implementation generates a fake tracking number.

    Args:
        address: The delivery address string.

    Returns:
        A dict with 'tracking_number' and 'status' keys.

    Raises:
        LogisticsAPIError: If the API call fails.
    """
    try:
        # --- Mock implementation ---
        # In production, this would be:
        # response = requests.post(
        #     f"{LOGISTICS_API_BASE_URL}/shipments",
        #     json={"address": address},
        #     headers={"Authorization": f"Bearer {LOGISTICS_API_KEY}"},
        #     timeout=LOGISTICS_API_TIMEOUT,
        # )
        # response.raise_for_status()
        # return response.json()

        tracking_number = _generate_tracking_number()
        return {
            "tracking_number": tracking_number,
            "status": "collected",
            "details": [
                {
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "collected",
                    "description": "包裹已揽收",
                }
            ],
        }
    except requests.RequestException as e:
        raise LogisticsAPIError(f"Failed to create shipment: {e}") from e


def _call_logistics_api_query(logistics_no):
    """Call the third-party logistics API to query shipment status (mock).

    In production, this would make a real HTTP GET request via requests.
    The mock implementation simulates status progression.

    Args:
        logistics_no: The tracking number to query.

    Returns:
        A dict with 'tracking_number', 'status', and 'details' keys.

    Raises:
        LogisticsAPIError: If the API call fails.
    """
    try:
        # --- Mock implementation ---
        # In production, this would be:
        # response = requests.get(
        #     f"{LOGISTICS_API_BASE_URL}/shipments/{logistics_no}",
        #     headers={"Authorization": f"Bearer {LOGISTICS_API_KEY}"},
        #     timeout=LOGISTICS_API_TIMEOUT,
        # )
        # response.raise_for_status()
        # return response.json()

        # Simulate random status progression
        status = random.choice(_MOCK_STATUS_FLOW)
        details = [
            {
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "description": _status_description(status),
            }
        ]
        return {
            "tracking_number": logistics_no,
            "status": status,
            "details": details,
        }
    except requests.RequestException as e:
        raise LogisticsAPIError(f"Failed to query shipment: {e}") from e


def _status_description(status):
    """Get a human-readable description for a logistics status.

    Args:
        status: The logistics status string.

    Returns:
        A Chinese description string.
    """
    descriptions = {
        "collected": "包裹已揽收",
        "in_transit": "运输中",
        "out_for_delivery": "派送中",
        "delivered": "已签收",
    }
    return descriptions.get(status, "状态未知")


def create_logistics(sample_id, address):
    """Create a logistics order for a sample shipment.

    Calls the third-party logistics API to create a shipment,
    then updates the sample record with the tracking number and
    logistics info. If the API call fails, logs the error and
    marks the sample for retry.

    Args:
        sample_id: The ID of the sample to ship.
        address: The delivery address.

    Returns:
        The tracking number string if successful, None if failed.

    Raises:
        ValueError: If the sample is not found.
    """
    sample = db.session.get(Sample, sample_id)
    if not sample:
        raise ValueError(f"Sample {sample_id} not found")

    try:
        result = _call_logistics_api_create(address)
        tracking_number = result["tracking_number"]

        sample.logistics_no = tracking_number
        sample.logistics_info = {
            "status": result["status"],
            "details": result["details"],
            "retry_pending": False,
        }
        sample.status = "shipping"
        db.session.commit()

        logger.info(
            "Logistics order created for sample %s: %s",
            sample_id,
            tracking_number,
        )
        return tracking_number

    except (LogisticsAPIError, Exception) as e:
        logger.error(
            "Failed to create logistics for sample %s: %s",
            sample_id,
            str(e),
        )
        # Mark for retry
        sample.logistics_info = {
            "status": "error",
            "details": [],
            "error": str(e),
            "retry_pending": True,
        }
        db.session.commit()
        return None


def query_logistics(logistics_no):
    """Query logistics status details for a tracking number.

    Calls the third-party logistics API to get the current status
    and tracking details for a shipment.

    Args:
        logistics_no: The tracking number to query.

    Returns:
        A dict with 'tracking_number', 'status', and 'details' keys
        if successful. Returns an error dict if the API call fails.
    """
    if not logistics_no:
        return {"error": "No tracking number provided", "status": "unknown"}

    try:
        result = _call_logistics_api_query(logistics_no)
        return result
    except LogisticsAPIError as e:
        logger.error("Failed to query logistics %s: %s", logistics_no, str(e))
        return {
            "tracking_number": logistics_no,
            "status": "error",
            "error": str(e),
            "details": [],
        }


def sync_logistics_status(sample_id):
    """Synchronize logistics status for a sample.

    Queries the logistics API for the latest status and updates
    the sample record. If the status has changed, sends a
    notification to the buyer. If the API call fails, marks
    the sample for retry on the next sync.

    Note:
        Logistics sync updates tracking information only. The
        sample status transition shipping -> received is handled
        explicitly by the buyer confirmation endpoint.

    Args:
        sample_id: The ID of the sample to sync.

    Returns:
        True if sync was successful, False otherwise.

    Raises:
        ValueError: If the sample is not found.
    """
    sample = db.session.get(Sample, sample_id)
    if not sample:
        raise ValueError(f"Sample {sample_id} not found")

    # Skip if no tracking number and not pending retry
    if not sample.logistics_no:
        # Check if this is a retry-pending sample that failed logistics creation
        logistics_info = sample.logistics_info or {}
        if logistics_info.get("retry_pending"):
            logger.info(
                "Retrying logistics creation for sample %s",
                sample_id,
            )
            result = create_logistics(sample_id, sample.address)
            return result is not None
        return False

    try:
        result = _call_logistics_api_query(sample.logistics_no)
        new_status = result.get("status")
        old_info = sample.logistics_info or {}
        old_status = old_info.get("status")

        # Update logistics info
        sample.logistics_info = {
            "status": new_status,
            "details": result.get("details", []),
            "retry_pending": False,
        }

        # Check if status changed
        if new_status != old_status:
            logger.info(
                "Logistics status changed for sample %s: %s -> %s",
                sample_id,
                old_status,
                new_status,
            )

            db.session.commit()

            # Send notification about status change
            send_notification(
                user_id=sample.buyer_id,
                notification_type="logistics",
                title="物流状态更新",
                content=f"您的样品(单号: {sample.logistics_no})物流状态已更新为: {_status_description(new_status)}",
                ref_id=sample.id,
                ref_type="sample",
            )
        else:
            db.session.commit()

        return True

    except (LogisticsAPIError, Exception) as e:
        logger.error(
            "Failed to sync logistics for sample %s: %s",
            sample_id,
            str(e),
        )
        # Mark for retry – reassign the whole dict so SQLAlchemy
        # detects the change on the JSON column.
        logistics_info = dict(sample.logistics_info or {})
        logistics_info["retry_pending"] = True
        logistics_info["error"] = str(e)
        sample.logistics_info = logistics_info
        db.session.commit()
        return False
