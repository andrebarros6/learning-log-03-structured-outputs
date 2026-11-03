"""Get JSON that parses every time.

    python -m src.main check chat               # step 1: what the chat gave you
    python -m src.main run --mode prompt        # step 2: asking nicely, via the API
    python -m src.main run --mode schema        # step 3: constraining the shape

`check` needs no API key. `run` saves every raw response under out/, so you
can open the ones that failed and see why.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from .check import Verdict, check_output
from .extract import DEFAULT_MODEL, Mode, extract, make_client

ROOT = Path(__file__).resolve().parent.parent
EMAILS = ROOT / "data" / "emails"
OUT = ROOT / "out"


def _mark(ok: bool, asked: bool = True) -> str:
    if not asked:
        return "-"
    return "yes" if ok else "NO"


def print_table(rows: list[tuple[str, Verdict]]) -> None:
    print(f"{'output':<22} {'parses':>6} {'shape':>6} {'adds up':>8}  why not")
    print("-" * 78)
    for name, v in rows:
        print(
            f"{name:<22} {_mark(v.parses):>6} {_mark(v.right_shape, v.parses):>6}"
            f" {_mark(v.adds_up, v.right_shape):>8}  {v.reason}"
        )
    n = len(rows)
    if not n:
        return
    parsed = sum(v.parses for _, v in rows)
    shaped = sum(v.right_shape for _, v in rows)
    added = sum(v.adds_up for _, v in rows)
    print("-" * 78)
    print(f"parses {parsed}/{n}, right shape {shaped}/{n}, adds up {added}/{n}")


def cmd_check(folder: Path) -> None:
    files = sorted(folder.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files in {folder}. Paste each chat reply into one first.")
    print_table([(f.name, check_output(f.read_text(encoding="utf-8"))) for f in files])


def cmd_run(mode: Mode, runs: int, model: str) -> None:
    client = make_client()
    out = OUT / mode
    out.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, Verdict]] = []
    tokens_in = tokens_out = 0

    emails = sorted(EMAILS.glob("*.txt"))
    print(f"{len(emails)} emails x {runs} runs, mode={mode}, model={model}\n")
    for path in emails:
        email = path.read_text(encoding="utf-8")
        for k in range(1, runs + 1):
            result = extract(client, email, mode, model)
            tokens_in += result.input_tokens
            tokens_out += result.output_tokens
            name = f"{path.stem}-{k}.txt"
            (out / name).write_text(result.text, encoding="utf-8")
            verdict = check_output(result.text)
            if result.stop_reason != "end_turn":
                verdict.reason = f"[stopped: {result.stop_reason}] {verdict.reason}"
            rows.append((name, verdict))

    print_table(rows)
    print(f"\ntokens: {tokens_in:,} in, {tokens_out:,} out. Raw responses are in {out}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Check outputs you saved by hand")
    check.add_argument("folder", type=Path)

    run = sub.add_parser("run", help="Extract every sample email through the API")
    run.add_argument("--mode", choices=["prompt", "schema"], required=True)
    run.add_argument("--runs", type=int, default=3, help="Runs per email (default 3)")
    run.add_argument("--model", default=DEFAULT_MODEL)

    args = parser.parse_args()
    if args.command == "check":
        cmd_check(args.folder)
    else:
        cmd_run(cast(Mode, args.mode), args.runs, args.model)


if __name__ == "__main__":
    main()
