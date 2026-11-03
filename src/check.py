"""Is this output usable as it stands?

Three questions, in order, each only asked if the one before passed:

1. Does it parse? `json.loads` on the text exactly as it came back. No
   stripping code fences, no hunting for the first `{`. If you have to repair
   it before it parses, a program downstream will have to as well, and the
   repair is the fragile part.
2. Is it the right shape? Validated against `Order`, strictly.
3. Does it add up? The self-consistency checks in validate.py.

The reasons it gives are a diagnosis for you to read. They are not used to
fix anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from .schema import Order
from .validate import problems


@dataclass
class Verdict:
    parses: bool
    right_shape: bool
    adds_up: bool
    reason: str = ""
    order: Optional[Order] = None


def _why_not_json(text: str, error: json.JSONDecodeError) -> str:
    stripped = text.lstrip()
    if not stripped:
        return "empty"
    if stripped.startswith("```"):
        return "wrapped in a markdown code fence"
    if stripped[0] not in "{[":
        return "text before the JSON"
    if error.msg == "Extra data":
        return "text after the JSON"
    return f"invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})"


def _why_wrong_shape(error: ValidationError) -> str:
    first = error.errors()[0]
    where = ".".join(str(part) for part in first["loc"]) or "top level"
    more = len(error.errors()) - 1
    suffix = f" (+{more} more)" if more else ""
    return f"{where}: {first['msg']}{suffix}"


def check_output(text: str) -> Verdict:
    try:
        json.loads(text)
    except json.JSONDecodeError as error:
        return Verdict(False, False, False, _why_not_json(text, error))

    try:
        order = Order.model_validate_json(text)
    except ValidationError as error:
        return Verdict(True, False, False, _why_wrong_shape(error))

    found = problems(order)
    if found:
        return Verdict(True, True, False, "; ".join(found), order)
    return Verdict(True, True, True, "", order)
