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
"""Security boundaries and business logic test suite for the redeem_discount tool."""

import pytest
from app.agent import DISCOUNT_STORE, redeem_discount


def test_redeem_discount_success() -> None:
    """Test successful discount code redemption by a registered user."""
    DISCOUNT_STORE["WELCOME50"] = False

    result = redeem_discount("WELCOME50", "user_123")
    assert "Success" in result
    assert "redeemed successfully" in result
    assert DISCOUNT_STORE["WELCOME50"] is True


def test_redeem_discount_guest_fails() -> None:
    """Test that a guest user (starts with guest_) is rejected from redeeming a discount."""
    DISCOUNT_STORE["WELCOME50"] = False

    result = redeem_discount("WELCOME50", "guest_user")
    assert "Error" in result
    assert "Registered user account required" in result
    assert DISCOUNT_STORE["WELCOME50"] is False


def test_redeem_discount_empty_user_fails() -> None:
    """Test that empty or None user IDs are rejected from redeeming a discount."""
    DISCOUNT_STORE["WELCOME50"] = False

    # Test empty string
    result_empty = redeem_discount("WELCOME50", "")
    assert "Error" in result_empty
    assert "Registered user account required" in result_empty

    # Test None
    result_none = redeem_discount("WELCOME50", None)
    assert "Error" in result_none
    assert "Registered user account required" in result_none
    assert DISCOUNT_STORE["WELCOME50"] is False


def test_redeem_discount_already_redeemed_fails() -> None:
    """Test that a single-use discount code cannot be redeemed twice."""
    DISCOUNT_STORE["WELCOME50"] = False

    # First redemption succeeds
    result1 = redeem_discount("WELCOME50", "user_123")
    assert "Success" in result1

    # Second redemption fails
    result2 = redeem_discount("WELCOME50", "user_456")
    assert "Error" in result2
    assert "already been redeemed" in result2


def test_redeem_discount_invalid_code_fails() -> None:
    """Test that an invalid/non-existent code is rejected."""
    result = redeem_discount("INVALID999", "user_123")
    assert "Error" in result
    assert "Invalid discount code" in result
