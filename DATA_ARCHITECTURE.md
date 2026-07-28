# CEMM Data Architecture — Native Semantic Spine

## 1. One linked authority graph

Authority may be split into files for review, but validation and import treat it as one graph. Every atom has one defining owner.

```text
base.json                         kernel operators/roles and universal foundations
conversation_foundation.json     conversation semantics, frames and learning contracts
domain files                     optional domain authority
reference forms                  language-specific structural evidence
training annotations             reviewed form-to-graph supervision
compiled form/language packs     deterministic generated artifacts
```

`conversation_foundation.json` is the sole owner of the native conversational frames and designation-learning contract. A sidecar semantic-spine authority file is forbidden because it would create duplicate ownership and order-sensitive import.

## 2. Persistent and transient classes

### Reviewed persistent authority

- atoms and semantic kinds;
- five-operator role contracts;
- reviewed designations;
- semantic-frame atoms and `rel:has_semantic_frame` links;
- learning-contract concepts and capability licensing;
- capabilities, dependencies and entitlements;
- rules/mechanisms;
- dimensions/domains/value links;
- explicit reference forms.

### Mutable persistent state

- observations;
- attributed claim occurrences and epistemic placements;
- admitted world facts and state timelines;
- compact frontiers and commit receipts;
- verified common ground;
- effect and operation-observation receipts.

### Transient cycle state

- semantic contributions;
- form, designation, reference and graph hypotheses;
- coverage receipts and settling factors;
- query closure/bindings;
- unbound learning plans;
- goals and transition previews;
- Response CSIR before Stage-21 ownership.

A pending learning obligation is dialogue state, not semantic authority. It contains a response-bound typed plan and expires or is invalidated on authority reload.

## 3. Semantic-frame data

A frame is an atom of kind `semantic_frame`:

```json
{
  "ref": "frame:event-learn",
  "kind": "semantic_frame",
  "metadata": {
    "semantic_frame": {
      "contribution_kind": "predicate",
      "ports_provided": ["predicate:event"],
      "ports_required": ["argument:subject", "argument:object"],
      "roles": [
        {"role_ref": "role:actor", "required": true, "filler_kinds": ["atom"]},
        {"role_ref": "role:object", "required": true, "filler_kinds": ["atom"]}
      ],
      "predicate": true,
      "replace_defaults": true,
      "kernel_operator_ref": "op:event",
      "score": 0.35
    }
  }
}
```

The semantic target links to the frame using ordinary reviewed relation authority:

```text
event:learn --rel:has_semantic_frame--> frame:event-learn
```

Frame metadata may define roles, ports, proposition-taking status and capability dependencies. It may not contain surface phrases, regexes, language-specific token arrays or executable Python handlers.

## 4. Learning-contract data

The designation-learning contract is a concept atom with validated metadata:

```json
{
  "ref": "contract:designation_learning",
  "kind": "concept",
  "metadata": {
    "learning_contract": {
      "goal_ref": "goal:acquire_designation",
      "capability_ref": "cap:learn",
      "commit_operator_ref": "op:designation",
      "answer_contract_ref": "contract:designation_target_answer",
      "label_type_ref": "label:lexical",
      "expected_target_kinds": [
        "concept", "entity", "event_type", "relation_type", "time",
        "state_dimension", "value", "label_type", "capability"
      ],
      "licensed_query_kinds": [
        "designation_learning", "meaning_query", "designation_query"
      ]
    }
  }
}
```

Capability licensing is explicit:

```text
cap:learn --rel:licenses_learning_contract--> contract:designation_learning
```

The contract is authority. A concrete `LearningPlan` is transient protocol state derived only after execution of one exact licensed query. Its identity includes the exact QueryStructure, query ref/kind, authority generation, contract, capability, commit operator, expected target kinds and expiry. It cannot be replayed after authority reload.

## 5. Designations and form behaviour

A designation states that a surface may denote a target in a language/context. It does not contain the target's grammatical frame.

```text
op:designation(
  target,
  label_type,
  surface,
  language,
  script,
  prior,
  preferred,
  context?
)
```

Composition is obtained from:

```text
designation target kind
+ optional reviewed semantic frame
→ bounded semantic contribution candidates
```

Language packs retain closed-class structure and morphology evidence. Open-class entries may carry `open_class`, lemma and training provenance, but no semantic target authority.

## 6. Explicit lexical publication

The foundation generator publishes only reviewed surfaces listed in source data. It must never turn `namespace:internal_ref` into a word by splitting the ref or replacing underscores.

Because the current pre-core does not yet map an inflected form to a lemma designation, the English bootstrap explicitly publishes a finite reviewed set such as:

```text
learn / learns / learned / learning → event:learn
mean / means / meant → event:define
know / knows / knew / known → rel:knows and event:know candidates
```

These are reviewed designation alternatives, not form-pack semantic ports. A future morphology resolver can reduce this finite list without changing semantic authority or the five-operator substrate.

Internal semantic relations such as `rel:has_semantic_frame` and `rel:licenses_learning_contract` are marked non-user-visible and receive no lexical designation.

## 7. Learned data

A newly learned synonym normally adds one reviewed/admitted designation fact. It does not require:

- a new operator;
- a new schema family;
- a form-pack regeneration;
- an automatically minted concept;
- a duplicate event/capability word entry.

On the next world-revision refresh, the designation index returns the target and the affordance index derives safe profiles from the target kind. Explicit frames remain generation-pinned reviewed authority.

## 8. Validation laws

Before import or activation, validate:

- unique atom ownership across the complete bundle;
- all atom, role, control-symbol and fact references;
- frame links target `semantic_frame` atoms;
- contribution kinds belong to the closed ABI;
- ports/roles/filler kinds stay within bounds;
- frame roles are licensed by the selected kernel operator;
- contract targets have exact required kinds;
- capability-to-contract licensing exists;
- contract target/query-kind sets are bounded;
- no active `semantic_port`, `learning_operation` or `resolve_designation` remains;
- no automatic internal-ref lexical publication exists;
- source generators are deterministic;
- compiled pack hashes and ABI receipts match source output.

## 9. Migration and cutover

The release migration changes sources of truth together:

1. add optional `op:event` complement roles `role:object` and `role:target`;
2. replace the conversation-foundation generator;
3. regenerate `conversation_foundation.json` as the single owner;
4. migrate English seed annotations from lexical semantic fields to semantic anchors;
5. add generic capability, proposition, definition, predication and reaction families;
6. update the v6 form generator replay and `function_forms` rule;
7. regenerate the form pack twice;
8. regenerate/migrate the language pack and grammar twice;
9. link and validate base plus conversation authority;
10. rebuild a temporary store and attest runtime activation;
11. run focused and complete tests before target copy.

Existing mutable stores are not silently rewritten. A deployment should rebuild from reviewed authority plus preserved admitted world evidence under an explicit migration policy.

## 10. Indexing and performance

ABI 1 adds no database table. It uses existing atom/relation/designation indexes and bounded, revision-pinned in-memory caches.

Normal turns must not perform:

- whole-store scans;
- per-designation regex matching;
- authority revalidation;
- pack regeneration;
- semantic-frame discovery outside bounded target lookups;
- persistent storage of transient contribution candidates.

A future materialized affordance index is permitted only if profiling demonstrates a bottleneck. It must remain derived, generation-keyed and rebuildable from exact authority.


## Realization vocabulary isolation

Realization grammar tokens are output-only and must never be fed back into pre-core form classification. A language pack may retain realization grammar for output, but that vocabulary is not an input-side lexical authority and is never imported into the designation or form indexes.
