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
            return Client(api_key=self.api_key)
        return super().api_client


import os

# Simulated vulnerability: Unsafe hardcoded API key resolved
model_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "mock-key-value-12345"
model = Gemini(model="gemini-3.1-flash-lite", api_key=model_api_key)


# In-memory discount redemption store (simulating database state)
DISCOUNT_STORE: dict[str, bool] = {"WELCOME50": False, "SUMMER20": False}


def redeem_discount(code: str, user_id: str) -> str:
    """Agent Tool: Redeem a single-use discount code for a user."""
    if code not in DISCOUNT_STORE:
        return "Error: Invalid discount code."
    if DISCOUNT_STORE[code]:
        return "Error: Discount code has already been redeemed."
    if not user_id or user_id.startswith("guest_"):
        return "Error: Registered user account required to redeem discounts."

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


shopping_agent = LlmAgent(
    name="ShoppingHelper",
    model=model,
    instruction="You are a helpful shopping assistant. Use your tools to redeem discount codes and award loyalty points for users.",
    tools=[redeem_discount, award_loyalty_points],
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
