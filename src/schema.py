"""The shape every extraction must have.

One definition, used twice. `Order.model_json_schema()` is what gets sent to
the API to constrain the output, and `Order.model_validate_json()` is what
checks an output afterwards, whichever way it was produced. If the two were
written separately they would drift, and you'd be checking against a shape
you never asked for.

The field descriptions say the same things as prompts/prompt-only.md, so the
comparison between the two modes is about *constraint*, not about one side
getting better instructions.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# extra="forbid": an output with a field we didn't ask for is the wrong shape.
# strict=True: "12.50" is not 12.50. A number that arrives as a string is a
# failure, not something to coerce quietly.
_STRICT = ConfigDict(extra="forbid", strict=True)


class LineItem(BaseModel):
    model_config = _STRICT

    description: str
    quantity: int = Field(description="A whole number")
    unit_price: Optional[float] = Field(
        description="The price of one unit, or null if the email doesn't state it"
    )
    line_total: float


class Order(BaseModel):
    model_config = _STRICT

    kind: Literal["order", "refund"]
    merchant: str = Field(description="The shop's name")
    order_id: Optional[str] = Field(
        description="The order number as written, or null if the email doesn't give one"
    )
    order_date: Optional[date] = Field(
        description="The date the order was placed, or null if unknown"
    )
    currency: str = Field(description="The ISO 4217 code, such as EUR, GBP or USD")
    items: list[LineItem]
    discount: float = Field(description="The total discount, as a positive number, or 0")
    shipping: float = Field(description="The shipping charged, or 0")
    tax: float = Field(
        description="Tax added on top of the item prices, or 0 if the prices already include it"
    )
    total: float = Field(description="The amount charged or refunded, as a positive number")


def json_schema() -> dict[str, Any]:
    """The schema the API constrains the output to."""
    return Order.model_json_schema()
