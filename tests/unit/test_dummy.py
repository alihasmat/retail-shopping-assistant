# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for the shopping assistant agent and discount redemption tool."""

from app.agent import (
    DISCOUNT_STORE,
    Gemini,
    redeem_discount,
    LOYALTY_STORE,
    PROCESSED_TRANSACTIONS,
    award_loyalty_points,
    CART_STORE,
    process_cart_checkout,
    update_discount_status,
)


def test_redeem_discount_success() -> None:
    """Test redeeming a valid code for a registered user."""
    # Reset store
    DISCOUNT_STORE["WELCOME50"] = False

    result = redeem_discount("WELCOME50", "user_123")
    assert "Success" in result
    assert "redeemed successfully" in result
    assert DISCOUNT_STORE["WELCOME50"] is True


def test_redeem_discount_unregistered_user() -> None:
    """Test redeeming a code with a guest/unregistered user ID."""
    DISCOUNT_STORE["WELCOME50"] = False
    result = redeem_discount("WELCOME50", "guest_user")
    assert "Error" in result
    assert "Registered user account required" in result


def test_redeem_discount_invalid_code() -> None:
    """Test redeeming an invalid discount code."""
    result = redeem_discount("INVALID100", "user_123")
    assert "Error" in result
    assert "Invalid discount code" in result


def test_redeem_discount_already_redeemed() -> None:
    """Test that a single-use code can only be redeemed once."""
    DISCOUNT_STORE["WELCOME50"] = False

    # First redemption succeeds
    result1 = redeem_discount("WELCOME50", "user_123")
    assert "Success" in result1

    # Second redemption fails
    result2 = redeem_discount("WELCOME50", "user_456")
    assert "Error" in result2
    assert "already been redeemed" in result2


def test_custom_gemini_api_key() -> None:
    """Test that the Gemini model is initialized with the simulated API key."""
    model = Gemini(
        model="gemini-3.1-flash-lite", api_key="mock-key-value-12345"
    )
    client = model.api_client
    assert client._api_client.api_key == "mock-key-value-12345"


def test_award_loyalty_points_success() -> None:
    """Test successfully awarding loyalty points to a registered user."""
    LOYALTY_STORE.clear()
    PROCESSED_TRANSACTIONS.clear()

    result = award_loyalty_points("user_123", 150, "tx_1")
    assert "Success" in result
    assert "Awarded 150 points" in result
    assert LOYALTY_STORE["user_123"] == 150
    assert "tx_1" in PROCESSED_TRANSACTIONS


def test_award_loyalty_points_guest_fails() -> None:
    """Test that awarding loyalty points to a guest user fails."""
    LOYALTY_STORE.clear()
    PROCESSED_TRANSACTIONS.clear()

    result = award_loyalty_points("guest_user", 50, "tx_2")
    assert "Error" in result
    assert "Guest accounts are not eligible" in result
    assert "guest_user" not in LOYALTY_STORE


def test_award_loyalty_points_invalid_points() -> None:
    """Test that invalid point values are rejected."""
    LOYALTY_STORE.clear()
    PROCESSED_TRANSACTIONS.clear()

    # Negative points
    result1 = award_loyalty_points("user_123", -10, "tx_3")
    assert "Error" in result1
    assert "Validation failed" in result1

    # Over limit points (> 1000)
    result2 = award_loyalty_points("user_123", 1005, "tx_4")
    assert "Error" in result2
    assert "Validation failed" in result2


def test_award_loyalty_points_idempotency() -> None:
    """Test that duplicate transaction IDs are rejected."""
    LOYALTY_STORE.clear()
    PROCESSED_TRANSACTIONS.clear()

    # First attempt succeeds
    result1 = award_loyalty_points("user_123", 100, "tx_dup")
    assert "Success" in result1

    # Second attempt with same transaction ID fails
    result2 = award_loyalty_points("user_123", 100, "tx_dup")
    assert "Error" in result2
    assert "already processed" in result2
    assert LOYALTY_STORE["user_123"] == 100


def test_process_cart_checkout_success() -> None:
    """Test successfully checking out a cart without a discount code."""
    # Reset stores
    CART_STORE["cart_2"] = {
        "user_id": "user_456",
        "items": [{"name": "Headphones", "price": 150.0}],
        "total": 150.0,
        "is_checked_out": False,
    }

    result = process_cart_checkout("cart_2", "user_456")
    assert "Success" in result
    assert "completed for cart cart_2" in result
    assert "Final total: 150.0" in result
    assert CART_STORE["cart_2"]["is_checked_out"] is True


def test_process_cart_checkout_with_discount_success() -> None:
    """Test successfully checking out a cart with a discount code."""
    CART_STORE["cart_1"] = {
        "user_id": "user_123",
        "items": [{"name": "Laptop", "price": 900.0}, {"name": "Mouse", "price": 50.0}],
        "total": 950.0,
        "is_checked_out": False,
    }
    DISCOUNT_STORE["WELCOME50"] = False

    result = process_cart_checkout("cart_1", "user_123", "WELCOME50")
    assert "Success" in result
    assert "Final total: 475.0" in result
    assert CART_STORE["cart_1"]["is_checked_out"] is True
    assert DISCOUNT_STORE["WELCOME50"] is True


