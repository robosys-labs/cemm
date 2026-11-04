# G5 v7 pre-fit physical-likelihood correction — 2026-11-04

**Status: pre-fit implementation erratum; no v7 TEST generated/scored.**
Original experiment protocol was frozen in \`4bf1e61\`. An audit of the
unchanged v6 code and v7 generator found a physically consequential
likelihood discrepancy *before accepting any v7 fit*:

- The simulator inverts the **observed binary selected payoff** with
  probability e(source), independently of the latent meaning.
- The v6 likelihood treats e as swapping the two meaning-specific
  payoff forecasts: ((1-e)a + e b, (1-e)b + e a).
- The correct Bernoulli observation likelihood is
  (e + (1-2e)a, e + (1-2e)b). These coincide only where a+b=1.
  For a=b=1, the old model predicts a certain observed 1 regardless
  of sensor noise, contradicting the generator's observed bit flip.
- The v7 model now feeds the **correct likelihood-transformed row**
  into the unchanged v6 temporal recursion with zero further
  exception mixing. It still learns only h,e_A,e_B, with no gold
  meaning labels, from exactly the same selected-payoff tape.
- To isolate the effect of source conditioning from correcting the
  old emission equation AND from refitting on new outcomes, add a
  **physics-matched, source-neutral two-scalar control**. Fit `h,e`
  once on the identical NAND TRAIN selected-payoff histories with
  `h=(.05,.15,.35,.5)`, `e=(.01,.03,.05,.1,.2,.3)`;
  tie-break toward smaller values. No gold labels. That shared error
  grid spans both source-specific grids and uses only 24 candidates
  against the source model's 64. Frozen original v6 h=.15/e=.1
  (uncorrected emission) and TRAIN-calibrated G5 rule remain.
  The same predeclared stationary NLL, immediate stable-B Brier,
  net utility and worst-seed metrics compare the physics-matched
  control. This is a capacity-matched negative control, not a new
  target architecture or a post-test fit.

The initial automated invariant run on the first implementation is
**not an accepted fit** even if its software tests pass; any numbers from
that earlier source are only pre-fit diagnostics. All accepted fits and
future raw evidence must name the revised source commit. No hidden
challenge inspection, post-score tuning or replacement of the v6
historical result is authorized. Physical menus remain inherited and
G5 scientific admission remains NOT_ADMITTED.
