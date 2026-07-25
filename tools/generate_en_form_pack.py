#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def lit_capture(name):
    return {"$capture": name}


def context(name):
    return {"$context": name}


def designation_claim(target="$capture:target", label="$capture:label", surface="surface"):
    return {
        "force": "claim",
        "apps": [{
            "operator": "op:designation",
            "args": {
                "role:target": target,
                "role:label_type": label,
                "role:surface": lit_capture(surface),
                "role:language": context("language_literal"),
                "role:script": context("script_literal"),
                "role:prior": context("one_float_literal"),
                "role:preferred": context("true_literal"),
            },
            "stance": "support",
        }],
        "query": None,
        "directive": None,
        "describe": None,
        "qualifiers": {"construction_family": "designation_claim"},
        "modality": "actual",
    }


def designation_query(target="$capture:target", label="$capture:label"):
    return {
        "force": "query",
        "apps": [],
        "query": {
            "restrictions": [{
                "operator": "op:designation",
                "args": {
                    "role:target": target,
                    "role:label_type": label,
                    "role:surface": "?q0",
                    "role:language": context("language_literal"),
                },
                "stance": "support",
            }],
            "variables": [{
                "ref": "?q0",
                "filler_kind": "literal:text",
                "role_ref": "role:surface",
            }],
            "projection": ["?q0"],
            "qualifiers": {"query_kind": "designation_property"},
        },
        "directive": None,
        "describe": None,
        "qualifiers": {"construction_family": "designation_query"},
        "modality": "actual",
    }


def meaning_query(surface="surface"):
    return {
        "force": "query",
        "apps": [],
        "query": {
            "restrictions": [{
                "operator": "op:designation",
                "args": {
                    "role:target": "?q0",
                    "role:label_type": "?q1",
                    "role:surface": lit_capture(surface),
                    "role:language": context("language_literal"),
                },
                "stance": "support",
            }],
            "variables": [
                {"ref": "?q0", "filler_kind": "atom", "role_ref": "role:target"},
                {"ref": "?q1", "filler_kind": "label_type", "role_ref": "role:label_type"},
            ],
            "projection": ["?q0", "?q1"],
            "qualifiers": {"query_kind": "designation_learning"},
        },
        "directive": None,
        "describe": None,
        "qualifiers": {"learning_operation": "resolve_designation"},
        "modality": "actual",
    }


def alias_claim(surface="surface", target="$capture:target"):
    packet = designation_claim(target=target, label="label:lexical", surface=surface)
    packet["qualifiers"] = {"construction_family": "lexical_alias_claim"}
    return packet


def p(ref, pattern, packet, weight=1.0, ignore=("discourse",)):
    return {
        "ref": ref,
        "pattern": pattern,
        "packet": packet,
        "weight": weight,
        "ignore_kinds": list(ignore),
        "preserve_unknowns": True,
    }


function_forms = """
a an the this these those some any each every either neither no all both few many much more most less least
and or but nor yet so if then else because since while although though unless until when whenever where wherever
who whom whose which what whatever why how whether
am is are was were be being been do does did doing have has had having can could may might must shall should will would
not n't to of in on at by for from with without into onto over under above below between among through during before after around about against toward towards
as than that there here it its itself they them their theirs themselves he him his himself she her hers herself we us our ours ourselves
i me my mine myself you your yours yourself yourselves
please let tell say ask answer mean means meant define defined explain describe call called name named know knew known learn learned remember remembered forget forgot forgotten
now today tonight tomorrow yesterday already still just also only even very really quite perhaps maybe probably certainly
up down out off back away together apart again once twice
""".split()

nonblocking = """
well okay ok alright right so actually basically honestly frankly anyway anyhow perhaps maybe please hey hi hello look listen hmm um uh oh wow
""".split()

