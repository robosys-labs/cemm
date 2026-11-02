# G3 effect and role grounding v2 — prospective normalization study

## Question and prior evidence

The complete v1 study returned `REVISE_EFFECT_ROLE_GROUNDING` in every law/seed
condition. Its raw forecasts, scored failures and independent saved-record audit
remain immutable. Seed 7 failed to acquire one new SET word. All other seeds
failed conditional probability quality and bilingual probability agreement;
some also failed retained NLL, and seed 37 regressed on exact retained world and
action predictions. Passing goal choice in some seeds is not G3 completion.

TRAIN-only diagnostics found that appending zero SET logits to inherited raw
contact logits made an arbitrary common contact-logit shift determine a new
effect-family prior. Wrong-action finite native likelihood tails then received
more responsibility than a correct SET action with negligible prior. This is
credit assignment and probability scale, not floating-point underflow.
Normalization is a narrow hypothesis; its ability to repair the broader
probability and retention failures remains unverified.

## Single model change

Preserve the 92-scalar state dictionary: every one of the 88 accepted parent
scalars is copied exactly and the four new scalars start at zero. At every
forward call use:

```python
contact = contact_logits.log_softmax(-1) + log(2)
action_logp = cat((contact, set_logits), -1).log_softmax(-1)
```

Initialization assigns half the probability to each effect family and one
quarter to each SET direction, while retaining the parent's conditional
contact distribution. The learned SET scores remain free, so these family
probabilities are not fixed after training. No literal word chooses a meaning,
effect or role. The four generic alternatives remain contact(A,B), contact(B,A),
SET(A,1), SET(B,1). All 562 acquired native world parameters remain frozen.

## Evidence and budget

The four v1 training files are copied byte-for-byte: observed teaching,
observed rehearsal, parser-only labels and the collision-safe lexical identity
registry. The grounded learner sees the same 16 teaching endpoints plus 1,152
old TRAIN rehearsal forecasts. Gold action labels enter only the parser
control. TRAIN-withheld new-word/VOS cells were opened in v1 and are expressly
not described as fresh lexical cells.

Five seeds (7, 11, 23, 37, 53), three arms and 15 fits remain fixed. Each fit
uses Adam at .02, 256 updates, gradient clip 5, and equally weighted teaching
and rehearsal mean losses. The 400-second per-fit CPU ceiling and complete
Python/PyTorch/NumPy float64 one-thread runtime are unchanged. There is one
attempt per stage, zero retries, no checkpoint selection and no additional
training observations. Same nominal budgets do not imply equal consumed
compute. The text-only model still has 1,048 parameters versus 92 for the
grounded and parser models.

The current text-only checkpoints and every fit-report field except resource
timing must exactly reproduce v1. This is required before archived text-only
forecasts can serve as the opened-bank control; the receipt is rechecked before
collection and scoring. A fresh normalized parser is collected for the new
challenge. The opened parser is explicitly the archived v1 descriptive baseline.

## Fresh challenge and opened regressions

Fresh structures are `hub_return4` (four events/four entities) and
`triangle_fan5` (five events/five entities). Ordered structures and unordered
participant multigraphs are disjoint from 70 source-defined prior recipe
entries, including opened v1. Identity/challenge seeds are 20261102501 and
20261102502. Three layouts rotate within each episode. Physical modes,
anchors, role reversals, SET/contact phases, context conditions and final
alternatives retain the same factorial coverage.

Each law has 1,536 episodes, 6,912 forecast points (6,144 identifiable and 768
ambiguous), 384 same-prefix alternative groups and 1,536 supplied goals. NAND
has 558 effect-sensitive goals; NOR has 702. Goals include impossible joint
targets while spectator coordinates remain fixed, plus both SET-required and
contact-required decisions.

The frozen raw inventory has 100 trace files plus one lexical identity receipt:

| Evidence | Saved forecast rows |
| --- | ---: |
| Fresh grounded canonical/masked, parser and text-only | 276,480 |
| Six historical language banks, grounded canonical | 131,520 |
| Opened v1 challenge, current grounded canonical/masked | 138,240 |
| **Total** | **546,240** |

These are dependent factorial observations and control views, not independent
trials. Actual prefix readings arrive after each prediction; this is not an
autonomous rollout. The v1 TRAIN-only diagnostic exposures remain separately
counted and are never portrayed as additional fresh evidence.

## Frozen decision

Every original v1 numeric criterion and stratum remains unchanged. The fresh
bank must meet all identifiable, probability, ambiguity, trajectory, reversal,
action, bilingual, goal and causal-control gates in every law/seed. All six
historical banks retain the original exact world/action and mean-NLL gates;
SET probability is never renormalized away.

The opened v1 bank must also meet the unchanged candidate gates. Additionally,
canonical forecasts must have zero formerly correct identifiable-world
regressions and zero formerly correct globally taught action regressions.
Actual-world changes on unresolved ambiguous points and masked control changes
remain fully reported. They are not reclassified as identifiable competence.

All valid scientific failures produce all ten reports and a complete `REVISE`
decision. Malformed evidence, missing rows, runtime/provenance failures, mutation
or failed exact control reproduction stop execution. Only every prospective
check passing permits `DEVELOPMENT_G3_COMPLETE` and progression to G4.

## Publication, audit and scope

The complete failed v1 result must be published before v2 preparation. Bind its
full data, fits, raw forecasts, scored results and diagnostic evidence. Publish
v2 source/data/runtime before fitting, all actual weights before collection,
and all raw forecasts before scoring. Preparation alone imports the generator;
grounded training reads only its observed tapes. Every output directory is
exclusive and historical bytes are rechecked at each stage.

A separate standard-library auditor checks saved evidence before parsing
evaluator targets, then recomputes the declared decision arithmetic without
running a model or the original scorer. This is independent arithmetic within
the same team, not independent challenge custody.

Formal scientific admission remains open. Development G3 is bounded to this
two-mode world, supplied identities, finite action alternatives, controlled
three-token forms and finite supplied goals. It does not establish unrestricted
natural-language understanding, natural-language goal parsing or general
planning. The inclusive 2,000-line target remains unmet. This isolated study
does not change production runtime, semantic authority or any ABI.
