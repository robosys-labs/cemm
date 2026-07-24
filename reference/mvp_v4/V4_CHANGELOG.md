# v4 Changelog

## Architectural changes from v3

1. Replaced closed whole-program semantic classification with open structured graph prediction.
2. Added independent application-slot, operator and role-pointer neural heads.
3. Added N-best exact candidate compilation and recurrent inhibition/settling.
4. Removed combined-document semantic class dependence; document interpretation is clause-compositional.
5. Added structured semantic rule induction with variables/existentials.
6. Added provisional rule candidate store, semantic deduplication, evidence threshold and promotion.
7. Added explicit authority activation/reload before promoted rules can execute.
8. Removed the hard-seeded mother-in-law decomposition rule from family knowledge.
9. Added reviewed unknown-vocabulary acquisition using opaque atoms + exact designation facts + the same structured interpreter.
10. Separated semantic-authority atoms from mutable world-occurrence atoms for authority hashing.
11. Preserved v3 self-state, workspace, identity/designations, anti-bloat inference and semantic-pointer NLG.
12. Expanded regression coverage to 37 passing tests.
