"""Generate the split authority data files from the legacy monolith.

This script reads data/authority.json, splits it into three reviewed owners
(kernel, conversation, state_operations), a manifest, and writes them with
correct SHA-256 hashes. Run once to produce the data split.
"""
import json
from pathlib import Path

from cemm_authoritative_hybrid.canonical import sha256_governed_text

ROOT = Path(__file__).resolve().parents[1]
AUTH_DIR = ROOT / "data" / "authority"
AUTH_DIR.mkdir(parents=True, exist_ok=True)

legacy = json.loads((ROOT / "data" / "authority.json").read_text(encoding="utf-8"))

atoms = {a["ref"]: a for a in legacy["atoms"]}
designations = legacy["designations"]
event_sigs = legacy["event_signatures"]
rules = legacy["rules"]
capabilities = legacy["capabilities"]
permissions = legacy["permissions"]
adapters = legacy["adapters"]
operator_roles = legacy["operator_roles"]
value_dims = legacy["value_dimensions"]

# --- Kernel: core semantic operators, base kinds, participants ---
kernel_atom_refs = [
    "participant:user", "participant:system",
    "concept:person", "concept:digital_agent", "concept:job_role",
    "label:name", "label:lexical",
    "rel:has_capability", "rel:has_role", "rel:likes", "rel:owns",
    "cap:query", "cap:respond",
    "adapter:memory",
    "entity:book",
]
kernel_atoms = [atoms[r] for r in kernel_atom_refs if r in atoms]
kernel_designations = [d for d in designations if d["target"] in set(kernel_atom_refs)]
kernel_event_sigs = []
kernel_rules = []
kernel_caps = {k: v for k, v in capabilities.items() if k in set(kernel_atom_refs)}
kernel_perms = [p for p in permissions if p[0] in set(kernel_atom_refs)]
kernel_adapters = [a for a in adapters if a in set(kernel_atom_refs)]
kernel_value_dims = {}

kernel = {
    "owner": "kernel",
    "atoms": kernel_atoms,
    "designations": kernel_designations,
    "event_signatures": kernel_event_sigs,
    "rules": kernel_rules,
    "capabilities": kernel_caps,
    "permissions": kernel_perms,
    "adapters": kernel_adapters,
    "operator_roles": operator_roles,
    "value_dimensions": kernel_value_dims,
    "transitions": [],
    "source": {"origin": "legacy-authority-json", "reviewed": True},
}

# --- Conversation: conversation events, greetings, farewells, speech, learning ---
conv_atom_refs = [
    "event:conversation_session", "event:turn",
    "event:greeting", "event:farewell",
    "event:learn_alias", "event:say", "event:leave", "event:teach",
    "cap:learn_alias",
    "permission:write_alias",
    "entity:alice", "entity:bob", "entity:carol", "entity:mary",
    "rel:mother_in_law", "rel:has_partner",
]
conv_atoms = [atoms[r] for r in conv_atom_refs if r in atoms]
conv_designations = [d for d in designations if d["target"] in set(conv_atom_refs)]
conv_event_sigs = [es for es in event_sigs if es["event_type"] in set(conv_atom_refs)]
conv_rules = [r for r in rules]
conv_caps = {k: v for k, v in capabilities.items() if k in set(conv_atom_refs)}
conv_perms = [p for p in permissions if p[0] in set(conv_atom_refs) or p[2] in set(conv_atom_refs)]
conv_adapters = [a for a in adapters if a in set(conv_atom_refs)]
conv_value_dims = {}

conversation = {
    "owner": "conversation",
    "atoms": conv_atoms,
    "designations": conv_designations,
    "event_signatures": conv_event_sigs,
    "rules": conv_rules,
    "capabilities": conv_caps,
    "permissions": conv_perms,
    "adapters": conv_adapters,
    "operator_roles": {},
    "value_dimensions": conv_value_dims,
    "transitions": [],
    "source": {"origin": "legacy-authority-json", "reviewed": True},
}

# --- State Operations: state dimensions, values, transitions, state events ---
state_atom_refs = [
    "dim:operational_status", "dim:availability", "dim:power",
    "dim:marital_status", "dim:admissibility",
    "value:operating_normally", "value:online", "value:offline",
    "value:on", "value:off", "value:married",
    "value:available", "value:unavailable",
    "value:enabled", "value:disabled",
    "event:set_state",
    "cap:set_state",
    "permission:set_state",
    "adapter:state",
    "entity:server", "entity:lamp", "entity:door",
    "entity:router", "entity:light",
]
state_atoms = [atoms[r] for r in state_atom_refs if r in atoms]
state_designations = [d for d in designations if d["target"] in set(state_atom_refs)]
state_event_sigs = [es for es in event_sigs if es["event_type"] in set(state_atom_refs)]
state_rules = []
state_caps = {k: v for k, v in capabilities.items() if k in set(state_atom_refs)}
state_perms = [p for p in permissions if p[0] in set(state_atom_refs) or p[2] in set(state_atom_refs)]
state_adapters = [a for a in adapters if a in set(state_atom_refs)]
state_value_dims = {k: v for k, v in value_dims.items() if k in set(state_atom_refs)}

state_operations = {
    "owner": "state_operations",
    "atoms": state_atoms,
    "designations": state_designations,
    "event_signatures": state_event_sigs,
    "rules": state_rules,
    "capabilities": state_caps,
    "permissions": state_perms,
    "adapters": state_adapters,
    "operator_roles": {},
    "value_dimensions": state_value_dims,
    "transitions": [],
    "source": {"origin": "legacy-authority-json", "reviewed": True},
}

# --- Write owner files ---
owners_meta = []
for name, data in [
    ("kernel", kernel),
    ("conversation", conversation),
    ("state_operations", state_operations),
]:
    p = AUTH_DIR / f"{name}.json"
    p.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
    sha = sha256_governed_text(p)
    owners_meta.append({"name": name, "path": f"{name}.json", "sha256": sha})

manifest = {
    "generation": "authority-v1-2026-07-29",
    "abi_version": 1,
    "owners": owners_meta,
}
(AUTH_DIR / "manifest.json").write_text(
    json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
)

print("Authority split generated successfully.")
for o in owners_meta:
    print(f"  {o['name']}: {o['sha256'][:16]}...")
