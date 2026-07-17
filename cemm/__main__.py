"""CEMM v3.4.7 command-line entrypoint."""
from __future__ import annotations

import argparse
import json
import sys
import time

from .app.runtime import Runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM v3.4.7 cognitive semantic kernel")
    parser.add_argument("--eval", help="Evaluate one text input and exit")
    parser.add_argument("--once", help="Handle one user turn")
    parser.add_argument("--chat", action="store_true", help="Interactive chat")
    parser.add_argument("--context-id", default="", help="Stable conversation context")
    parser.add_argument("--language", default=None, help="Input language hint")
    parser.add_argument("--target-language", default=None, help="Output language")
    parser.add_argument("--database", default=":memory:", help="SQLite path")
    parser.add_argument("--trace-json", action="store_true", help="Print structured trace")
    args = parser.parse_args()

    runtime = Runtime(database_path=args.database)
    context_id = args.context_id or f"session:{int(time.time())}"
    one_shot = args.once if args.once is not None else args.eval
    try:
        if one_shot is not None:
            result = runtime.run_text(
                one_shot,
                context_id=context_id,
                language_hint=args.language,
                target_language=args.target_language,
            )
            if result.output_text:
                print(result.output_text)
            if args.trace_json:
                print(json.dumps({
                    "stages": result.trace.stages,
                    "details": result.trace.details,
                    "errors": result.trace.errors,
                }, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
            raise SystemExit(0 if result.output_text else 2)

        print("CEMM — canonical v3.4.7 runtime")
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
            result = runtime.run_text(
                text,
                context_id=context_id,
                language_hint=args.language,
                target_language=args.target_language,
            )
            if result.output_text:
                print(result.output_text)
            else:
                print("[no semantically authorized surface output]", file=sys.stderr)
            if args.trace_json and result.trace.errors:
                print(json.dumps(result.trace.errors, ensure_ascii=False), file=sys.stderr)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
