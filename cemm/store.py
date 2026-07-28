"""Semantic store with exact authority, mutable world and epistemic separation."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path

from cemm.constants import DDL, SCHEMA_VERSION
from cemm.authority import load_documents, validate_documents
from cemm.semantic_contributions import SemanticAffordanceIndex
from cemm.model import (
    AmbiguousReferent,
    Fact,
    canonical,
    isexist,
    isvar,
    lit,
    norm_text,
    now,
    stable,
)


class Store:
    SNAP = (
        "atoms",
        "operator_roles",
        "applications",
        "bindings",
        "observations",
        "claims",
        "claim_occurrences",
        "epistemic_placements",
        "proof_links",
        "rules",
        "reference_forms",
        "control_symbols",
    )

    def __init__(self, path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        tables = {str(row[0]) for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if tables and "schema_meta" not in tables:
            populated = any(
                self.db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                for table in ("atoms", "applications", "claims", "generations")
                if table in tables
            )
            if populated:
                self.db.close()
                raise RuntimeError(
                    "CEMM store schema is pre-v1-final and is intentionally unsupported; rebuild the store from authority/world evidence"
                )
        self.db.executescript(DDL)
        version = self.db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        if version and str(version[0]) == "2" and SCHEMA_VERSION == "3":
            columns = {
                str(row[1]) for row in self.db.execute("PRAGMA table_info(rules)")
            }
            if "definition_ref" not in columns:
                self.db.execute("ALTER TABLE rules ADD COLUMN definition_ref TEXT")
            self.db.execute(
                "UPDATE schema_meta SET value=? WHERE key='schema_version'",
                (SCHEMA_VERSION,),
            )
            self.db.commit()
            version = self.db.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
        if not version or str(version[0]) != SCHEMA_VERSION:
            raise RuntimeError(f"unsupported CEMM schema version: {version[0] if version else None}")
        if not self.db.execute("SELECT 1 FROM generations").fetchone():
            self.db.execute(
                "INSERT INTO generations VALUES(1,NULL,?,?,?)",
                (now(), "initial", hashlib.sha256(b"initial").hexdigest()),
            )
            self.db.commit()

    @property
    def generation(self):
        return int(self.db.execute("SELECT max(generation) FROM generations").fetchone()[0])

    def begin(self, reason, *, expected_world_revision=None):
        if expected_world_revision is not None:
            current = self.revisions()["world_revision"]
            if int(expected_world_revision) != current:
                raise RuntimeError(f"world revision CAS failed: expected {expected_world_revision}, found {current}")
        generation = self.generation + 1
        self.db.execute(
            "INSERT INTO generations VALUES(?,?,?,?,?)",
            (generation, generation - 1, now(), reason, "pending"),
        )
        return generation

    def finish(
        self,
        generation,
        *,
        cycle_ref="maintenance",
        stage=13,
        expected_world_revision=None,
        world_delta=False,
        observation_delta=False,
        discourse_delta=False,
        effect_delta=False,
        payload=None,
    ):
        """Finish one generation using an incremental receipt, never a full-store scan."""
        revisions = self.revisions()
        if expected_world_revision is not None and int(expected_world_revision) != revisions["world_revision"]:
            raise RuntimeError(
                f"world revision CAS failed: expected {expected_world_revision}, found {revisions['world_revision']}"
            )
        parent = self.db.execute(
            "SELECT content_hash FROM generations WHERE generation=?", (int(generation) - 1,)
        ).fetchone()
        material = payload if payload is not None else self._generation_material(int(generation))
        payload_hash = hashlib.sha256(
            canonical((str(parent[0]) if parent else "", int(generation), material)).encode()
        ).hexdigest()
        self.db.execute(
            "UPDATE generations SET content_hash=? WHERE generation=?",
            (payload_hash, int(generation)),
        )
        next_revisions = dict(revisions)
        for key, changed in (
            ("world_revision", world_delta),
            ("observation_revision", observation_delta),
            ("discourse_revision", discourse_delta),
            ("effect_revision", effect_delta),
        ):
            if changed:
                next_revisions[key] += 1
        self.db.execute(
            "UPDATE revision_state SET world_revision=?,discourse_revision=?,observation_revision=?,effect_revision=? WHERE singleton=1",
            (
                next_revisions["world_revision"],
                next_revisions["discourse_revision"],
                next_revisions["observation_revision"],
                next_revisions["effect_revision"],
            ),
        )
        receipt_ref = stable("commit-receipt", cycle_ref, stage, generation, payload_hash, next_revisions)
        self.db.execute(
            "INSERT OR REPLACE INTO commit_receipts VALUES(?,?,?,?,?,?,?,?)",
            (
                receipt_ref,
                cycle_ref,
                int(stage),
                expected_world_revision,
                next_revisions["world_revision"],
                int(generation),
                payload_hash,
                now(),
            ),
        )
        return {
            "receipt_ref": receipt_ref,
            "generation": int(generation),
            "payload_hash": payload_hash,
            "revisions": next_revisions,
            "stage": int(stage),
        }

    def revisions(self):
        row = self.db.execute("SELECT * FROM revision_state WHERE singleton=1").fetchone()
        return {
            "world_revision": int(row["world_revision"]),
            "discourse_revision": int(row["discourse_revision"]),
            "observation_revision": int(row["observation_revision"]),
            "effect_revision": int(row["effect_revision"]),
        }

    def _generation_material(self, generation):
        material = []
        for table in (
            "atoms", "applications", "observations", "claims", "claim_occurrences",
            "epistemic_placements", "rules", "rule_candidates", "frontiers"
        ):
            columns = [row[1] for row in self.db.execute(f"PRAGMA table_info({table})")]
            if "generation" not in columns:
                continue
            rows = self.db.execute(
                f"SELECT * FROM {table} WHERE generation=? ORDER BY 1", (generation,)
            ).fetchall()
            if rows:
                material.append((table, [dict(row) for row in rows]))
        return material

    def snapshot_hash(self):
        material = []
        for table in self.SNAP:
            columns = [
                item[1]
                for item in self.db.execute(f"PRAGMA table_info({table})")
                if item[1] not in {"observed_at", "created_at", "generation"}
            ]
            rows = self.db.execute(
                f"SELECT {','.join(columns)} FROM {table} ORDER BY {columns[0]}"
            ).fetchall()
            material.append((table, [dict(row) for row in rows]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()

    def authority_hash(self, upto_generation=None):
        cutoff = self.generation if upto_generation is None else int(upto_generation)
        material = []
        for table in ("operator_roles", "reference_forms", "control_symbols"):
            columns = [item[1] for item in self.db.execute(f"PRAGMA table_info({table})")]
            rows = self.db.execute(
                f"SELECT {','.join(columns)} FROM {table} ORDER BY {columns[0]}"
            ).fetchall()
            material.append((table, [dict(row) for row in rows]))
        for table in ("atoms", "rules"):
            columns = [
                item[1]
                for item in self.db.execute(f"PRAGMA table_info({table})")
                if item[1] != "generation"
            ]
            where = "generation<=?" + (
                " AND authority_scope='authority'" if table == "atoms" else ""
            )
            rows = self.db.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {where} ORDER BY {columns[0]}",
                (cutoff,),
            ).fetchall()
            material.append((table, [dict(row) for row in rows]))
        rows = self.db.execute(
            """SELECT a.app_ref,a.operator_ref,b.role_ref,b.filler_kind,b.filler_value,
                      c.stance,c.authority_status
               FROM applications a
               JOIN bindings b ON b.app_ref=a.app_ref
               JOIN claims c ON c.app_ref=a.app_ref
               JOIN observations o ON o.observation_ref=c.observation_ref
               WHERE a.generation<=?
                 AND o.source_ref IN('seed','reviewed_acquisition')
                 AND c.authority_status IN('reviewed','promoted')
               ORDER BY a.app_ref,b.role_ref,b.ordinal,c.stance""",
            (cutoff,),
        ).fetchall()
        material.append(("seed_semantics", [dict(row) for row in rows]))
        definitions = self.db.execute(
            "SELECT observation_ref,surface,packet,generation FROM observations "
            "WHERE source_ref='reviewed_definition' AND generation<=? "
            "ORDER BY observation_ref",
            (cutoff,),
        ).fetchall()
        material.append(("reviewed_definition_graphs", [dict(row) for row in definitions]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()

    def exact(self, table, columns, values, keys, ignore=()):
        try:
            self.db.execute(
                f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in values)})",
                values,
            )
        except sqlite3.IntegrityError:
            key_values = [values[columns.index(key)] for key in keys]
            row = self.db.execute(
                f"SELECT * FROM {table} WHERE " + " AND ".join(f"{key}=?" for key in keys),
                key_values,
            ).fetchone()
            if not row:
                raise
            for column, value in zip(columns, values):
                if column not in ignore and row[column] != value:
                    raise ValueError(f"immutable conflict {table}:{key_values}:{column}")

    def atom(self, ref):
        return self.db.execute("SELECT * FROM atoms WHERE ref=?", (ref,)).fetchone()

    def authority_atom(self, ref, *, upto_generation=None):
        """Return an authority-scoped atom visible to the pinned generation."""
        cutoff = self.generation if upto_generation is None else int(upto_generation)
        return self.db.execute(
            "SELECT * FROM atoms WHERE ref=? AND authority_scope='authority' AND generation<=?",
            (ref, cutoff),
        ).fetchone()

    def foundational(self, ref):
        atom = self.atom(ref)
        return bool(atom and json.loads(atom["metadata"]).get("foundational"))

    def symbol(self, role):
        row = self.db.execute(
            "SELECT semantic_ref FROM control_symbols WHERE role=?", (role,)
        ).fetchone()
        if not row:
            raise ValueError(f"missing control symbol {role}")
        return str(row[0])

    def creatable_kinds(self):
        return {
            str(row[0])
            for row in self.db.execute(
                "SELECT semantic_ref FROM control_symbols WHERE role LIKE 'new_kind.%'"
            )
        }

    def roles(self, operator):
        return {
            row["role_ref"]: row
            for row in self.db.execute(
                "SELECT * FROM operator_roles WHERE operator_ref=?", (operator,)
            )
        }

    @staticmethod
    def encode_value(value):
        if isinstance(value, dict) and "literal" in value:
            return "literal", canonical(value["literal"])
        if isinstance(value, dict) and "app" in value:
            return "app", str(value["app"])
        return "atom", str(value)

    @staticmethod
    def decode_value(kind, value):
        if kind == "literal":
            return {"literal": json.loads(value)}
        if kind == "app":
            return {"app": value}
        return value

    def _validate_filler(self, role, value, spec):
        filler_kind, filler_value = self.encode_value(value)
        expected = spec["filler_kind"]
        if expected == "state_value":
            if filler_kind == "atom" and not self.atom(filler_value):
                raise ValueError(f"unknown state atom {role}:{filler_value}")
            if filler_kind == "app" and not self.db.execute(
                "SELECT 1 FROM applications WHERE app_ref=?", (filler_value,)
            ).fetchone():
                raise ValueError(f"unknown state app {role}:{filler_value}")
            return
        if expected and expected.startswith("literal:"):
            if filler_kind != "literal" or json.loads(filler_value)["type"] != expected.split(":", 1)[1]:
                raise ValueError(f"literal kind {role}")
            return
        if filler_kind == "atom" and not self.atom(filler_value):
            raise ValueError(f"unknown atom filler {role}:{filler_value}")
        if filler_kind == "app" and not self.db.execute(
            "SELECT 1 FROM applications WHERE app_ref=?", (filler_value,)
        ).fetchone():
            raise ValueError(f"unknown app filler {role}:{filler_value}")
        if expected in {"atom", "app"} and filler_kind != expected:
            raise ValueError(f"filler class {role}")
        if expected and expected not in {"atom", "app"} and not expected.startswith("literal:"):
            atom = self.atom(filler_value) if filler_kind == "atom" else None
            if not atom or atom["kind"] != expected:
                raise ValueError(f"filler kind {role}: expected {expected}")

    @staticmethod
    def _application_predicate_ref(operator, args):
        role = {
            "op:event": "role:type",
            "op:relation": "role:relation",
            "op:state": "role:dimension",
            "op:type": "role:class",
        }.get(str(operator))
        value = args.get(role) if role else None
        return value if isinstance(value, str) and not value.startswith(("?", "!")) else None

    def _frame_allows_app(self, operator, role_ref, args):
        predicate = self._application_predicate_ref(operator, args)
        if not predicate:
            return False
        profiles = SemanticAffordanceIndex(
            self, self.generation, max_profiles_per_target=4
        ).profiles_for(predicate)
        return any(
            profile.metadata.get("kernel_operator_ref") == operator
            and profile.metadata.get("proposition_taking")
            and any(role.role_ref == role_ref and "app" in role.filler_kinds for role in profile.roles)
            for profile in profiles
        )

    def validate_app(self, operator, args):
        if not self.atom(operator):
            raise ValueError(f"unknown operator {operator}")
        specs = self.roles(operator)
        for role, value in args.items():
            if role not in specs:
                raise ValueError(f"{operator} disallows {role}")
            try:
                self._validate_filler(role, value, specs[role])
            except ValueError:
                if not (
                    isinstance(value, dict)
                    and set(value) == {"app"}
                    and self._frame_allows_app(operator, role, args)
                    and self.db.execute(
                        "SELECT 1 FROM applications WHERE app_ref=?", (str(value["app"]),)
                    ).fetchone()
                ):
                    raise
        for role, spec in specs.items():
            if spec["required"] and role not in args:
                raise ValueError(f"missing {operator}:{role}")
        try:
            state_operator = self.symbol("operator.state")
            dimension_role = self.symbol("role.dimension")
            value_role = self.symbol("role.value")
        except ValueError:
            state_operator = dimension_role = value_role = None
        if operator == state_operator and dimension_role in args:
            dimension = self.atom(str(args[dimension_role]))
            if not dimension or dimension["kind"] != "state_dimension":
                raise ValueError(f"invalid state dimension:{args[dimension_role]}")
            if value_role in args:
                self.validate_state_value(str(args[dimension_role]), args[value_role])

    def app_signature(self, operator, args):
        return stable(
            "app",
            operator,
            sorted((role, *self.encode_value(value)) for role, value in args.items()),
        )

    def insert_app(
        self,
        operator,
        args,
        generation,
        observation,
        stance="support",
        confidence=1.0,
        authority="reviewed",
        valid_from=None,
    ):
        self.validate_app(operator, args)
        app_ref = self.app_signature(operator, args)
        self.db.execute(
            "INSERT OR IGNORE INTO applications VALUES(?,?,?)",
            (app_ref, operator, generation),
        )
        for ordinal, (role, value) in enumerate(sorted(args.items())):
            filler_kind, filler_value = self.encode_value(value)
            binding_ref = stable("bind", app_ref, role, filler_kind, filler_value, ordinal)
            self.db.execute(
                "INSERT OR IGNORE INTO bindings VALUES(?,?,?,?,?,?)",
                (binding_ref, app_ref, role, filler_kind, filler_value, ordinal),
            )
        observed = self.db.execute(
            "SELECT observed_at FROM observations WHERE observation_ref=?", (observation,)
        ).fetchone()
        effective_from = valid_from or (str(observed[0]) if observed else now())
        claim_ref = stable("claim", app_ref, observation, stance)
        self.db.execute(
            "INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?)",
            (
                claim_ref,
                app_ref,
                observation,
                stance,
                float(confidence),
                authority,
                effective_from,
                None,
                generation,
            ),
        )
        self.db.execute(
            "INSERT OR IGNORE INTO proof_links VALUES(?,?,?,?,?)",
            (stable("proof", claim_ref), claim_ref, observation, "assert", "[]"),
        )
        self._supersede_state(app_ref, operator, args, stance, effective_from, observation)
        try:
            designation_operator = self.symbol("operator.designation")
        except ValueError:
            designation_operator = None
        if operator == designation_operator:
            self.index_designation_app(app_ref)
        return app_ref

    @staticmethod
    def _literal_or_value(value, default=None):
        if value is None:
            return default
        if isinstance(value, dict) and "literal" in value:
            return value["literal"].get("value", default)
        return value

    def index_designation_app(self, app_ref):
        """Refresh one designation index row from an active exact application.

        This is the normal incremental path. Full index rebuild is reserved for
        imports/audits and never runs for ordinary acquisition or conversation.
        """
        try:
            operator = self.symbol("operator.designation")
            roles = {
                key: self.symbol(f"designation.{key}")
                for key in ("target", "type", "surface", "language", "script", "prior", "preferred", "context")
            }
        except ValueError:
            return None
        application = self.db.execute(
            "SELECT operator_ref FROM applications WHERE app_ref=?", (app_ref,)
        ).fetchone()
        if not application or str(application["operator_ref"]) != operator:
            return None
        active = self.db.execute(
            "SELECT 1 FROM claims WHERE app_ref=? AND stance='support' AND valid_to IS NULL LIMIT 1",
            (app_ref,),
        ).fetchone()
        if not active:
            self.db.execute("DELETE FROM designation_index WHERE label_ref=?", (app_ref,))
            return None
        values = {}
        for binding in self.db.execute(
            "SELECT role_ref,filler_kind,filler_value FROM bindings WHERE app_ref=? ORDER BY ordinal",
            (app_ref,),
        ).fetchall():
            values[str(binding["role_ref"])] = self.decode_value(
                binding["filler_kind"], binding["filler_value"]
            )
        target = self._literal_or_value(values.get(roles["target"]))
        surface = self._literal_or_value(values.get(roles["surface"]))
        if not target or not surface:
            self.db.execute("DELETE FROM designation_index WHERE label_ref=?", (app_ref,))
            return None
        row = (
            app_ref,
            str(target),
            str(self._literal_or_value(values.get(roles["type"]), "label:default")),
            str(surface),
            str(self._literal_or_value(values.get(roles["language"]), "und")),
            str(self._literal_or_value(values.get(roles["script"]), "Zyyy")),
            float(self._literal_or_value(values.get(roles["prior"]), 1.0)),
            int(bool(self._literal_or_value(values.get(roles["preferred"]), False))),
            self._literal_or_value(values.get(roles["context"])),
        )
        self.db.execute(
            "INSERT OR REPLACE INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)", row
        )
        return app_ref

    def _observation_context(self, observation_ref):
        row = self.db.execute(
            "SELECT packet FROM observations WHERE observation_ref=?", (observation_ref,)
        ).fetchone()
        if not row:
            return None
        try:
            packet = json.loads(row[0])
            return packet.get("context_ref") or packet.get("qualifiers", {}).get("context")
        except Exception:
            return None

    def _supersede_state(self, new_ref, operator, args, stance, effective_from, observation_ref):
        try:
            state_operator = self.symbol("operator.state")
            subject_role = self.symbol("role.subject")
            dimension_role = self.symbol("role.dimension")
            value_role = self.symbol("role.value")
        except ValueError:
            return
        if stance != "support" or operator != state_operator or any(
            role not in args for role in (subject_role, dimension_role, value_role)
        ):
            return
        dimension = self.atom(str(args[dimension_role]))
        metadata = json.loads(dimension["metadata"]) if dimension else {}
        cardinality = metadata.get("cardinality") or (
            "one" if metadata.get("exclusive") else "many"
        )
        if cardinality != "one":
            return
        new_context = self._observation_context(observation_ref)
        for claim in self.state_claim_records(args[subject_role], args[dimension_role]):
            if claim["app_ref"] == new_ref or claim["stance"] != "support" or claim["valid_to"] is not None:
                continue
            if canonical(claim["value"]) == canonical(args[value_role]):
                continue
            if claim.get("context_ref") != new_context:
                continue
            self.db.execute(
                "UPDATE claims SET valid_to=? WHERE claim_ref=?",
                (effective_from, claim["claim_ref"]),
            )

    def type_classes(self, referent_ref):
        rows = self.db.execute(
            """SELECT DISTINCT bc.filler_value FROM applications a
               JOIN bindings bi ON bi.app_ref=a.app_ref AND bi.role_ref='role:instance' AND bi.filler_kind='atom'
               JOIN bindings bc ON bc.app_ref=a.app_ref AND bc.role_ref='role:class' AND bc.filler_kind='atom'
               JOIN claims c ON c.app_ref=a.app_ref
               WHERE a.operator_ref='op:type' AND bi.filler_value=?
                 AND c.stance='support' AND c.valid_to IS NULL""",
            (referent_ref,),
        ).fetchall()
        return [str(row[0]) for row in rows]

    def relation_objects(self, subject_ref, relation_ref, authority_only=False, upto_generation=None):
        sql = """SELECT DISTINCT bo.filler_value FROM applications a
                 JOIN bindings bs ON bs.app_ref=a.app_ref AND bs.role_ref='role:subject' AND bs.filler_kind='atom'
                 JOIN bindings br ON br.app_ref=a.app_ref AND br.role_ref='role:relation' AND br.filler_kind='atom'
                 JOIN bindings bo ON bo.app_ref=a.app_ref AND bo.role_ref='role:object' AND bo.filler_kind='atom'
                 JOIN claims c ON c.app_ref=a.app_ref
                 WHERE a.operator_ref='op:relation' AND bs.filler_value=? AND br.filler_value=?
                   AND c.stance='support' AND c.valid_to IS NULL"""
        params = [subject_ref, relation_ref]
        if authority_only:
            sql += " AND c.authority_status IN('reviewed','promoted') AND a.generation<=?"
            params.append(self.generation if upto_generation is None else int(upto_generation))
        return [str(row[0]) for row in self.db.execute(sql, params).fetchall()]

    def dimensions_for_value(self, value_ref, *, authority_only=True, upto_generation=None):
        """Return explicitly related state dimensions for a semantic value.

        This is not compiler completion. Language candidates must explicitly
        select a DIM_OF_A* source; this method only resolves that declared
        semantic dependency against exact authority.
        """
        try:
            relation = self.symbol("profile.value_dimension_relation")
        except ValueError:
            return ()
        return tuple(sorted(set(self.relation_objects(
            value_ref,
            relation,
            authority_only=authority_only,
            upto_generation=upto_generation,
        ))))

    def state_dimension_domain_type(self, dimension_ref):
        try:
            relation = self.symbol("profile.dimension_domain_relation")
        except ValueError:
            return None
        domains = self.relation_objects(dimension_ref, relation, authority_only=True)
        if len(domains) != 1:
            return None
        atom = self.atom(domains[0])
        return json.loads(atom["metadata"]).get("domain_type") if atom else None

    def validate_state_value(self, dimension_ref, value):
        dimension = self.atom(dimension_ref)
        metadata = json.loads(dimension["metadata"]) if dimension else {}
        filler_kind, filler_value = self.encode_value(value)
        domain = self.state_dimension_domain_type(dimension_ref) or metadata.get("domain_type")
        allowed_fillers = set(metadata.get("value_filler_kinds", []))
        if allowed_fillers and filler_kind not in allowed_fillers:
            raise ValueError(f"state value filler {dimension_ref}:{filler_kind}")
        if filler_kind == "atom":
            atom = self.atom(filler_value)
            allowed_kinds = set(metadata.get("value_atom_kinds", []))
            if allowed_kinds and (not atom or atom["kind"] not in allowed_kinds):
                raise ValueError(f"state value atom kind {dimension_ref}:{filler_value}")
            if domain == "categorical" and (not atom or atom["kind"] != "value"):
                raise ValueError(f"categorical state requires value atom:{dimension_ref}")
        elif filler_kind == "literal":
            literal = json.loads(filler_value)
            expected = metadata.get("literal_type")
            if expected and literal.get("type") != expected:
                raise ValueError(f"state literal type {dimension_ref}:{literal.get('type')}")
            if domain == "categorical":
                raise ValueError(f"categorical state requires semantic value atom:{dimension_ref}")
            if domain == "continuous" and literal.get("type") not in {"int", "float"}:
                raise ValueError(f"continuous state requires numeric literal:{dimension_ref}")
            numeric = literal.get("value")
            if isinstance(numeric, (int, float)):
                if "min" in metadata and numeric < metadata["min"]:
                    raise ValueError(f"state value below minimum:{dimension_ref}")
                if "max" in metadata and numeric > metadata["max"]:
                    raise ValueError(f"state value above maximum:{dimension_ref}")

    def state_claim_records(self, subject_ref=None, dimension_ref=None):
        state_operator = self.symbol("operator.state")
        subject_role = self.symbol("role.subject")
        dimension_role = self.symbol("role.dimension")
        value_role = self.symbol("role.value")
        sql = """SELECT a.app_ref,c.claim_ref,c.stance,c.confidence,c.authority_status,
                        c.valid_from,c.valid_to,c.generation,
                        bs.filler_value subject_ref,bd.filler_value dimension_ref,
                        o.observation_ref,o.source_ref,o.observed_at,o.packet,
                        bv.filler_kind value_kind,bv.filler_value value_data,p.parent_refs
                 FROM applications a
                 JOIN bindings bs ON bs.app_ref=a.app_ref AND bs.role_ref=? AND bs.filler_kind='atom'
                 JOIN bindings bd ON bd.app_ref=a.app_ref AND bd.role_ref=? AND bd.filler_kind='atom'
                 JOIN bindings bv ON bv.app_ref=a.app_ref AND bv.role_ref=?
                 JOIN claims c ON c.app_ref=a.app_ref
                 JOIN observations o ON o.observation_ref=c.observation_ref
                 LEFT JOIN proof_links p ON p.subject_ref=c.claim_ref
                 WHERE a.operator_ref=?"""
        params = [subject_role, dimension_role, value_role, state_operator]
        if subject_ref is not None:
            sql += " AND bs.filler_value=?"
            params.append(subject_ref)
        if dimension_ref is not None:
            sql += " AND bd.filler_value=?"
            params.append(dimension_ref)
        output = []
        for row in self.db.execute(sql, params).fetchall():
            try:
                packet = json.loads(row["packet"])
            except Exception:
                packet = {}
            output.append(
                {
                    "app_ref": str(row["app_ref"]),
                    "claim_ref": str(row["claim_ref"]),
                    "subject_ref": str(row["subject_ref"]),
                    "dimension_ref": str(row["dimension_ref"]),
                    "value": self.decode_value(row["value_kind"], row["value_data"]),
                    "stance": str(row["stance"]),
                    "confidence": float(row["confidence"]),
                    "authority_status": str(row["authority_status"]),
                    "valid_from": row["valid_from"],
                    "valid_to": row["valid_to"],
                    "generation": int(row["generation"]),
                    "observation_ref": str(row["observation_ref"]),
                    "source_ref": str(row["source_ref"]),
                    "observed_at": str(row["observed_at"]),
                    "context_ref": packet.get("context_ref") or packet.get("qualifiers", {}).get("context"),
                    "proof_parents": json.loads(row["parent_refs"] or "[]"),
                }
            )
        return output

    def base_facts(self):
        """Explicit audit/debug full materialization. Runtime cognition must use matching_facts."""
        return self.matching_facts((), limit=None)

    def add_observation(self, surface, packet, language, source, generation, confidence=0.95, occurrence_ref=None, *, modality="language"):
        ref = stable("obs", surface, modality, language, source, packet, occurrence_ref or "dedup")
        self.db.execute(
            "INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?)",
            (ref, surface, modality, language, source, now(), canonical(packet), confidence, generation),
        )
        return ref

    def add_claim_occurrence(self, observation_ref, act, generation):
        payload = act.as_dict() if hasattr(act, "as_dict") else dict(act)
        occurrence_ref = stable("claim-occurrence", observation_ref, payload)
        self.db.execute(
            "INSERT OR IGNORE INTO claim_occurrences VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                occurrence_ref,
                observation_ref,
                payload["act_ref"],
                payload["force"],
                payload["speaker_ref"],
                payload["addressee_ref"],
                canonical(payload.get("content", [])),
                payload.get("context_ref"),
                payload.get("modality", "actual"),
                now(),
                generation,
            ),
        )
        return occurrence_ref

    def add_epistemic_placement(self, occurrence_ref, placement, generation):
        payload = placement.as_dict() if hasattr(placement, "as_dict") else dict(placement)
        self.db.execute(
            "INSERT OR IGNORE INTO epistemic_placements VALUES(?,?,?,?,?,?,?,?,?)",
            (
                payload["placement_ref"],
                occurrence_ref,
                payload["admission_class"],
                int(bool(payload["admitted"])),
                payload["reason"],
                payload.get("context_ref"),
                canonical(payload.get("target_refs", [])),
                now(),
                generation,
            ),
        )
        return payload["placement_ref"]

    def retract_claim_occurrence(self, occurrence_ref, speaker_ref, *, valid_to=None):
        row = self.db.execute(
            "SELECT observation_ref,speaker_ref FROM claim_occurrences WHERE occurrence_ref=?",
            (occurrence_ref,),
        ).fetchone()
        if not row:
            raise ValueError(f"unknown claim occurrence: {occurrence_ref}")
        if str(row["speaker_ref"]) != str(speaker_ref):
            raise PermissionError("a participant may retract only their own attributed claim occurrence")
        closed_at = valid_to or now()
        claims = self.db.execute(
            "SELECT claim_ref,app_ref FROM claims WHERE observation_ref=? AND valid_to IS NULL",
            (row["observation_ref"],),
        ).fetchall()
        for claim in claims:
            self.db.execute("UPDATE claims SET valid_to=? WHERE claim_ref=?", (closed_at, claim["claim_ref"]))
        for app_ref in sorted({str(claim["app_ref"]) for claim in claims}):
            self.index_designation_app(app_ref)
        return tuple(str(claim["claim_ref"]) for claim in claims)

    def claim_occurrence_records(self):
        return [
            {
                **dict(row),
                "content": json.loads(row["content"]),
            }
            for row in self.db.execute(
                "SELECT * FROM claim_occurrences ORDER BY created_at,occurrence_ref"
            ).fetchall()
        ]

    def epistemic_placement_records(self):
        return [
            {
                **dict(row),
                "admitted": bool(row["admitted"]),
                "target_refs": json.loads(row["target_refs"]),
            }
            for row in self.db.execute(
                "SELECT * FROM epistemic_placements ORDER BY created_at,placement_ref"
            ).fetchall()
        ]

    def validate_rule(self, rule):
        antecedent = list(rule.get("if", []))
        consequent = list(rule.get("then", []))
        if not antecedent or not consequent:
            raise ValueError("rule requires antecedent and consequent")
        if not 0 < float(rule.get("confidence", 1)) <= 1:
            raise ValueError("rule confidence out of range")
        bound = {
            value
            for clause in antecedent
            for value in clause.get("args", {}).values()
            if isvar(value)
        }
        if any(
            isexist(value)
            for clause in antecedent
            for value in clause.get("args", {}).values()
        ):
            raise ValueError("existential witness cannot appear in antecedent")
        for clause in antecedent + consequent:
            operator = clause.get("operator")
            if not self.atom(operator):
                raise ValueError(f"rule unknown operator {operator}")
            specs = self.roles(operator)
            for role, value in clause.get("args", {}).items():
                if role not in specs:
                    raise ValueError(f"rule {operator} disallows {role}")
                if isinstance(value, str) and (isvar(value) or isexist(value)):
                    if clause in consequent and isvar(value) and value not in bound:
                        raise ValueError(f"unbound consequent variable {value}")
                    continue
                self._validate_filler(role, value, specs[role])
            if operator == "op:state":
                dimension = clause.get("args", {}).get("role:dimension")
                state_value = clause.get("args", {}).get("role:value")
                if dimension is not None and state_value is not None and not (isvar(dimension) or isvar(state_value) or isexist(state_value)):
                    self.validate_state_value(str(dimension), state_value)
            if clause in consequent:
                for role, spec in specs.items():
                    if spec["required"] and role not in clause.get("args", {}):
                        raise ValueError(f"rule consequent missing {operator}:{role}")

    def publish_definition_graph(
        self,
        *,
        target_ref: str,
        antecedent,
        consequent,
        confidence: float = 1.0,
        source_ref: str = "reviewed_definition",
    ) -> dict:
        """Publish one reviewed atomic definition and its derived rule index.

        The canonical definition graph is persisted in the reviewed observation
        packet. The `rules` row is a deterministic execution projection that
        names its source graph through `definition_ref`; it has no independent
        semantic authority.
        """
        target = self.authority_atom(str(target_ref))
        if target is None:
            raise ValueError(f"definition target is not reviewed authority:{target_ref}")
        rule = {
            "rule_kind": "definition",
            "if": [dict(item) for item in antecedent],
            "then": [dict(item) for item in consequent],
            "confidence": float(confidence),
        }
        self.validate_rule(rule)
        clauses = tuple(rule["if"]) + tuple(rule["then"])
        if not any(
            str(target_ref) in {
                str(value)
                for value in dict(clause.get("args", {})).values()
                if isinstance(value, str)
            }
            for clause in clauses
        ):
            raise ValueError("definition graph must explicitly contain its target")
        definition_ref = stable(
            "reviewed-definition-graph-v1", str(target_ref),
            canonical(rule["if"]), canonical(rule["then"]), float(confidence),
        )
        existing = self.definition_graph(definition_ref)
        if existing is not None:
            return existing
        projection_rule_ref = stable(
            "definition-rule-projection-v1", definition_ref,
            canonical(rule["if"]), canonical(rule["then"]),
        )
        definition_application_refs = []
        for side, clauses_for_side in (
            ("antecedent", rule["if"]),
            ("consequent", rule["then"]),
        ):
            for index, clause in enumerate(clauses_for_side):
                operator = str(clause["operator"])
                args = dict(clause.get("args", {}))
                specs = self.roles(operator)
                for role, spec in specs.items():
                    if spec["required"] and role not in args:
                        raise ValueError(f"definition application missing {operator}:{role}")
                app_ref = stable(
                    "definition-application-v1", definition_ref, side, index,
                    operator, canonical(args),
                )
                definition_application_refs.append(app_ref)
        packet = {
            "definition_graph": {
                "definition_ref": definition_ref,
                "target_ref": str(target_ref),
                "antecedent": rule["if"],
                "consequent": rule["then"],
                "confidence": float(confidence),
                "projection_rule_refs": [projection_rule_ref],
                "application_refs": definition_application_refs,
            }
        }
        with self.db:
            generation = self.begin("publish_definition_graph:" + definition_ref[-16:])
            observation_ref = self.add_observation(
                definition_ref, packet, "und", source_ref, generation,
                float(confidence), modality="semantic_definition",
            )
            for app_ref, clause in zip(
                definition_application_refs,
                tuple(rule["if"]) + tuple(rule["then"]),
            ):
                operator = str(clause["operator"])
                args = dict(clause.get("args", {}))
                self.db.execute(
                    "INSERT INTO applications(app_ref,operator_ref,generation) VALUES(?,?,?)",
                    (app_ref, operator, generation),
                )
                for ordinal, (role, value) in enumerate(sorted(args.items())):
                    specs = self.roles(operator)
                    if role not in specs:
                        raise ValueError(f"definition application disallows {operator}:{role}")
                    if not (isinstance(value, str) and (isvar(value) or isexist(value))):
                        self._validate_filler(role, value, specs[role])
                    filler_kind, filler_value = self.encode_value(value)
                    self.db.execute(
                        "INSERT INTO bindings(binding_ref,app_ref,role_ref,filler_kind,filler_value,ordinal) VALUES(?,?,?,?,?,?)",
                        (
                            stable(
                                "definition-binding-v1", app_ref, role,
                                filler_kind, filler_value, ordinal,
                            ),
                            app_ref, role, filler_kind, filler_value, ordinal,
                        ),
                    )
            self.db.execute(
                "INSERT INTO rules(rule_ref,rule_kind,antecedent,consequent,confidence,authority_status,generation,definition_ref) VALUES(?,?,?,?,?,?,?,?)",
                (
                    projection_rule_ref, "definition", canonical(rule["if"]),
                    canonical(rule["then"]), float(confidence), "reviewed",
                    generation, definition_ref,
                ),
            )
            self.rebuild_rule_index(projection_rule_ref)
            receipt = self.finish(
                generation,
                cycle_ref="reviewed-definition-publication",
                stage=13,
                world_delta=True,
                observation_delta=True,
                payload={"definition_ref": definition_ref, "target_ref": target_ref},
            )
        return {
            "definition_ref": definition_ref,
            "target_ref": str(target_ref),
            "antecedent": rule["if"],
            "consequent": rule["then"],
            "projection_rule_refs": [projection_rule_ref],
            "application_refs": definition_application_refs,
            "observation_ref": observation_ref,
            "generation": generation,
            "receipt": receipt,
        }

    def definition_graph(self, definition_ref: str) -> dict | None:
        row = self.db.execute(
            "SELECT packet,observation_ref,generation FROM observations "
            "WHERE source_ref='reviewed_definition' AND surface=? "
            "ORDER BY generation DESC LIMIT 1",
            (str(definition_ref),),
        ).fetchone()
        if row is None:
            return None
        packet = json.loads(row["packet"])
        graph = dict(packet.get("definition_graph") or {})
        if str(graph.get("definition_ref") or "") != str(definition_ref):
            raise ValueError("definition observation identity mismatch")
        return {
            **graph,
            "observation_ref": str(row["observation_ref"]),
            "generation": int(row["generation"]),
        }

    def upsert_rule_candidate(self, rule, generation, confidence=0.9, min_evidence=2):
        self.validate_rule(rule)
        antecedent = canonical(rule["if"])
        consequent = canonical(rule["then"])
        kind = rule.get("rule_kind", "definition")
        ref = stable("rulecand", kind, antecedent, consequent)
        row = self.db.execute(
            "SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)
        ).fetchone()
        if row:
            self.db.execute(
                "UPDATE rule_candidates SET evidence_count=evidence_count+1,last_generation=?,confidence=max(confidence,?) WHERE candidate_ref=?",
                (generation, float(confidence), ref),
            )
        else:
            self.db.execute(
                "INSERT INTO rule_candidates VALUES(?,?,?,?,?,?,?,?,?)",
                (ref, kind, antecedent, consequent, 1, "provisional", float(confidence), generation, generation),
            )
        row = self.db.execute(
            "SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)
        ).fetchone()
        promoted = False
        if int(row["evidence_count"]) >= int(min_evidence) and row["status"] != "promoted":
            rule_ref = stable("rule", kind, antecedent, consequent)
            self.db.execute(
                "INSERT OR IGNORE INTO rules(rule_ref,rule_kind,antecedent,consequent,confidence,authority_status,generation,definition_ref) VALUES(?,?,?,?,?,?,?,?)",
                (rule_ref, kind, antecedent, consequent, float(row["confidence"]), "promoted", generation, None),
            )
            self.db.execute(
                "UPDATE rule_candidates SET status='promoted' WHERE candidate_ref=?", (ref,)
            )
            self.rebuild_rule_index(rule_ref)
            promoted = True
        return ref, promoted

    def add_rule_candidate(self, ref, kind, antecedent, consequent, confidence, generation):
        row = self.db.execute(
            "SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)
        ).fetchone()
        if row:
            self.db.execute(
                "UPDATE rule_candidates SET evidence_count=evidence_count+1,last_generation=?,confidence=max(confidence,?) WHERE candidate_ref=?",
                (generation, float(confidence), ref),
            )
        else:
            self.db.execute(
                "INSERT INTO rule_candidates VALUES(?,?,?,?,?,?,?,?,?)",
                (ref, kind, antecedent, consequent, 1, "provisional", float(confidence), generation, generation),
            )
        return ref

    @staticmethod
    def decode_rule_side(raw):
        return json.loads(raw) if isinstance(raw, str) else list(raw)

    def _facts_from_app_refs(self, app_refs, limit=None):
        """Hydrate a bounded application set in three indexed batch queries."""
        app_refs = list(dict.fromkeys(str(item) for item in app_refs))
        if not app_refs:
            return []
        if limit is not None:
            app_refs = app_refs[: int(limit)]
        placeholders = ",".join("?" for _ in app_refs)
        applications = self.db.execute(
            f"SELECT app_ref,operator_ref FROM applications WHERE app_ref IN ({placeholders}) ORDER BY app_ref",
            app_refs,
        ).fetchall()
        bindings_by_app = {ref: {} for ref in app_refs}
        for row in self.db.execute(
            f"SELECT app_ref,role_ref,filler_kind,filler_value FROM bindings "
            f"WHERE app_ref IN ({placeholders}) ORDER BY app_ref,role_ref,ordinal",
            app_refs,
        ).fetchall():
            bindings_by_app.setdefault(str(row["app_ref"]), {})[str(row["role_ref"])] = self.decode_value(
                row["filler_kind"], row["filler_value"]
            )
        claims_by_app = {ref: {"support": [], "deny": []} for ref in app_refs}
        for row in self.db.execute(
            f"SELECT app_ref,stance,confidence FROM claims WHERE app_ref IN ({placeholders}) "
            "AND valid_to IS NULL ORDER BY app_ref,stance",
            app_refs,
        ).fetchall():
            claims_by_app.setdefault(str(row["app_ref"]), {"support": [], "deny": []})[
                str(row["stance"])
            ].append(float(row["confidence"]))
        output = []
        for application in applications:
            app_ref = str(application["app_ref"])
            args = bindings_by_app.get(app_ref, {})
            stances = claims_by_app.get(app_ref, {})
            for stance in ("support", "deny"):
                confidences = stances.get(stance, ())
                if confidences:
                    output.append(
                        Fact(
                            app_ref,
                            str(application["operator_ref"]),
                            args,
                            stance,
                            max(confidences),
                        )
                    )
        return output

    def matching_facts(self, patterns=(), limit=128):
        patterns = tuple(patterns or ())
        if not patterns:
            sql = "SELECT app_ref FROM applications ORDER BY app_ref"
            params = []
            if limit is not None:
                sql += " LIMIT ?"; params.append(int(limit))
            refs = [str(row[0]) for row in self.db.execute(sql, params).fetchall()]
            return self._facts_from_app_refs(refs, limit)
        candidate_sets = []
        for pattern in patterns:
            joins = []
            join_params = []
            index = 0
            for role, value in pattern.get("args", {}).items():
                if isinstance(value, str) and isvar(value):
                    continue
                alias = f"b{index}"; index += 1
                kind, encoded = self.encode_value(value)
                joins.append(
                    f"JOIN bindings {alias} ON {alias}.app_ref=a.app_ref "
                    f"AND {alias}.role_ref=? AND {alias}.filler_kind=? AND {alias}.filler_value=?"
                )
                join_params.extend([role, kind, encoded])
            joins.append("JOIN claims c ON c.app_ref=a.app_ref AND c.stance=? AND c.valid_to IS NULL")
            join_params.append(pattern.get("stance", "support"))
            sql = f"SELECT DISTINCT a.app_ref FROM applications a {' '.join(joins)} WHERE a.operator_ref=? ORDER BY a.app_ref"
            params = join_params + [pattern["operator"]]
            if limit is not None:
                sql += " LIMIT ?"; params.append(int(limit))
            candidate_sets.append({str(row[0]) for row in self.db.execute(sql, params).fetchall()})
        refs = set.union(*candidate_sets) if candidate_sets else set()
        return self._facts_from_app_refs(sorted(refs), limit)

    def facts_mentioning(self, refs, limit=64):
        refs = sorted(set(str(x) for x in refs))
        if not refs or limit <= 0:
            return []
        placeholders = ",".join("?" for _ in refs)
        rows = self.db.execute(
            f"SELECT DISTINCT app_ref FROM bindings WHERE filler_kind='atom' AND filler_value IN ({placeholders}) ORDER BY app_ref LIMIT ?",
            (*refs, int(limit)),
        ).fetchall()
        return self._facts_from_app_refs([str(row[0]) for row in rows], limit)

    def rebuild_rule_index(self, rule_ref=None):
        if rule_ref is None:
            self.db.execute("DELETE FROM rule_index")
            rows = self.db.execute("SELECT * FROM rules").fetchall()
        else:
            self.db.execute("DELETE FROM rule_index WHERE rule_ref=?", (rule_ref,))
            rows = self.db.execute("SELECT * FROM rules WHERE rule_ref=?", (rule_ref,)).fetchall()
        for row in rows:
            for side, raw in (("antecedent", row["antecedent"]), ("consequent", row["consequent"])):
                for clause in json.loads(raw):
                    operator = str(clause.get("operator"))
                    constants = {
                        str(value) for value in clause.get("args", {}).values()
                        if isinstance(value, str) and not isvar(value) and not isexist(value)
                    } or {None}
                    for semantic_ref in constants:
                        self.db.execute(
                            "INSERT OR IGNORE INTO rule_index VALUES(?,?,?,?)",
                            (row["rule_ref"], side, operator, semantic_ref),
                        )

    def relevant_rules(self, *, rule_kinds=("definition","entailment"), consequent=True, operator_refs=(), semantic_refs=(), authority_generation=None, limit=64):
        cutoff = self.generation if authority_generation is None else int(authority_generation)
        kinds = tuple(rule_kinds)
        side = "consequent" if consequent else "antecedent"
        clauses = [f"r.rule_kind IN ({','.join('?' for _ in kinds)})", "r.authority_status IN('reviewed','promoted')", "r.generation<=?"]
        params = list(kinds) + [cutoff]
        filters = []
        operator_refs = tuple(sorted(set(operator_refs)))
        semantic_refs = tuple(sorted(set(semantic_refs)))
        if operator_refs:
            filters.append(f"ri.operator_ref IN ({','.join('?' for _ in operator_refs)})")
            params.extend(operator_refs)
        if semantic_refs:
            filters.append(f"ri.semantic_ref IN ({','.join('?' for _ in semantic_refs)})")
            params.extend(semantic_refs)
        if filters:
            clauses.append("(" + " OR ".join(filters) + ")")
        sql = f"SELECT DISTINCT r.* FROM rules r JOIN rule_index ri ON ri.rule_ref=r.rule_ref AND ri.side=? WHERE {' AND '.join(clauses)} ORDER BY r.rule_ref LIMIT ?"
        params = [side] + params + [int(limit)]
        return [dict(row) for row in self.db.execute(sql, params).fetchall()]

    def commit_common_ground(self, conversation_ref, act_ref, semantic_action, status="emitted", *, expected_discourse_revision=None):
        revisions = self.revisions()
        if expected_discourse_revision is not None and int(expected_discourse_revision) != revisions["discourse_revision"]:
            raise RuntimeError(
                f"discourse revision CAS failed: expected {expected_discourse_revision}, found {revisions['discourse_revision']}"
            )
        new_revision = revisions["discourse_revision"] + 1
        entry_ref = stable("common-ground", conversation_ref, act_ref, semantic_action, status, new_revision)
        self.db.execute(
            "INSERT OR IGNORE INTO common_ground VALUES(?,?,?,?,?,?,?)",
            (entry_ref, conversation_ref, act_ref, canonical(semantic_action), status, now(), new_revision),
        )
        self.db.execute("UPDATE revision_state SET discourse_revision=? WHERE singleton=1", (new_revision,))
        return {"entry_ref": entry_ref, "discourse_revision": new_revision}

    def journal_effect(self, plan, result=None):
        payload = plan.as_dict() if hasattr(plan, "as_dict") else dict(plan)
        existing = self.db.execute(
            "SELECT * FROM effect_journal WHERE idempotency_key=?", (payload["idempotency_key"],)
        ).fetchone()
        if existing and existing["status"] in {"succeeded", "declined"}:
            return {
                "effect_ref": str(existing["effect_ref"]),
                "effect_revision": int(existing["effect_revision"]),
                "idempotent_replay": True,
            }
        revisions = self.revisions()
        new_revision = revisions["effect_revision"] + 1
        result_payload = result.as_dict() if result is not None and hasattr(result, "as_dict") else result
        effect_ref = stable("effect", payload["idempotency_key"])
        self.db.execute(
            "INSERT INTO effect_journal VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(idempotency_key) DO UPDATE SET status=excluded.status,result=excluded.result,updated_at=excluded.updated_at,effect_revision=excluded.effect_revision",
            (
                effect_ref, payload["idempotency_key"], payload["goal_ref"], payload.get("adapter_ref"),
                canonical(payload.get("request", {})), (result_payload or {}).get("status", "planned") if isinstance(result_payload, dict) else "planned",
                canonical(result_payload) if result_payload is not None else None, now(), now(), new_revision,
            ),
        )
        self.db.execute("UPDATE revision_state SET effect_revision=? WHERE singleton=1", (new_revision,))
        return {"effect_ref": effect_ref, "effect_revision": new_revision, "idempotent_replay": False}

    def _existing_authority_manifest(self):
        atoms = {
            str(row["ref"]): {
                "ref": str(row["ref"]),
                "kind": str(row["kind"]),
                "metadata": json.loads(row["metadata"]),
            }
            for row in self.db.execute(
                "SELECT ref,kind,metadata FROM atoms WHERE authority_scope='authority'"
            ).fetchall()
        }
        operator_roles = {
            (str(row["operator_ref"]), str(row["role_ref"])): {
                "operator_ref": str(row["operator_ref"]),
                "role_ref": str(row["role_ref"]),
                "required": bool(row["required"]),
                "cardinality": str(row["cardinality"]),
                "filler_kind": row["filler_kind"],
            }
            for row in self.db.execute("SELECT * FROM operator_roles").fetchall()
        }
        controls = {
            str(row["role"]): str(row["semantic_ref"])
            for row in self.db.execute("SELECT * FROM control_symbols").fetchall()
        }
        return atoms, operator_roles, controls

    def import_bundle(self, paths):
        """Link and atomically import one authority graph split across JSON files.

        No file is imported before the complete bundle passes exact cross-file
        validation.  Import order therefore cannot hide missing atoms, role
        contracts, rule constants, or concept/subtype confusion.
        """
        documents = load_documents(paths)
        existing_atoms, existing_roles, existing_controls = self._existing_authority_manifest()
        empty_authority = not existing_atoms
        report = validate_documents(
            documents,
            existing_atoms=existing_atoms,
            existing_operator_roles=existing_roles,
            existing_controls=existing_controls,
            require_foundations=empty_authority,
        )
        with self.db:
            generation = self.begin(
                "import_bundle:" + hashlib.sha256(
                    canonical((report.bundle_hash, [document.name for document in documents])).encode()
                ).hexdigest()[:16]
            )
            # The graph is linked before this point.  Durable insertion is now
            # deterministic and grouped by semantic dependency, not file order.
            for document in sorted(documents, key=lambda item: str(item.path)):
                for atom in sorted(document.data.get("atoms", ()), key=lambda item: item["ref"]):
                    self.exact(
                        "atoms",
                        ["ref", "kind", "metadata", "generation", "authority_scope"],
                        [atom["ref"], atom["kind"], canonical(atom.get("metadata", {})), generation, "authority"],
                        ["ref"],
                        {"generation"},
                    )
            for document in sorted(documents, key=lambda item: str(item.path)):
                for item in sorted(
                    document.data.get("operator_roles", ()),
                    key=lambda value: (value["operator_ref"], value["role_ref"]),
                ):
                    self.exact(
                        "operator_roles",
                        ["operator_ref", "role_ref", "required", "cardinality", "filler_kind"],
                        [item["operator_ref"], item["role_ref"], int(item.get("required", False)), "one", item.get("filler_kind")],
                        ["operator_ref", "role_ref"],
                    )
                for role, ref in sorted(document.data.get("control_symbols", {}).items()):
                    self.exact("control_symbols", ["role", "semantic_ref"], [role, ref], ["role"])
                for item in sorted(
                    document.data.get("reference_forms", ()),
                    key=lambda value: (value.get("language", "en"), value["surface"], value.get("bound_ref") or ""),
                ):
                    self.exact(
                        "reference_forms",
                        ["language", "surface", "features", "bound_ref", "weight"],
                        [item.get("language", "en"), item["surface"], canonical(item.get("features", {})), item.get("bound_ref"), float(item.get("weight", 1))],
                        ["language", "surface", "bound_ref"],
                    )
            for document in sorted(documents, key=lambda item: str(item.path)):
                for rule in sorted(document.data.get("rules", ()), key=lambda item: item["rule_ref"]):
                    self.validate_rule(rule)
                    kind = rule.get("rule_kind", "entailment")
                    antecedent = canonical(rule.get("if", ()))
                    consequent = canonical(rule.get("then", ()))
                    if self.db.execute(
                        "SELECT 1 FROM rules WHERE rule_kind=? AND antecedent=? AND consequent=?",
                        (kind, antecedent, consequent),
                    ).fetchone():
                        continue
                    self.exact(
                        "rules",
                        ["rule_ref", "rule_kind", "antecedent", "consequent", "confidence", "authority_status", "generation", "definition_ref"],
                        [rule["rule_ref"], kind, antecedent, consequent, float(rule.get("confidence", 1)), rule.get("authority_status", "reviewed"), generation, rule.get("definition_ref")],
                        ["rule_ref"],
                        {"generation"},
                    )
            fact_count = 0
            for document in sorted(documents, key=lambda item: str(item.path)):
                for fact in sorted(
                    document.data.get("facts", ()),
                    key=lambda item: canonical((item.get("operator"), item.get("stance", "support"), item.get("args", {}), item.get("fact_ref", ""))),
                ):
                    observation = self.add_observation(
                        fact.get("source_text", fact.get("fact_ref", fact["operator"])),
                        fact,
                        "und",
                        fact.get("source_ref", "seed"),
                        generation,
                        float(fact.get("confidence", 1)),
                    )
                    self.insert_app(
                        fact["operator"],
                        fact.get("args", {}),
                        generation,
                        observation,
                        fact.get("stance", "support"),
                        fact.get("confidence", 1),
                        fact.get("authority_status", "reviewed"),
                    )
                    fact_count += 1
            self.rebuild_rule_index()
            self.rebuild_designations()
            receipt = self.finish(
                generation,
                cycle_ref="authority-bundle-import",
                stage=13,
                world_delta=True,
                observation_delta=True,
                payload={"bundle": report.as_dict(), "facts": fact_count},
            )
        return {"generation": generation, "bundle": report.as_dict(), "receipt": receipt}

    def import_data(self, path):
        """Import one reviewed extension against already-linked authority.

        Initial repository setup must use :meth:`import_bundle` so cross-file
        references are validated before any write.
        """
        return self.import_bundle((path,))["generation"]

    def rebuild_designations(self):
        """Maintenance-only rebuild of the generic designation index."""
        self.db.execute("DELETE FROM designation_index")
        try:
            operator = self.symbol("operator.designation")
        except ValueError:
            return
        app_refs = self.db.execute(
            "SELECT app_ref FROM applications WHERE operator_ref=? ORDER BY app_ref",
            (operator,),
        ).fetchall()
        for row in app_refs:
            self.index_designation_app(str(row["app_ref"]))

    def label_candidates(self, surface, language, kind=None):
        needle = norm_text(surface.strip())
        rows = self.db.execute(
            """SELECT d.*,a.kind,coalesce(s.use_count,0) use_count,coalesce(e.salience,0) salience,
                      coalesce(e.last_turn,0) last_turn
               FROM designation_index d JOIN atoms a ON a.ref=d.target_ref
               LEFT JOIN label_stats s ON s.label_ref=d.label_ref
               LEFT JOIN discourse_entities e ON e.atom_ref=d.target_ref
               WHERE d.language IN (?, 'und') AND d.context_ref IS NULL
                 AND lower(d.surface)=lower(?)""",
            (language, surface.strip()),
        ).fetchall()
        by_target = {}
        current_turn = int(self.db.execute("SELECT coalesce(max(last_turn),0) FROM discourse_entities").fetchone()[0])
        for row in rows:
            if norm_text(row["surface"]) != needle or (kind and row["kind"] != kind):
                continue
            effective_salience = float(row["salience"]) * (0.55 ** max(0, current_turn - int(row["last_turn"])))
            score = (
                float(row["prior"])
                + 0.25 * int(row["preferred"])
                + 0.05 * math.log1p(int(row["use_count"]))
                + 0.8 * effective_salience
                + (0.08 if row["language"] == language else 0)
            )
            old = by_target.get(row["target_ref"])
            if not old or score > old[0]:
                by_target[row["target_ref"]] = (score, row)
        return sorted([(ref, *item) for ref, item in by_target.items()], key=lambda item: (-item[1], item[0]))

    def resolve_label(self, surface, language, kind=None, margin=0.18):
        candidates = self.label_candidates(surface, language, kind)
        if not candidates:
            return None
        if len(candidates) > 1 and candidates[0][1] - candidates[1][1] < margin:
            raise AmbiguousReferent(
                surface,
                [{"ref": item[0], "score": item[1]} for item in candidates[:5]],
            )
        return candidates[0][0]

    def record_use(self, surface, language, ref):
        rows = self.db.execute(
            "SELECT label_ref,surface,preferred,prior FROM designation_index "
            "WHERE target_ref=? AND language IN (?, 'und') ORDER BY preferred DESC,prior DESC",
            (ref, language),
        ).fetchall()
        needle = norm_text(surface)
        row = next((item for item in rows if norm_text(item["surface"]) == needle), None)
        if row:
            self.db.execute(
                "INSERT INTO label_stats VALUES(?,1,?) ON CONFLICT(label_ref) "
                "DO UPDATE SET use_count=use_count+1,last_used=excluded.last_used",
                (row["label_ref"], now()),
            )

    def preferred(self, ref, language, context=None):
        rows = self.db.execute(
            "SELECT d.*,coalesce(s.use_count,0) use_count FROM designation_index d "
            "LEFT JOIN label_stats s ON s.label_ref=d.label_ref "
            "WHERE target_ref=? AND language IN (?, 'und')",
            (ref, language),
        ).fetchall()
        if not rows:
            return ref

        def score(row):
            return (
                float(row["prior"])
                + 0.5 * int(row["preferred"])
                + 0.04 * math.log1p(int(row["use_count"]))
                + (0.1 if row["language"] == language else 0)
                + (0.7 if context and row["context_ref"] == context else 0)
                - (0.15 if context and row["context_ref"] and row["context_ref"] != context else 0)
            )

        return str(max(rows, key=score)["surface"])

    def touch(self, refs):
        """Lazy salience decay: update only mentioned referents."""
        turn = int(self.db.execute("SELECT coalesce(max(last_turn),0)+1 FROM discourse_entities").fetchone()[0])
        for ref in set(refs):
            atom = self.atom(ref)
            if atom and atom["kind"] in {"entity", "participant", "resource", "source", "existential"}:
                row = self.db.execute("SELECT salience,last_turn FROM discourse_entities WHERE atom_ref=?", (ref,)).fetchone()
                old = float(row["salience"]) * (0.55 ** max(0, turn - int(row["last_turn"]))) if row else 0.0
                self.db.execute(
                    "INSERT INTO discourse_entities VALUES(?,?,?) ON CONFLICT(atom_ref) DO UPDATE SET salience=excluded.salience,last_turn=excluded.last_turn",
                    (ref, min(3.0, old + 1.0), turn),
                )

    def frontier(self, surface, reason, details, generation):
        """Accumulate one canonical unresolved target inside Stage 13."""
        payload = dict(details or {})
        payload.pop("frontier_ref", None)
        identity = {
            "target_ref": payload.get("target_ref"),
            "evidence": payload.get("evidence", ()),
            "blocks": payload.get("blocks", ()),
        }
        ref = stable("frontier", norm_text(surface), reason, identity)
        self.db.execute(
            """INSERT INTO frontiers(
                   frontier_ref,surface,reason,details,generation,last_generation,evidence_count,status
               ) VALUES(?,?,?,?,?,?,1,'open')
               ON CONFLICT(frontier_ref) DO UPDATE SET
                 details=excluded.details,
                 last_generation=excluded.last_generation,
                 evidence_count=frontiers.evidence_count+1""",
            (ref, surface, reason, canonical(payload), int(generation), int(generation)),
        )
        return ref

    def find_relation_object(self, subject, relation):
        values = self.relation_objects(subject, relation)
        return values[0] if len(values) == 1 else None

    def user_visible_fact(self, fact):
        if fact.operator == self.symbol("operator.designation"):
            return False
        if fact.operator == "op:relation":
            relation = fact.args.get("role:relation")
            atom = self.atom(relation) if isinstance(relation, str) else None
            if atom and json.loads(atom["metadata"]).get("user_visible") is False:
                return False
        return True
