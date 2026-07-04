# Semantic Compression And Unsupervised Learning

Purpose: define how CEMM can learn fundamental atoms and relations from utterances and transcripts without becoming a huge database.

## 1. Core Principle

CEMM should not store experience.

CEMM should compile experience.

The raw path:

```text
utterance/transcript
-> working UOL graph
-> graph patch candidates
-> construction/predicate/concept consolidation
-> keep only useful traces
```

The durable result:

```text
stronger atom
better ports
better predicate schemas
better causal affordances
better pragmatic operators
```

## 2. Brain-Like Memory Separation

Complementary Learning Systems argues for fast episodic learning plus gradual semantic consolidation. CEMM should mirror this separation:

```text
fast path: capture graph trace
slow path: consolidate repeated structure
```

See [McClelland, McNaughton, and O'Reilly, 1995](https://pubmed.ncbi.nlm.nih.gov/7624455/) and [O'Reilly et al., 2011](https://pubmed.ncbi.nlm.nih.gov/22141588/).

## 3. What Gets Stored

Do not store:

```text
every sentence
every graph
every paraphrase
every repeated fact
```

Store:

```text
new atom
new alias
new port
new acceptable predicate
new causal relation
new contradiction boundary
new source reliability update
new pragmatic operator
high-value exemplar
```

## 4. Self-Supervised Signals In Chat Logs

Human-human chat logs contain weak supervision:

| Signal | What CEMM Learns |
|---|---|
| question-answer pairs | expected answer target and form |
| correction | replacement graph patch |
| confirmation | support for interpretation |
| disagreement | contradiction or scope boundary |
| repetition | construction support |
| paraphrase | alias/same_as relation |
| repair request | ambiguity marker |
| response delay or frustration | pragmatic failure |
| topic shift | segmentation and salience |
| narrative sequence | temporal and causal chains |

## 5. Candidate Extraction Without Supervision

Unsupervised extraction loop:

```text
1. Segment turns into candidate meaning groups.
2. Build temporary UOL graphs.
3. Cluster graph fragments by shape and surface distribution.
4. Find repeated predicate-argument forms.
5. Induce candidate constructions.
6. Induce ports from repeated argument positions.
7. Induce causal affordances from repeated before/after patterns.
8. Score by recurrence, source diversity, repair rate, and usefulness.
9. Promote compact structures.
10. Decay redundant traces.
```

## 6. Compression Score

A graph fragment is worth promoting when:

```text
compression_gain =
  traces_explained
  + future_prediction_gain
  + repair_reduction
  + source_diversity
  + causal_usefulness
  - complexity_cost
  - contradiction_cost
```

Promote only when compression gain is positive.

This prevents memory bloat.

## 7. Example: Leader And President

Observed:

```text
president is a leader
president leads a country
leader of the team
head of government
current president of X
former president of X
```

Consolidated:

```text
leader:
  kind: role_concept
  ports:
    holder: person/group
    domain: group/org/country
  predicates:
    leads(domain)
    represents(domain)
    directs(domain)
  causal_affordances:
    decision -> domain_state_change

president:
  inherits: leader
  kind: office_role
  ports:
    holder: person
    domain: country/org
    time_scope: current/former/future
  freshness:
    current_holder requires fresh evidence
```

Discard most utterance graphs after this consolidation.

## 8. Dynamic Atom Deepening

Every promoted atom can be recursively explained through more fundamental atoms:

```text
president -> leader -> authority -> enables(govern) -> causes(policy_change)
```

As CEMM grows:

```text
atoms get deeper
ports get sharper
predicate compatibility improves
causal explanation improves
working graph construction gets faster
```

This is the path to a stronger runtime operational graph network.

## 9. Source Ingestion

CEMM can learn from:

```text
dictionaries
Wikipedia
large LLMs
user teaching
chat logs
documents
tools/APIs
```

But every source becomes:

```text
SourceAtom
EvidenceAtom
PermissionAtom
GraphPatch
```

Large LLMs are hypothesis generators, not truth authorities.

Dictionaries are strong for lexical meaning.

Wikipedia is useful for broad entity/world knowledge with source and time policy.

User teaching is strong for local definitions, preferences, and private context, but must retain source scope.

## 10. Implementation Direction

Add:

```text
cemm/learning/graph_patch_extractor.py
cemm/learning/concept_consolidator.py
cemm/learning/construction_inducer.py
cemm/learning/predicate_schema_inducer.py
cemm/learning/causal_affordance_inducer.py
cemm/memory/concept_lattice.py
cemm/memory/episodic_trace_store.py
```

## 11. Design Rule

Memory is not the record of everything CEMM has seen.

Memory is the compressed structure CEMM can use to understand the next thing better.
