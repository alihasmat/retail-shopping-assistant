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

from __future__ import annotations
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.apps.app import App
from google.adk.models.google_llm import Gemini as ADKGemini
from google.adk.workflow import Workflow
from google.genai import Client
import logging
import threading
from pydantic import BaseModel, Field, field_validator



# FIX: Subclass Gemini to support and propagate the api_key parameter in Pydantic v2
class Gemini(ADKGemini):
    api_key: str = None

    @property
    def api_client(self) -> Client:
        if self.api_key:
            if not hasattr(self, "_cached_api_client") or self._cached_api_client is None:
                self._cached_api_client = Client(api_key=self.api_key)
            return self._cached_api_client
        return super().api_client



import os

# Simulated vulnerability: Unsafe hardcoded API key resolved
model_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "mock-key-value-12345"
model = Gemini(model="gemini-3.1-flash-lite", api_key=model_api_key)


# In-memory discount redemption store (simulating database state)
DISCOUNT_STORE: dict[str, bool] = {"WELCOME50": False, "SUMMER20": False}


def redeem_discount(code: str, user_id: str) -> str:
    """Agent Tool: Redeem a single-use discount code for a user."""
    if not user_id or user_id.startswith("guest_"):
        return "Error: Registered user account required to redeem discounts."
    if code not in DISCOUNT_STORE:
        return "Error: Invalid discount code."
    if DISCOUNT_STORE[code]:
        return "Error: Discount code has already been redeemed."

    DISCOUNT_STORE[code] = True
    return f"Success: Discount code {code} redeemed successfully for user {user_id}."


logger = logging.getLogger(__name__)

# In-memory loyalty points store
LOYALTY_STORE: dict[str, int] = {}
# Idempotency tracking for transactions
PROCESSED_TRANSACTIONS: set[str] = set()
store_lock = threading.Lock()


class AwardLoyaltyPointsInput(BaseModel):
    user_id: str = Field(..., min_length=1)
    points: int = Field(..., gt=0, le=1000)
    transaction_id: str = Field(..., min_length=1)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if v.startswith("guest_"):
            raise ValueError("Guest accounts are not eligible for loyalty points.")
        return v


def award_loyalty_points(user_id: str, points: int, transaction_id: str) -> str:
    """Agent Tool: Award loyalty points to a registered user's account after a purchase."""
    try:
        validated = AwardLoyaltyPointsInput(
            user_id=user_id, points=points, transaction_id=transaction_id
        )
    except Exception as e:
        return f"Error: Validation failed. {e}"

    with store_lock:
        if validated.transaction_id in PROCESSED_TRANSACTIONS:
            return f"Error: Transaction {validated.transaction_id} already processed."

        current_points = LOYALTY_STORE.get(validated.user_id, 0)
        new_points = current_points + validated.points
        LOYALTY_STORE[validated.user_id] = new_points
        PROCESSED_TRANSACTIONS.add(validated.transaction_id)

        logger.info(
            f"Successfully awarded {validated.points} points to user {validated.user_id} "
            f"for transaction {validated.transaction_id}."
        )
        return f"Success: Awarded {validated.points} points to user {validated.user_id}. New balance: {new_points}."


# Simulated server-side shopping cart data store
CART_STORE: dict[str, dict[str, Any]] = {
    "cart_1": {
        "user_id": "user_123",
        "items": [{"name": "Laptop", "price": 900.0}, {"name": "Mouse", "price": 50.0}],
        "total": 950.0,
        "is_checked_out": False,
    },
    "cart_2": {
        "user_id": "user_456",
        "items": [{"name": "Headphones", "price": 150.0}],
        "total": 150.0,
        "is_checked_out": False,
    },
    "cart_guest": {
        "user_id": "guest_789",
        "items": [{"name": "Book", "price": 20.0}],
        "total": 20.0,
        "is_checked_out": False,
    },
}


class ProcessCartCheckoutInput(BaseModel):
    cart_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    discount_code: str | None = Field(default=None)


