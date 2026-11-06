# G5 physical-answer query qualification

The TRAIN-only protocol at `ae0924e` ran on November 6 using the committed native receipt file at `8bbd710`. The new 64-line policy computes expected reward after a possible physical observation by summing all endpoint outcomes. Its separate update function conditions on the physical endpoint after purchase. Eight synthetic tests pass, including indistinguishable role answers, equal rewards, unavailable and expensive queries, impossible observations, normalization roundoff and arithmetic overflow. [Protocol](PHYSICAL_QUERY_PREFLIGHT_V1.md) · [Policy](physical_query_v1.py).

The native qualification contains all 960 declared policy evaluations. Eight utterance pairs from the original 16 teaching rows are evaluated in both delivery orders by five frozen worlds, giving 80 dependent ordered contexts. Every condition receives the same zero-cost first receipt. The reset condition discards it, while the retained condition uses its posterior. The query is for the second demonstration. Two complete executions produced byte-identical results, and the expected-utility formula agreed with exhaustive Bayesian updating within 2.22e−16. [All observations and policy decisions](results/physical-query-preflight-v1.json).

| Identity-reward condition | Second queries at .05 fee | Mean expected reward before query | Mean expected reward after observation | Mean expected query value |
|---|---:|---:|---:|---:|
| Reset prior | 80 / 80 | .250000 | .624145 | .374145 |
| Retained first receipt | 40 / 80 | .499693 | .749317 | .249624 |

Retaining the first receipt increased the expected value of a second demonstration on 40 contexts and decreased it on 40. The signed mean change was −.124521, with a range of −.499024 to +.249466. The policy bought the 40 second observations that distinguish the remaining candidates in the bit-changing examples. On the purchased observations, the largest posterior weight became .996700–.998883.

The other 40 contexts retained the all-ones role ambiguity. Their predicted observation value was .00023897–.00047438, below the .05 fee. Small native approximation differences yield a nonzero expected value in these examples. Both role hypotheses survive in the retained prior. A stopped query therefore remains an unresolved interpretation when the available observation cannot justify its price.

All .75-fee, unavailable and equal-reward cases bought zero observations. Those controls follow algebraically from the supplied reward tables and fees. The identity table values correct identification of the event-local menu hypothesis after a passive demonstration. This result measures expected identification value and marginal second-query decisions on reused TRAIN data. Realized physical utility, matched final correctness, calibrated confidence, fresh-instance transfer, source conflict and cross-process persistence still require prospective measurement. Candidate roles were aligned only where the physical action tuples were identical.

Reproduce with `python -m experiments.predictive_nucleus.physical_query_preflight_v1` and run the synthetic guards with `python -m unittest experiments.predictive_nucleus.tests.test_physical_query_v1`. The driver evaluates the policy directly from pinned observations. [Driver](physical_query_preflight_v1.py).
