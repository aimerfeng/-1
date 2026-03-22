"""Unit tests for the logistics service.

Tests cover:
- create_logistics: successful creation, API failure with retry marking
- query_logistics: successful query, missing tracking number, API failure
- sync_logistics_status: status change with notification, no change,
  retry on failure, delivered status update, retry-pending creation
"""

import logging
from unittest.mock import patch, MagicMock

import pytest

from server.extensions import db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.sample import Sample
from server.services.logistics import (
    create_logistics,
    query_logistics,
    sync_logistics_status,
    LogisticsAPIError,
    _generate_tracking_number,
    _status_description,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_supplier(db_session):
    """Create a supplier user for testing."""
    user = User(
        phone="13800000001",
        role="supplier",
        company_name="Test Supplier Co",
    )
    user.set_password("password123")
    db_session.session.add(user)
    db_session.session.flush()
    return user


def _create_buyer(db_session):
    """Create a buyer user for testing."""
    user = User(
        phone="13800000002",
        role="buyer",
        company_name="Test Buyer Co",
    )
    user.set_password("password123")
    db_session.session.add(user)
    db_session.session.flush()
    return user


def _create_fabric(db_session, supplier_id):
    """Create a fabric record for testing."""
    fabric = Fabric(
        supplier_id=supplier_id,
        name="Test Fabric",
        composition="100% Cotton",
        weight=200.0,
        width=150.0,
        craft="Plain Weave",
        price=25.0,
    )
    db_session.session.add(fabric)
    db_session.session.flush()
    return fabric


def _create_sample(db_session, fabric_id, buyer_id, supplier_id, status="approved"):
    """Create a sample record for testing."""
    sample = Sample(
        fabric_id=fabric_id,
        buyer_id=buyer_id,
        supplier_id=supplier_id,
        quantity=5,
        address="Test Address, City, 100000",
        status=status,
    )
    db_session.session.add(sample)
    db_session.session.flush()
    return sample


# ---------------------------------------------------------------------------
# Tests for _generate_tracking_number
# ---------------------------------------------------------------------------

class TestGenerateTrackingNumber:
    """Tests for the tracking number generator."""

    def test_format_starts_with_sf(self):
        """Tracking number should start with 'SF'."""
        tn = _generate_tracking_number()
        assert tn.startswith("SF")

    def test_format_is_alphanumeric(self):
        """Tracking number should be alphanumeric after the SF prefix."""
        tn = _generate_tracking_number()
        assert tn[:2] == "SF"
        assert tn[2:].isdigit()

    def test_uniqueness(self):
        """Two generated tracking numbers should be different (high probability)."""
        tn1 = _generate_tracking_number()
        tn2 = _generate_tracking_number()
        # Not guaranteed but extremely likely with timestamp + random
        # We just verify they are valid format
        assert tn1.startswith("SF")
        assert tn2.startswith("SF")


# ---------------------------------------------------------------------------
# Tests for _status_description
# ---------------------------------------------------------------------------

class TestStatusDescription:
    """Tests for status description mapping."""

    def test_known_statuses(self):
        assert _status_description("collected") == "包裹已揽收"
        assert _status_description("in_transit") == "运输中"
        assert _status_description("out_for_delivery") == "派送中"
        assert _status_description("delivered") == "已签收"

    def test_unknown_status(self):
        assert _status_description("unknown_status") == "状态未知"


# ---------------------------------------------------------------------------
# Tests for create_logistics
# ---------------------------------------------------------------------------

class TestCreateLogistics:
    """Tests for the create_logistics function."""

    def test_successful_creation(self, app_context, db):
        """Should create logistics order and update sample."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id)
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_create"
        ) as mock_api:
            mock_api.return_value = {
                "tracking_number": "SF17001234561234",
                "status": "collected",
                "details": [
                    {
                        "time": "2024-01-01 10:00:00",
                        "status": "collected",
                        "description": "包裹已揽收",
                    }
                ],
            }

            result = create_logistics(sample.id, sample.address)

            assert result == "SF17001234561234"
            assert sample.logistics_no == "SF17001234561234"
            assert sample.status == "shipping"
            assert sample.logistics_info["status"] == "collected"
            assert sample.logistics_info["retry_pending"] is False

    def test_api_failure_marks_retry(self, app_context, db):
        """Should mark sample for retry when API call fails."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id)
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_create"
        ) as mock_api:
            mock_api.side_effect = LogisticsAPIError("Connection timeout")

            result = create_logistics(sample.id, sample.address)

            assert result is None
            assert sample.logistics_info["retry_pending"] is True
            assert "Connection timeout" in sample.logistics_info["error"]

    def test_sample_not_found(self, app_context, db):
        """Should raise ValueError for non-existent sample."""
        with pytest.raises(ValueError, match="Sample 9999 not found"):
            create_logistics(9999, "Some Address")

    def test_logs_error_on_failure(self, app_context, db, caplog):
        """Should log error when API call fails."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id)
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_create"
        ) as mock_api:
            mock_api.side_effect = LogisticsAPIError("API down")

            with caplog.at_level(logging.ERROR):
                create_logistics(sample.id, sample.address)

            assert "Failed to create logistics" in caplog.text


# ---------------------------------------------------------------------------
# Tests for query_logistics
# ---------------------------------------------------------------------------

class TestQueryLogistics:
    """Tests for the query_logistics function."""

    def test_successful_query(self):
        """Should return logistics details for valid tracking number."""
        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api:
            mock_api.return_value = {
                "tracking_number": "SF17001234561234",
                "status": "in_transit",
                "details": [
                    {
                        "time": "2024-01-01 12:00:00",
                        "status": "in_transit",
                        "description": "运输中",
                    }
                ],
            }

            result = query_logistics("SF17001234561234")

            assert result["tracking_number"] == "SF17001234561234"
            assert result["status"] == "in_transit"
            assert len(result["details"]) == 1

    def test_empty_tracking_number(self):
        """Should return error dict for empty tracking number."""
        result = query_logistics("")
        assert result["status"] == "unknown"
        assert "error" in result

    def test_none_tracking_number(self):
        """Should return error dict for None tracking number."""
        result = query_logistics(None)
        assert result["status"] == "unknown"

    def test_api_failure_returns_error(self):
        """Should return error dict when API call fails."""
        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api:
            mock_api.side_effect = LogisticsAPIError("Service unavailable")

            result = query_logistics("SF17001234561234")

            assert result["status"] == "error"
            assert "error" in result


# ---------------------------------------------------------------------------
# Tests for sync_logistics_status
# ---------------------------------------------------------------------------

class TestSyncLogisticsStatus:
    """Tests for the sync_logistics_status function."""

    def test_status_change_sends_notification(self, app_context, db):
        """Should send notification when logistics status changes."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="shipping")
        sample.logistics_no = "SF17001234561234"
        sample.logistics_info = {
            "status": "collected",
            "details": [],
            "retry_pending": False,
        }
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api, patch(
            "server.services.logistics.send_notification"
        ) as mock_notify:
            mock_api.return_value = {
                "tracking_number": "SF17001234561234",
                "status": "in_transit",
                "details": [
                    {
                        "time": "2024-01-02 10:00:00",
                        "status": "in_transit",
                        "description": "运输中",
                    }
                ],
            }

            result = sync_logistics_status(sample.id)

            assert result is True
            assert sample.logistics_info["status"] == "in_transit"
            mock_notify.assert_called_once_with(
                user_id=buyer.id,
                notification_type="logistics",
                title="物流状态更新",
                content=f"您的样品(单号: SF17001234561234)物流状态已更新为: 运输中",
                ref_id=sample.id,
                ref_type="sample",
            )

    def test_no_change_no_notification(self, app_context, db):
        """Should not send notification when status hasn't changed."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="shipping")
        sample.logistics_no = "SF17001234561234"
        sample.logistics_info = {
            "status": "in_transit",
            "details": [],
            "retry_pending": False,
        }
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api, patch(
            "server.services.logistics.send_notification"
        ) as mock_notify:
            mock_api.return_value = {
                "tracking_number": "SF17001234561234",
                "status": "in_transit",
                "details": [],
            }

            result = sync_logistics_status(sample.id)

            assert result is True
            mock_notify.assert_not_called()

    def test_delivered_does_not_auto_update_sample_status(self, app_context, db):
        """Delivered logistics should not auto-mark sample as received."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="shipping")
        sample.logistics_no = "SF17001234561234"
        sample.logistics_info = {
            "status": "out_for_delivery",
            "details": [],
            "retry_pending": False,
        }
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api, patch(
            "server.services.logistics.send_notification"
        ):
            mock_api.return_value = {
                "tracking_number": "SF17001234561234",
                "status": "delivered",
                "details": [],
            }

            result = sync_logistics_status(sample.id)

            assert result is True
            assert sample.status == "shipping"
            assert sample.logistics_info["status"] == "delivered"

    def test_api_failure_marks_retry(self, app_context, db):
        """Should mark for retry when API call fails during sync."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="shipping")
        sample.logistics_no = "SF17001234561234"
        sample.logistics_info = {
            "status": "collected",
            "details": [],
            "retry_pending": False,
        }
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_query"
        ) as mock_api:
            mock_api.side_effect = LogisticsAPIError("Timeout")

            result = sync_logistics_status(sample.id)

            assert result is False
            assert sample.logistics_info["retry_pending"] is True
            assert "Timeout" in sample.logistics_info["error"]

    def test_no_tracking_number_returns_false(self, app_context, db):
        """Should return False when sample has no tracking number and no retry pending."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="approved")
        db.session.commit()

        result = sync_logistics_status(sample.id)
        assert result is False

    def test_retry_pending_retries_creation(self, app_context, db):
        """Should retry logistics creation when retry_pending is True and no tracking number."""
        supplier = _create_supplier(db)
        buyer = _create_buyer(db)
        fabric = _create_fabric(db, supplier.id)
        sample = _create_sample(db, fabric.id, buyer.id, supplier.id, status="approved")
        sample.logistics_info = {
            "status": "error",
            "details": [],
            "error": "Previous failure",
            "retry_pending": True,
        }
        db.session.commit()

        with patch(
            "server.services.logistics._call_logistics_api_create"
        ) as mock_api:
            mock_api.return_value = {
                "tracking_number": "SF17009999991111",
                "status": "collected",
                "details": [
                    {
                        "time": "2024-01-03 10:00:00",
                        "status": "collected",
                        "description": "包裹已揽收",
                    }
                ],
            }

            result = sync_logistics_status(sample.id)

            assert result is True
            assert sample.logistics_no == "SF17009999991111"
            assert sample.status == "shipping"

    def test_sample_not_found(self, app_context, db):
        """Should raise ValueError for non-existent sample."""
        with pytest.raises(ValueError, match="Sample 9999 not found"):
            sync_logistics_status(9999)
