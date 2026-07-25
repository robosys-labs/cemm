"""Semantic store with exact authority, mutable world and epistemic separation."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path

from cemm.constants import DDL
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
        self.db.executescript(DDL)
        if not self.db.execute("SELECT 1 FROM generations").fetchone():
            self.db.execute(
                "INSERT INTO generations VALUES(1,NULL,?,?,?)",
                (now(), "initial", hashlib.sha256(b"initial").hexdigest()),
            )
            self.db.commit()

    @property
    def generation(self):
        return int(self.db.execute("SELECT max(generation) FROM generations").fetchone()[0])

    def begin(self, reason):
        generation = self.generation + 1
        self.db.execute(
            "INSERT INTO generations VALUES(?,?,?,?,?)",
            (generation, generation - 1, now(), reason, "pending"),
        )
        return generation

    def finish(self, generation):
        content_hash = self.snapshot_hash()
        self.db.execute(
            "UPDATE generations SET content_hash=? WHERE generation=?",
            (content_hash, generation),
        )
        return content_hash

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

    def validate_app(self, operator, args):
        if not self.atom(operator):
            raise ValueError(f"unknown operator {operator}")
        specs = self.roles(operator)
        for role, value in args.items():
            if role not in specs:
                raise ValueError(f"{operator} disallows {role}")
            self._validate_filler(role, value, specs[role])
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
        output = []
        for application in self.db.execute("SELECT * FROM applications ORDER BY app_ref"):
            args = {}
            for binding in self.db.execute(
                "SELECT * FROM bindings WHERE app_ref=? ORDER BY role_ref,ordinal",
                (application["app_ref"],),
            ):
                args[binding["role_ref"]] = self.decode_value(
                    binding["filler_kind"], binding["filler_value"]
                )
            rows = self.db.execute(
                "SELECT stance,confidence FROM claims WHERE app_ref=? AND valid_to IS NULL",
                (application["app_ref"],),
            ).fetchall()
            stances = {row["stance"] for row in rows}
            if "support" in stances:
                output.append(
                    Fact(
                        application["app_ref"],
                        application["operator_ref"],
                        args,
                        "support",
                        max(float(row["confidence"]) for row in rows if row["stance"] == "support"),
                    )
                )
            if "deny" in stances:
                output.append(
                    Fact(
                        application["app_ref"],
                        application["operator_ref"],
                        args,
                        "deny",
                        max(float(row["confidence"]) for row in rows if row["stance"] == "deny"),
                    )
                )
        return output

    def add_observation(self, surface, packet, language, source, generation, confidence=0.95, occurrence_ref=None):
        ref = stable("obs", surface, language, source, packet, occurrence_ref or "dedup")
        self.db.execute(
            "INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?)",
            (ref, surface, "language", language, source, now(), canonical(packet), confidence, generation),
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
            if clause in consequent:
                for role, spec in specs.items():
                    if spec["required"] and role not in clause.get("args", {}):
                        raise ValueError(f"rule consequent missing {operator}:{role}")

    def infer_state_dimension(self, value_ref):
        try:
            value_relation = self.symbol("policy.state_value_relation")
            dimension_relation = self.symbol("policy.state_dimension_relation")
        except ValueError:
            return None
        specs = [
            fact.args.get("role:subject")
            for fact in self.base_facts()
            if fact.operator == "op:relation"
            and fact.stance == "support"
            and fact.args.get("role:relation") == value_relation
            and fact.args.get("role:object") == value_ref
        ]
        dimensions = {
            fact.args.get("role:object")
            for fact in self.base_facts()
            if fact.operator == "op:relation"
            and fact.stance == "support"
            and fact.args.get("role:subject") in specs
            and fact.args.get("role:relation") == dimension_relation
        }
        return next(iter(dimensions)) if len(dimensions) == 1 else None

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
                "INSERT OR IGNORE INTO rules VALUES(?,?,?,?,?,?,?)",
                (rule_ref, kind, antecedent, consequent, float(row["confidence"]), "promoted", generation),
            )
            self.db.execute(
                "UPDATE rule_candidates SET status='promoted' WHERE candidate_ref=?", (ref,)
            )
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

    def import_data(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        with self.db:
            generation = self.begin(f"import:{Path(path).name}")
            for atom in data.get("atoms", []):
                self.exact(
                    "atoms",
                    ["ref", "kind", "metadata", "generation"],
                    [atom["ref"], atom["kind"], canonical(atom.get("metadata", {})), generation],
                    ["ref"],
                    {"generation"},
                )
            for item in data.get("operator_roles", []):
                if item.get("cardinality", "one") != "one":
                    raise ValueError("MVP supports one filler per role; represent multiplicity with repeated applications")
                self.exact(
                    "operator_roles",
                    ["operator_ref", "role_ref", "required", "cardinality", "filler_kind"],
                    [item["operator_ref"], item["role_ref"], int(item.get("required", False)), "one", item.get("filler_kind")],
                    ["operator_ref", "role_ref"],
                )
            for role, ref in data.get("control_symbols", {}).items():
                self.exact("control_symbols", ["role", "semantic_ref"], [role, ref], ["role"])
            for item in data.get("reference_forms", []):
                self.exact(
                    "reference_forms",
                    ["language", "surface", "features", "bound_ref", "weight"],
                    [item.get("language", "en"), item["surface"], canonical(item.get("features", {})), item.get("bound_ref"), float(item.get("weight", 1))],
                    ["language", "surface", "bound_ref"],
                )
            for rule in data.get("rules", []):
                self.validate_rule(rule)
                kind = rule.get("rule_kind", "entailment")
                antecedent = canonical(rule.get("if", []))
                consequent = canonical(rule.get("then", []))
                if self.db.execute(
                    "SELECT 1 FROM rules WHERE rule_kind=? AND antecedent=? AND consequent=?",
                    (kind, antecedent, consequent),
                ).fetchone():
                    continue
                self.exact(
                    "rules",
                    ["rule_ref", "rule_kind", "antecedent", "consequent", "confidence", "authority_status", "generation"],
                    [rule["rule_ref"], kind, antecedent, consequent, float(rule.get("confidence", 1)), rule.get("authority_status", "reviewed"), generation],
                    ["rule_ref"],
                    {"generation"},
                )
            for fact in data.get("facts", []):
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
            self.rebuild_designations()
            self.finish(generation)
        return generation

    def rebuild_designations(self):
        self.db.execute("DELETE FROM designation_index")
        try:
            operator = self.symbol("operator.designation")
            roles = {
                key: self.symbol(f"designation.{key}")
                for key in ("target", "type", "surface", "language", "script", "prior", "preferred", "context")
            }
        except ValueError:
            return
        for fact in self.base_facts():
            if fact.operator != operator or fact.stance != "support":
                continue

            def value(key, default=None):
                item = fact.args.get(roles[key], default)
                return item.get("literal", {}).get("value") if isinstance(item, dict) and "literal" in item else item

            if not value("target") or not value("surface"):
                continue
            self.db.execute(
                "INSERT OR REPLACE INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    fact.ref,
                    str(value("target")),
                    str(value("type", "label:default")),
                    str(value("surface")),
                    str(value("language", "und")),
                    str(value("script", "Zyyy")),
                    float(value("prior", 1)),
                    int(bool(value("preferred", False))),
                    value("context"),
                ),
            )

    def label_candidates(self, surface, language, kind=None):
        rows = self.db.execute(
            """SELECT d.*,a.kind,coalesce(s.use_count,0) use_count,coalesce(e.salience,0) salience
               FROM designation_index d JOIN atoms a ON a.ref=d.target_ref
               LEFT JOIN label_stats s ON s.label_ref=d.label_ref
               LEFT JOIN discourse_entities e ON e.atom_ref=d.target_ref
               WHERE d.language IN (?, 'und')""",
            (language,),
        ).fetchall()
        by_target = {}
        needle = norm_text(surface.strip())
        for row in rows:
            if row["context_ref"] is not None:
                continue
            if norm_text(row["surface"]) != needle or (kind and row["kind"] != kind):
                continue
            score = (
                float(row["prior"])
                + 0.25 * int(row["preferred"])
                + 0.05 * math.log1p(int(row["use_count"]))
                + 0.8 * float(row["salience"])
                + (0.08 if row["language"] == language else 0)
            )
            old = by_target.get(row["target_ref"])
            if not old or score > old[0]:
                by_target[row["target_ref"]] = (score, row)
        return sorted(
            [(ref, *item) for ref, item in by_target.items()],
            key=lambda item: (-item[1], item[0]),
        )

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
        self.db.execute("UPDATE discourse_entities SET salience=salience*.55")
        turn = int(
            self.db.execute(
                "SELECT coalesce(max(last_turn),0)+1 FROM discourse_entities"
            ).fetchone()[0]
        )
        for ref in set(refs):
            atom = self.atom(ref)
            if atom and atom["kind"] in {"entity", "participant", "resource", "source", "existential"}:
                self.db.execute(
                    "INSERT INTO discourse_entities VALUES(?,1,?) ON CONFLICT(atom_ref) "
                    "DO UPDATE SET salience=min(3,salience+1),last_turn=excluded.last_turn",
                    (ref, turn),
                )

    def frontier(self, surface, reason, details):
        ref = stable("frontier", surface, reason, details, self.generation)
        self.db.execute(
            "INSERT OR IGNORE INTO frontiers VALUES(?,?,?,?,?)",
            (ref, surface, reason, canonical(details), self.generation),
        )
        self.db.commit()
        return ref

    def find_relation_object(self, subject, relation):
        for fact in self.base_facts():
            if (
                fact.stance == "support"
                and fact.operator == "op:relation"
                and fact.args.get("role:subject") == subject
                and fact.args.get("role:relation") == relation
            ):
                return fact.args.get("role:object")
        return None

    def user_visible_fact(self, fact):
        if fact.operator == self.symbol("operator.designation"):
            return False
        if fact.operator == "op:relation":
            relation = fact.args.get("role:relation")
            atom = self.atom(relation) if isinstance(relation, str) else None
            if atom and json.loads(atom["metadata"]).get("user_visible") is False:
                return False
        return True
