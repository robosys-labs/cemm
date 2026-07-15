"""CEMM canonical v3.4.1 command-line entrypoint."""
from __future__ import annotations

import argparse
import sys
import time

from .app.runtime import Runtime


def process_input(
    text: str,
    runtime: Runtime,
    context_id: str,
) -> str:
    return runtime.run_text_result(text, context_id=context_id).output_text


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — cognitive semantic kernel")
    parser.add_argument("--eval", help="Evaluate one text input and exit")
    parser.add_argument("--once", help="Handle one user turn")
    parser.add_argument("--chat", action="store_true", help="Interactive chat")
    parser.add_argument("--context-id", default="", help="Stable conversation context")
    args = parser.parse_args()

    runtime = Runtime()
    context_id = args.context_id or f"session:{int(time.time())}"

    one_shot = args.once if args.once is not None else args.eval
    if one_shot is not None:
        result = runtime.run_text_result(one_shot, context_id=context_id)
        if result.output_text:
            print(result.output_text)
        if result.errors:
            print("\n".join(result.errors), file=sys.stderr)
        raise SystemExit(0 if result.output_text else 2)

    print("CEMM — canonical v3.4.1 runtime")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.casefold() in {"exit", "quit"}:
            break
        result = runtime.run_text_result(text, context_id=context_id)
        if result.output_text:
            print(result.output_text)
        else:
            # Transport diagnostic, deliberately not represented as CEMM's
            # semantic response.
            print("[no semantically authorized surface output]", file=sys.stderr)
        if result.errors:
            print("[trace] " + " | ".join(result.errors), file=sys.stderr)


if __name__ == "__main__":
    main()
