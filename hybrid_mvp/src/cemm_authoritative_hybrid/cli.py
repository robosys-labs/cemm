from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .bootstrap import load_runtime

DEMO_TURNS = (
    "hello",
    "what can you do",
    "can you learn",
    "alice is bob mother-in-law",
    "is bob married",
    "mary said bob left",
    "did bob leave",
    "did mary say bob left",
    "do you have a telescope",
    "server is offline",
    "imagine server is online",
    "turn lamp on",
    "yoz means hello",
)


def _diagnostic(cycle: Any) -> dict[str, Any]:
    """Return the exact cycle diagnostic; R1 authorizes no response surface."""
    return cycle.as_dict()


def demo(runtime: Any, trace: bool = False) -> list[Any]:
    rows = []
    session_ref = "session:demo"
    for text in DEMO_TURNS:
        cycle = runtime.process(session_ref, text, trace=trace)
        rows.append(cycle)
        print(f"USER: {text}")
        print(json.dumps(_diagnostic(cycle), indent=2, sort_keys=True))
    return rows


def interactive(runtime: Any, trace: bool = False) -> None:
    print("CEMM authoritative hybrid MVP. /new, /trace, /quit")
    tracing = trace
    session_index = 0
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            print()
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/new":
            session_index += 1
            print("cemm> new session")
            continue
        if text == "/trace":
            tracing = not tracing
            print(f"cemm> trace={tracing}")
            continue
        cycle = runtime.process(
            f"session:interactive:{session_index}", text, trace=tracing
        )
        print(json.dumps(_diagnostic(cycle), indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--profile", default="development")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    runtime = load_runtime(args.root, profile=args.profile)
    if args.demo:
        demo(runtime, args.trace)
    else:
        interactive(runtime, args.trace)


if __name__ == "__main__":
    main()