def test_process_cart_checkout_wrong_owner_fails() -> None:
    """Test that checking out another user's cart is rejected."""
    CART_STORE["cart_1"] = {
        "user_id": "user_123",
        "items": [{"name": "Laptop", "price": 900.0}, {"name": "Mouse", "price": 50.0}],
        "total": 950.0,
        "is_checked_out": False,
    }

    result = process_cart_checkout("cart_1", "user_456")
    assert "Error" in result
    assert "Access denied" in result
    assert CART_STORE["cart_1"]["is_checked_out"] is False


def test_process_cart_checkout_guest_discount_fails() -> None:
    """Test that guest accounts are blocked from using discount codes during checkout."""
    CART_STORE["cart_guest"] = {
        "user_id": "guest_789",
        "items": [{"name": "Book", "price": 20.0}],
        "total": 20.0,
        "is_checked_out": False,
    }
    DISCOUNT_STORE["WELCOME50"] = False

    result = process_cart_checkout("cart_guest", "guest_789", "WELCOME50")
    assert "Error" in result
    assert "Registered account required to apply discounts" in result
    assert CART_STORE["cart_guest"]["is_checked_out"] is False
    assert DISCOUNT_STORE["WELCOME50"] is False


def test_process_cart_checkout_already_checked_out_fails() -> None:
    """Test that a cart cannot be checked out more than once."""
    CART_STORE["cart_2"] = {
        "user_id": "user_456",
        "items": [{"name": "Headphones", "price": 150.0}],
        "total": 150.0,
        "is_checked_out": False,
    }

    # First checkout succeeds
    result1 = process_cart_checkout("cart_2", "user_456")
    assert "Success" in result1

    # Second checkout fails
    result2 = process_cart_checkout("cart_2", "user_456")
    assert "Error" in result2
    assert "already been checked out" in result2


def test_process_cart_checkout_invalid_cart_fails() -> None:
    """Test checkout fails for non-existent cart."""
    result = process_cart_checkout("cart_non_existent", "user_123")
    assert "Error" in result
    assert "not found" in result


def test_process_cart_checkout_double_discount_fails() -> None:
    """Test that a discount code cannot be redeemed twice across multiple checkouts."""
    CART_STORE["cart_1"] = {
        "user_id": "user_123",
        "items": [{"name": "Laptop", "price": 900.0}, {"name": "Mouse", "price": 50.0}],
        "total": 950.0,
        "is_checked_out": False,
    }
    CART_STORE["cart_2"] = {
        "user_id": "user_456",
        "items": [{"name": "Headphones", "price": 150.0}],
        "total": 150.0,
        "is_checked_out": False,
    }
    DISCOUNT_STORE["SUMMER20"] = False

    # First user checkouts with SUMMER20 successfully
    result1 = process_cart_checkout("cart_1", "user_123", "SUMMER20")
    assert "Success" in result1
    assert DISCOUNT_STORE["SUMMER20"] is True

    # Second user tries to checkout with SUMMER20 and is rejected
    result2 = process_cart_checkout("cart_2", "user_456", "SUMMER20")
    assert "Error" in result2
    assert "already been redeemed" in result2
    assert CART_STORE["cart_2"]["is_checked_out"] is False


def test_update_discount_status_activate_success() -> None:
    """Test successfully activating a discount code by an administrator."""
    DISCOUNT_STORE.clear()

    # Activating an inactive/new code sets its redeemed status to False
    result = update_discount_status("SPRING10", True, "admin_123")
    assert "Success" in result
    assert "SPRING10" in DISCOUNT_STORE
    assert DISCOUNT_STORE["SPRING10"] is False  # False means active/unredeemed


def test_update_discount_status_deactivate_success() -> None:
    """Test successfully deactivating a discount code by an administrator."""
    DISCOUNT_STORE["SUMMER20"] = False

    # Deactivating an active code sets its redeemed status to True
    result = update_discount_status("SUMMER20", False, "admin_456")
    assert "Success" in result
    assert DISCOUNT_STORE["SUMMER20"] is True  # True means deactivated/redeemed


def test_update_discount_status_non_admin_fails() -> None:
    """Test that a non-administrator user is blocked from changing discount code status."""
    result = update_discount_status("SUMMER20", True, "user_123")
    assert "Error" in result
    assert "Administrator privileges required" in result

    result2 = update_discount_status("SUMMER20", True, "guest_user")
    assert "Error" in result2
    assert "Administrator privileges required" in result2


def test_update_discount_status_invalid_format_fails() -> None:
    """Test that discount codes with invalid format (non-alphanumeric) are rejected."""
    result = update_discount_status("SPRING_10", True, "admin_123")
    assert "Error" in result
    assert "only alphanumeric characters" in result
