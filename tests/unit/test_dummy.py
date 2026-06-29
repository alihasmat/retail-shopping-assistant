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

from app.agent import DISCOUNT_STORE, Gemini, redeem_discount


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
        model="gemini-3.1-flash-lite", api_key="AIzaSyD-mock-key-value-12345"
    )
    client = model.api_client
    assert client._api_client.api_key == "AIzaSyD-mock-key-value-12345"
