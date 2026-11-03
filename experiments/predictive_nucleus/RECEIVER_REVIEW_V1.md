# Corrections to the G4 receiver v1 decision

The original KEEP survives a checkpoint replay. The ten published policies
reproduce all 207,360 recorded decisions and action values, and all 46,440
selected TRAIN rewards agree with the archived physical endpoints. Two
adversarial records reveal a verification gap. The original arithmetic scorer
accepts an action inconsistent with its saved value vector and a paid-silent
row with a reply-dependent value vector. The strengthened replay rejects both.
Neither defect was found in the published records.

Three qualifications change how the original result should be read.

1. The 96 held-out cases comprise 63 distinct physical menus with 96 menu–goal
   combinations. NAND contributes 45 menus across eight parent lineages. NOR
   contributes 18 across four. Thirty-three menus each carry two goals. There
   are 6,912 distinct communication scenarios, each evaluated at five inherited
   model seeds.
2. The so-called unreadable channel carries a full bit. In the distinct unknown
   cases, `unregistered-0` appears 384 times and always means zero;
   `unregistered-1` appears 384 times and always means one. The frozen decoder
   treats both as unresolved. Its 192 units of unproductive fees are real for
   this decoder. The experiment did not evaluate erasure of information from
   the underlying wire. Before querying, these cases remain indistinguishable
   from their useful counterparts on the receiver's inputs.
3. A post-score rule with supplied source polarity, public opportunity, focus,
   age and a fixed cost threshold reproduces all 34,560 queries and physical
   choices. This comparison supplies the source conventions; the receiver
   learned its corrections from outcomes. Both achieve the same observed
   utility. The original literal shortcut was source blind.

[Reconstruction and counts](results/communication-v1/receiver-review-v1.json) ·
[Replay implementation](audit_receiver_v1.py) ·
[Original frozen decision](COMMUNICATION_DECISION_V1.md).
