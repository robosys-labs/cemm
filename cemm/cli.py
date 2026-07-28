"""CEMM v1 command line interface."""
from __future__ import annotations
import argparse, json, sys
from cemm.model import canonical
from cemm.authority import load_documents, validate_documents, validate_pack_constants
from cemm.activation import assert_native_semantic_activation
from cemm.runtime import MODE_NORMAL, MODE_READ_ONLY, MODE_REVIEWED_TEACH, Runtime
from cemm.store import Store


def runtime(args):
    instance = Runtime(Store(args.db), args.pack)
    assert_native_semantic_activation(instance.i.form_pack, instance.s)
    return instance

def cmd_init(args):
    store = Store(args.db)
    if store.db.execute("SELECT 1 FROM atoms LIMIT 1").fetchone():
        raise RuntimeError("database is already initialized; use explicit acquisition/import tooling")
    documents = load_documents(args.data)
    report = validate_documents(documents, require_foundations=True)
    authority_refs = {
        str(atom["ref"])
        for document in documents
        for atom in document.data.get("atoms", ())
    }
    validate_pack_constants((args.pack,), authority_refs)
    imported = store.import_bundle(args.data)
    attestation = Runtime(store, args.pack).runtime_attestation
    print(canonical({"authority_bundle": report.as_dict(), "import": imported, "runtime": attestation}))

def cmd_chat(args):
    rt=runtime(args)
    for line in sys.stdin:
        if line.strip(): print(rt.process(line.strip(),mode=MODE_NORMAL)["response"])

def cmd_process(args):
    print(json.dumps(runtime(args).process(args.text or "",mode=args.mode),ensure_ascii=False,indent=2))

def cmd_inspect(args):
    store=Store(args.db)
    tables=("atoms","applications","bindings","claims","claim_occurrences","epistemic_placements","rules","rule_index","frontiers","commit_receipts","common_ground","effect_journal")
    for table in tables: print(table,store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    print("revisions",canonical(store.revisions()))
    if args.full_hash: print("snapshot",store.snapshot_hash())

def cmd_reload(args): print(canonical(runtime(args).reload_authority()))

def cmd_acquire(args):
    from cemm.acquisition import acquire_reviewed
    store=Store(args.db); rt=Runtime(store,args.pack)
    doc={"text":args.text,"mentions":json.loads(args.mentions),"language":args.language}
    print(json.dumps(acquire_reviewed(store,rt,doc),ensure_ascii=False,indent=2))

def main():
    parser=argparse.ArgumentParser(prog="cemm")
    sub=parser.add_subparsers(dest="command",required=True)
    def common(p): p.add_argument("--db",required=True);p.add_argument("--pack",required=True)
    p=sub.add_parser("init");common(p);p.add_argument("--data",action="append",default=[]);p.set_defaults(func=cmd_init)
    p=sub.add_parser("chat");common(p);p.set_defaults(func=cmd_chat)
    p=sub.add_parser("process");common(p);p.add_argument("text");p.add_argument("--mode",choices=[MODE_NORMAL,MODE_READ_ONLY,MODE_REVIEWED_TEACH],default=MODE_NORMAL);p.set_defaults(func=cmd_process)
    p=sub.add_parser("inspect");common(p);p.add_argument("--full-hash",action="store_true");p.set_defaults(func=cmd_inspect)
    p=sub.add_parser("reload");common(p);p.set_defaults(func=cmd_reload)
    p=sub.add_parser("acquire-reviewed");common(p);p.add_argument("--text",required=True);p.add_argument("--mentions",required=True);p.add_argument("--language",default="en");p.set_defaults(func=cmd_acquire)
    args=parser.parse_args();args.func(args)
if __name__=="__main__": main()
