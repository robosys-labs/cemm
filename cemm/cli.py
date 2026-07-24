"""CEMM v1 CLI.

Ports the v4 MVP CLI (cemm_mvp.py lines 707-719) and adds the two commands v4
was missing (weakness #3): ``reload`` and ``acquire``.

Entry point: ``python -m cemm.cli``.
"""
from __future__ import annotations
import argparse, json, sys

from cemm.store import Store
from cemm.runtime import Runtime
from cemm.model import canonical


def cmd_init(args):
    s = Store(args.db)
    for d in args.data:
        s.import_data(d)
    rt = Runtime(s, args.pack)
    print(canonical(rt.runtime_attestation))


def cmd_chat(args):
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    for line in sys.stdin:
        if line.strip():
            print(rt.process(line.strip())["response"])


def cmd_learn(args):
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    print(json.dumps(rt.process(args.text or "", learn=True, teach=False), ensure_ascii=False, indent=2))


def cmd_teach(args):
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    print(json.dumps(rt.process(args.text or "", learn=True, teach=True), ensure_ascii=False, indent=2))


def cmd_ask(args):
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    print(json.dumps(rt.process(args.text or "", learn=False, teach=False), ensure_ascii=False, indent=2))


def cmd_inspect(args):
    s = Store(args.db)
    for t in ("atoms", "operator_roles", "applications", "bindings", "claims",
              "rules", "designation_index", "label_stats", "frontiers", "generations"):
        print(t, s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
    print("snapshot", s.snapshot_hash())


def cmd_reload(args):
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    att = rt.reload_authority()
    print(f"Authority reloaded to generation {att['authority_generation']}.")


def cmd_acquire(args):
    from cemm.acquisition import acquire
    s = Store(args.db)
    rt = Runtime(s, args.pack)
    mentions = json.loads(args.mentions)
    doc = {"text": args.text, "mentions": mentions, "language": args.language}
    result = acquire(s, rt, doc)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="cemm")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--data", action="append", default=[])
    p.set_defaults(func=cmd_init)

    # chat
    p = sub.add_parser("chat")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_chat)

    # learn
    p = sub.add_parser("learn")
    p.add_argument("text", nargs="?")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_learn)

    # teach
    p = sub.add_parser("teach")
    p.add_argument("text", nargs="?")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_teach)

    # ask
    p = sub.add_parser("ask")
    p.add_argument("text", nargs="?")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_ask)

    # inspect
    p = sub.add_parser("inspect")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_inspect)

    # reload (NEW - weakness #3)
    p = sub.add_parser("reload")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.set_defaults(func=cmd_reload)

    # acquire (NEW - weakness #3)
    p = sub.add_parser("acquire")
    p.add_argument("--db", required=True)
    p.add_argument("--pack", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--mentions", required=True)
    p.add_argument("--language", default="en")
    p.set_defaults(func=cmd_acquire)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
