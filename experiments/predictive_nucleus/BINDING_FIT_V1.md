# Binding v1: completed fit, before collection

Source/data commitment was published at `cd1c1fd2663677121f7ec81ffa08e521931ef71f`
before fitting. Both source-head CI checks passed: invariant run 41226968556 and
source snapshot 41226968579. All fifteen fits completed their 256 updates with
1,024 observed outcomes per update; zero retries or checkpoint selection.

The complete actual JSON checkpoint bundle, including every state, initial/final
fingerprint, training curve and resource report, is published as three ordered
binary transport pieces. Concatenating `.part0`, `.part1`, `.part2` yields exactly
33,980 bytes, SHA-256
`424d68b973b7358c08ca0c4c21351497e458df416c0447858d43a88d4d8d1220`.
This is a transport representation of the actual weights, not a deterministic
recipe offered instead of weights. The collection workflow verifies all three
piece hashes and the reconstructed bundle before using it. The transport-only
workflow adaptation changes no bound source, data, model, protocol or threshold.

```sh
cat experiments/predictive_nucleus/data/binding-fit-v1/checkpoints.json.xz.part{0,1,2} > experiments/predictive_nucleus/data/binding-fit-v1/checkpoints.json.xz
```

Total fit-stage CPU/wall: 62.030222 / 62.046987 seconds; peak RSS 337,496 KiB.
Costs include shared native-cache preparation and stage overhead. They do not
establish matched consumed compute across arms.

| Seed | GRU last recorded training NLL | Factor | Additive |
|---|---:|---:|---:|
| 7 | 0.003589 | 0.295547 | 0.389248 |
| 11 | 0.004357 | 0.371668 | 0.444056 |
| 23 | 0.004301 | 0.368880 | 0.345138 |
| 37 | 0.005489 | 0.296560 | 0.444730 |
| 53 | 0.004233 | 0.277887 | 0.389598 |

The curves record each listed loss before that update, not a fresh post-fit
training evaluation. The factor model fits these observed outcomes much worse
than the GRU. This is not yet a held-challenge result or proof that its function
class is incapable. All seeds, including poor fits, proceed unchanged to the
single registered collection. No new fit or retuning is authorized by this record.

G3 and all original scientific gates remain open. Previous models, datasets,
results and decisions are unchanged.
