"""The two ways of asking: hoping for the shape, and constraining it.

Both send the same email. The difference is where the shape lives:

- prompt-only: the field list is in the prompt, and the model is asked
  nicely to return only JSON. Nothing enforces it.
- schema: the field list is in `output_config.format`, and the API constrains
  generation to it. The prompt just says what to do.

What's not here, on purpose: prefilling the assistant turn with `{` to force
JSON. That trick returns an error on current models. If you learned it, it's
gone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import anthropic

from .schema import json_schema

Mode = Literal["prompt", "schema"]

DEFAULT_MODEL = "claude-opus-5-5"
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_FILES: dict[str, str] = {"prompt": "prompt-only.md", "schema": "schema.md"}


@dataclass
class Result:
    text: str
    stop_reason: str
    input_tokens: int
    output_tokens: int


def require_api_key() -> None:
    """Fail early and clearly rather than deep inside an API call."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...      (Windows: set ANTHROPIC_API_KEY=...)"
        )


def load_prompt(mode: Mode) -> str:
    return (PROMPTS / PROMPT_FILES[mode]).read_text(encoding="utf-8").strip()


def build_request(email: str, mode: Mode, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """The full request, so you can see exactly what each mode sends."""
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": 16000,
        "messages": [
            {"role": "user", "content": f"{load_prompt(mode)}\n\n<email>\n{email}\n</email>"}
        ],
    }
    if mode == "schema":
        request["output_config"] = {"format": {"type": "json_schema", "schema": json_schema()}}
    return request


def response_text(response: Any) -> str:
    """The answer, as text. Current models may put thinking blocks first."""
    return "".join(block.text for block in response.content if block.type == "text")


def extract(client: Any, email: str, mode: Mode, model: str = DEFAULT_MODEL) -> Result:
    response = client.messages.create(**build_request(email, mode, model))
    return Result(
        text=response_text(response),
        stop_reason=response.stop_reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


def make_client() -> anthropic.Anthropic:
    require_api_key()
    return anthropic.Anthropic()
