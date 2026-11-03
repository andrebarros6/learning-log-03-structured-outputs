"""Checks a schema can't make.

A schema guarantees shape: the right fields, the right types. It can't
guarantee the values are right. A perfectly shaped order whose line items
don't add up to its total parses every time, and is still wrong.

These checks need no answer key. They only ask whether the extraction agrees
with itself.
"""

from __future__ import annotations

import re

from .schema import Order

# Money is compared to the cent. Floats can't hold 0.1 exactly, so allow
# half a cent either way rather than demand exact equality.
TOLERANCE = 0.005


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def problems(order: Order) -> list[str]:
    """Everything that doesn't add up. An empty list means it's consistent."""
    found: list[str] = []

    if not re.fullmatch(r"[A-Z]{3}", order.currency):
        found.append(f"currency {order.currency!r} is not a three-letter ISO code")

    if not order.items:
        found.append("no line items")

    for item in order.items:
        if item.quantity < 1:
            found.append(f"{item.description!r}: quantity {item.quantity}")
        if item.unit_price is not None and not _close(
            item.quantity * item.unit_price, item.line_total
        ):
            found.append(
                f"{item.description!r}: {item.quantity} x {item.unit_price:.2f}"
                f" is not {item.line_total:.2f}"
            )

    amounts = {
        "discount": order.discount,
        "shipping": order.shipping,
        "tax": order.tax,
        "total": order.total,
    }
    amounts.update({f"line total of {i.description!r}": i.line_total for i in order.items})
    for name, value in amounts.items():
        if value < 0:
            found.append(f"{name} is negative ({value:.2f})")

    items_sum = sum(i.line_total for i in order.items)
    expected = items_sum - order.discount + order.shipping + order.tax
    if not _close(expected, order.total):
        found.append(
            f"items {items_sum:.2f} - discount {order.discount:.2f}"
            f" + shipping {order.shipping:.2f} + tax {order.tax:.2f}"
            f" = {expected:.2f}, but total is {order.total:.2f}"
        )

    return found