def process_cart_checkout(
    cart_id: str, user_id: str, discount_code: str | None = None
) -> str:
    """Agent Tool: Apply an optional discount code and checkout a user's shopping cart."""
    try:
        validated = ProcessCartCheckoutInput(
            cart_id=cart_id, user_id=user_id, discount_code=discount_code
        )
    except Exception as e:
        return f"Error: Validation failed. {e}"

    with store_lock:
        if validated.cart_id not in CART_STORE:
            return f"Error: Cart {validated.cart_id} not found."

        cart = CART_STORE[validated.cart_id]

        if cart["user_id"] != validated.user_id:
            return f"Error: Access denied. Cart {validated.cart_id} does not belong to user {validated.user_id}."

        if cart["is_checked_out"]:
            return f"Error: Cart {validated.cart_id} has already been checked out."

        final_total = cart["total"]
        discount_applied = 0.0

        if validated.discount_code:
            if validated.user_id.startswith("guest_"):
                return "Error: Registered account required to apply discounts during checkout."

            if validated.discount_code not in DISCOUNT_STORE:
                return f"Error: Invalid discount code {validated.discount_code}."

            if DISCOUNT_STORE[validated.discount_code]:
                return f"Error: Discount code {validated.discount_code} has already been redeemed."

            rate = (
                0.5
                if validated.discount_code == "WELCOME50"
                else 0.2
                if validated.discount_code == "SUMMER20"
                else 0.0
            )
            discount_applied = cart["total"] * rate
            final_total -= discount_applied
            DISCOUNT_STORE[validated.discount_code] = True

        cart["is_checked_out"] = True
        cart["total"] = final_total

        logger.info(
            f"Checkout successful for cart {validated.cart_id}. "
            f"User: {validated.user_id}, Original: {cart['total'] + discount_applied}, "
            f"Discount Applied: {discount_applied}, Final Total: {final_total}."
        )

        return (
            f"Success: Checkout completed for cart {validated.cart_id}. "
            f"Applied discount: {discount_applied}. Final total: {final_total}."
        )


class UpdateDiscountStatusInput(BaseModel):
    code: str = Field(..., min_length=1)
    active: bool
    user_id: str = Field(..., min_length=1)

    @field_validator("user_id")
    @classmethod
    def validate_admin_user(cls, v: str) -> str:
        if not v.startswith("admin_"):
            raise ValueError(
                "Administrator privileges required to update discount status."
            )
        return v

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError(
                "Discount code must contain only alphanumeric characters."
            )
        return v.upper()


def update_discount_status(code: str, active: bool, user_id: str) -> str:
    """Agent Tool: Activate or deactivate a discount code. Requires administrative privileges."""
    try:
        validated = UpdateDiscountStatusInput(
            code=code, active=active, user_id=user_id
        )
    except Exception as e:
        return f"Error: Validation failed. {e}"

    with store_lock:
        # True active means "not redeemed yet" in DISCOUNT_STORE
        # False active means "already redeemed / inactive" in DISCOUNT_STORE
        DISCOUNT_STORE[validated.code] = not validated.active

        status_str = "activated" if validated.active else "deactivated"
        logger.info(
            f"Administrator {validated.user_id} {status_str} discount code {validated.code}."
        )

        return f"Success: Discount code {validated.code} has been {status_str}."


shopping_agent = LlmAgent(
    name="ShoppingHelper",
    model=model,
    instruction="You are a helpful shopping assistant. Use your tools to redeem discount codes, award loyalty points, process cart checkouts, and update discount statuses for users.",
    tools=[
        redeem_discount,
        award_loyalty_points,
        process_cart_checkout,
        update_discount_status,
    ],
)




root_workflow = Workflow(
    name="shopping_assistant_workflow",
    # FIX: Replaced Edge.chain with standard tuple-based edges
    edges=[("START", shopping_agent)],
)

app = App(
    # FIX: Set name to "app" to match folder name and avoid session errors
    name="app",
    root_agent=root_workflow,
)

root_agent = root_workflow