constructions = [
    p("en:designation-claim:possessive", [
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"kind": "anchor", "anchor_kind": "label_type", "slot": "label"},
        {"literal": "is"},
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
    ], designation_claim(), 1.45),
    p("en:designation-claim:reverse", [
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
        {"literal": "is"},
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"kind": "anchor", "anchor_kind": "label_type", "slot": "label"},
    ], designation_claim(), 1.25),
    p("en:designation-query:what-is", [
        {"literal": "what"}, {"literal": "is"},
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"kind": "anchor", "anchor_kind": "label_type", "slot": "label"},
    ], designation_query(), 1.5),
    p("en:designation-query:tell-me", [
        {"literal": "tell"},
        {"kind": "anchor", "anchor_kind": "participant", "slot": "audience"},
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"kind": "anchor", "anchor_kind": "label_type", "slot": "label"},
    ], designation_query(), 1.15),
    p("en:name-claim:call-me", [
        {"literal": "call"},
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
    ], designation_claim(label="label:name"), 1.35),
    p("en:name-claim:i-go-by", [
        {"kind": "anchor", "anchor_kind": "participant", "slot": "target"},
        {"literal": "go"}, {"literal": "by"},
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
    ], designation_claim(label="label:name_alias"), 1.2),
    p("en:meaning-query:what-does", [
        {"literal": "what"}, {"literal": "does"},
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
        {"literal": "mean"},
    ], meaning_query(), 1.45),
    p("en:meaning-query:meaning-of", [
        {"literal": "what"}, {"literal": "is"}, {"literal": "the", "optional": True},
        {"literal": "meaning"}, {"literal": "of"},
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 8},
    ], meaning_query(), 1.35),
    p("en:meaning-query:anaphoric-local", [
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 6, "allow_anchors": True},
        {"literal": ","}, {"literal": "what"}, {"literal": "does"}, {"literal": "that"}, {"literal": "mean"},
    ], meaning_query(), 1.6, ignore=()),
    p("en:alias-claim:means", [
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 6},
        {"literal": "means"},
        {"kind": "anchor", "slot": "target"},
    ], alias_claim(), 1.25),
    p("en:alias-claim:is-word-for", [
        {"open_text": True, "slot": "surface", "capture": "literal:text", "min_tokens": 1, "max_tokens": 6},
        {"literal": "is"}, {"literal": "another", "optional": True}, {"literal": "word"}, {"literal": "for"},
        {"kind": "anchor", "slot": "target"},
    ], alias_claim(), 1.2),
]

pack = {
    "version": 1,
    "language": "en",
    "function_forms": sorted(set(function_forms)),
    "nonblocking_discourse_forms": sorted(set(nonblocking)),
    "contractions": [
        {"surface": "what's", "expansions": [
            {"tokens": ["what", "is"], "score": 0.0},
            {"tokens": ["what", "has"], "score": -0.18},
        ]},
        {"surface": "who's", "expansions": [
            {"tokens": ["who", "is"], "score": 0.0},
            {"tokens": ["who", "has"], "score": -0.18},
        ]},
        {"surface": "where's", "expansions": [
            {"tokens": ["where", "is"], "score": 0.0},
            {"tokens": ["where", "has"], "score": -0.18},
        ]},
        {"surface": "how's", "expansions": [
            {"tokens": ["how", "is"], "score": 0.0},
            {"tokens": ["how", "has"], "score": -0.18},
        ]},
        {"surface": "name's", "expansions": [
            {"tokens": ["name", "is"], "score": 0.0},
            {"tokens": ["name", "has"], "score": -0.2},
        ]},
        {"surface": "i'm", "expansions": [{"tokens": ["i", "am"], "score": 0.0}]},
        {"surface": "you're", "expansions": [{"tokens": ["you", "are"], "score": 0.0}]},
        {"surface": "we're", "expansions": [{"tokens": ["we", "are"], "score": 0.0}]},
        {"surface": "they're", "expansions": [{"tokens": ["they", "are"], "score": 0.0}]},
        {"surface": "can't", "expansions": [{"tokens": ["can", "not"], "score": 0.0}]},
        {"surface": "won't", "expansions": [{"tokens": ["will", "not"], "score": 0.0}]},
        {"surface": "don't", "expansions": [{"tokens": ["do", "not"], "score": 0.0}]},
        {"surface": "doesn't", "expansions": [{"tokens": ["does", "not"], "score": 0.0}]},
        {"surface": "didn't", "expansions": [{"tokens": ["did", "not"], "score": 0.0}]},
        {"surface": "isn't", "expansions": [{"tokens": ["is", "not"], "score": 0.0}]},
        {"surface": "aren't", "expansions": [{"tokens": ["are", "not"], "score": 0.0}]},
    ],
    "constructions": constructions,
}
pack["pack_hash"] = hashlib.sha256(canonical(pack).encode()).hexdigest()
out = Path(__file__).resolve().parents[1] / "cemm" / "form_packs" / "en.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
print(pack["pack_hash"])
