# CEMM v3.4.2 foundation repair package

Target repository: `robosys-labs/cemm`  
Audited baseline commit: `b0f6b896a26906a56113f905f18167fb48d74a74` (`Hack fix!`)

This is a replacement overlay for the v3.4 substrate failures:

- removes domain/chat vocabulary from Python boot code;
- introduces versioned language-neutral foundation data;
- moves lexicalization, constructions and realization into language packs;
- adds a canonical semantic fact store and real critical commit path;
- compiles learned material by schema family;
- adds bounded relation/default/causal inference;
- replaces English `content_kind` rendering switches with generic clause templates.

## Apply

```bash
python apply_patch.py C:/dev/cemm
```

All replaced files are backed up under:

```text
C:/dev/cemm/.cemm_patch_backups/<timestamp>/
```

## Validate in the repository

```bash
python -m compileall cemm
pytest -q
python -m cemm --chat
python -m cemm.web_demo --debug
```

## Important boundary

The overlay has been syntax-compiled and its JSON/data tests run in the artifact
environment. The full repository test suite could not be executed here because
the complete checkout is not mounted in the artifact runtime. Apply it on a
branch and resolve any exact API drift reported by the repository suite.
