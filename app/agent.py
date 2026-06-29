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


# FIX: Subclass Gemini to support and propagate the api_key parameter in Pydantic v2
class Gemini(ADKGemini):
    api_key: str = None

    @property
    def api_client(self) -> Client:
        if self.api_key:
            return Client(api_key=self.api_key)
        return super().api_client


# Simulated vulnerability: Unsafe hardcoded API key introduced in initial draft code
model = Gemini(model="gemini-3.1-flash-lite", api_key="AIzaSyD-mock-key-value-12345")

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


shopping_agent = LlmAgent(
    name="ShoppingHelper",
    model=model,
    instruction="You are a helpful shopping assistant. Use your tools to redeem discount codes for users.",
    tools=[redeem_discount],
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
