"""Tests for everything that doesn't need an API key.

The checker and the validation are pure logic. The API call is tested with a
fake client: what matters offline is that each mode sends the request you
think it sends.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.check import check_output
from src.extract import build_request, extract, response_text
from src.schema import Order, json_schema
from src.validate import problems

GOOD: dict[str, Any] = {
    "kind": "order",
    "merchant": "Marlowe & Finch Books",
    "order_id": "MF-20481",
    "order_date": "2026-10-05",
    "currency": "GBP",
    "items": [
        {"description": "The Overstory (paperback)", "quantity": 1,
         "unit_price": 10.99, "line_total": 10.99},
        {"description": "Field Notes, 3-pack", "quantity": 2,
         "unit_price": 9.5, "line_total": 19.0},
    ],
    "discount": 0,
    "shipping": 3.95,
    "tax": 0,
    "total": 33.94,
}


def with_changes(**changes: Any) -> str:
    return json.dumps({**GOOD, **changes})


# --- does it parse ------------------------------------------------------


def test_clean_json_passes_everything():
    v = check_output(json.dumps(GOOD))
    assert (v.parses, v.right_shape, v.adds_up) == (True, True, True)
    assert v.reason == ""


def test_code_fence_is_a_parse_failure_not_something_to_strip():
    v = check_output("```json\n" + json.dumps(GOOD) + "\n```")
    assert not v.parses
    assert v.reason == "wrapped in a markdown code fence"


def test_text_before_the_json():
    v = check_output("Here's the order:\n" + json.dumps(GOOD))
    assert not v.parses
    assert v.reason == "text before the JSON"


def test_text_after_the_json():
    v = check_output(json.dumps(GOOD) + "\n\nLet me know if you need anything else.")
    assert not v.parses
    assert v.reason == "text after the JSON"


def test_unescaped_quote_in_a_name_breaks_parsing():
    broken = json.dumps(GOOD).replace("The Overstory", 'Monitor arm 27" heavy')
    v = check_output(broken)
    assert not v.parses
    assert v.reason.startswith("invalid JSON")


def test_empty_output():
    assert check_output("").reason == "empty"


# --- is it the right shape ----------------------------------------------


def test_number_as_string_is_wrong_shape():
    v = check_output(with_changes(total="33.94"))
    assert v.parses and not v.right_shape
    assert v.reason.startswith("total:")


def test_extra_field_is_wrong_shape():
    v = check_output(with_changes(notes="paid by card"))
    assert v.parses and not v.right_shape


def test_missing_field_is_wrong_shape():
    data = dict(GOOD)
    del data["tax"]
    v = check_output(json.dumps(data))
    assert not v.right_shape
    assert "tax" in v.reason


def test_kind_outside_the_enum_is_wrong_shape():
    assert not check_output(with_changes(kind="receipt")).right_shape


def test_impossible_date_is_wrong_shape():
    assert not check_output(with_changes(order_date="2026-02-30")).right_shape


def test_null_order_id_and_date_are_allowed():
    v = check_output(with_changes(order_id=None, order_date=None))
    assert v.right_shape and v.adds_up


# --- does it add up -----------------------------------------------------


def test_total_that_does_not_add_up():
    v = check_output(with_changes(total=35.0))
    assert v.right_shape and not v.adds_up
    assert "but total is 35.00" in v.reason


def test_included_vat_counted_as_added_tax_fails():
    # The trap in 02-mercearia: VAT shown, but already inside the prices.
    v = check_output(with_changes(tax=2.10))
    assert not v.adds_up


def test_unit_price_times_quantity():
    items = [dict(GOOD["items"][1], line_total=9.5)]
    order = Order.model_validate_json(with_changes(items=items, total=13.45))
    assert any("2 x 9.50 is not 9.50" in p for p in problems(order))


def test_unit_price_may_be_null():
    items = [dict(item, unit_price=None) for item in GOOD["items"]]
    assert check_output(with_changes(items=items)).adds_up


def test_negative_amounts_are_flagged():
    order = Order.model_validate_json(with_changes(discount=-1.0, total=34.94))
    assert any("discount is negative" in p for p in problems(order))


def test_currency_must_be_iso():
    order = Order.model_validate_json(with_changes(currency="£"))
    assert any("ISO" in p for p in problems(order))


def test_float_noise_is_tolerated():
    # 10.99 + 19.0 + 3.95 is not exactly 33.94 in floating point.
    assert problems(Order.model_validate_json(json.dumps(GOOD))) == []


# --- the schema sent to the API -----------------------------------------

UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
               "multipleOf", "minLength", "maxLength", "pattern",
               "minItems", "maxItems", "uniqueItems"}


def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_schema_closes_every_object():
    for node in _walk(json_schema()):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False


def test_schema_requires_every_field():
    for node in _walk(json_schema()):
        if node.get("type") == "object":
            assert set(node["required"]) == set(node["properties"])


def test_schema_stays_inside_the_supported_subset():
    for node in _walk(json_schema()):
        assert not UNSUPPORTED & set(node), f"unsupported keyword in {node}"


# --- the request each mode sends ----------------------------------------


def test_prompt_mode_sends_no_schema():
    request = build_request("an email", "prompt")
    assert "output_config" not in request
    assert "Return only the JSON." in request["messages"][0]["content"]


def test_schema_mode_constrains_the_output():
    request = build_request("an email", "schema")
    fmt = request["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"] == json_schema()


@pytest.mark.parametrize("mode", ["prompt", "schema"])
def test_no_prefill(mode):
    # Prefilling the assistant turn returns an error on current models.
    messages = build_request("an email", mode)["messages"]
    assert [m["role"] for m in messages] == ["user"]


@pytest.mark.parametrize("mode", ["prompt", "schema"])
def test_email_is_sent_whole(mode):
    email = 'Cable tray "Slim" \\ black'
    assert email in build_request(email, mode)["messages"][0]["content"]


def _block(kind: str, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(type=kind, text=text)


def test_response_text_skips_thinking_blocks():
    response = SimpleNamespace(content=[_block("thinking"), _block("text", "{}")])
    assert response_text(response) == "{}"


class FakeMessages:
    def __init__(self) -> None:
        self.sent: dict[str, Any] = {}

    def create(self, **request: Any) -> SimpleNamespace:
        self.sent = request
        return SimpleNamespace(
            content=[_block("text", json.dumps(GOOD))],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=500, output_tokens=200),
        )


def test_extract_returns_text_and_usage():
    client = SimpleNamespace(messages=FakeMessages())
    result = extract(client, "an email", "schema")
    assert check_output(result.text).adds_up
    assert (result.input_tokens, result.output_tokens) == (500, 200)
    assert "output_config" in client.messages.sent
