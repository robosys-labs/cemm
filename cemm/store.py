"""Store: semantic meaning database with authority/world separation.

Ported from v4 MVP (cemm_mvp.py lines 71-269).
"""
from __future__ import annotations
import hashlib, json, math, sqlite3
from pathlib import Path
from cemm.constants import DDL
from cemm.model import now, canonical, stable, norm_text, lit, isvar, isexist, Fact, AmbiguousReferent


class Store:
    SNAP = ("atoms", "operator_roles", "applications", "bindings", "observations", "claims", "proof_links", "rules", "reference_forms", "control_symbols")

    def __init__(self, path):
        self.path = str(path); self.db = sqlite3.connect(self.path); self.db.row_factory = sqlite3.Row; self.db.executescript(DDL)
        if not self.db.execute("SELECT 1 FROM generations").fetchone():
            self.db.execute("INSERT INTO generations VALUES(1,NULL,?,?,?)", (now(), "initial", hashlib.sha256(b"initial").hexdigest())); self.db.commit()

    @property
    def generation(self):
        return int(self.db.execute("SELECT max(generation) FROM generations").fetchone()[0])

    def begin(self, reason):
        g = self.generation + 1; self.db.execute("INSERT INTO generations VALUES(?,?,?,?,?)", (g, g - 1, now(), reason, "pending")); return g

    def finish(self, g):
        h = self.snapshot_hash(); self.db.execute("UPDATE generations SET content_hash=? WHERE generation=?", (h, g)); return h

    def snapshot_hash(self):
        material = []
        for t in self.SNAP:
            cols = [x[1] for x in self.db.execute(f"PRAGMA table_info({t})") if x[1] not in {"observed_at", "generation"}]
            rows = self.db.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {cols[0]}").fetchall(); material.append((t, [dict(r) for r in rows]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()

    def authority_hash(self, upto_generation=None):
        g = self.generation if upto_generation is None else int(upto_generation); material = []
        # Immutable kernel/language-control tables are all authority. Generation-bearing
        # records are pinned to the authority cutoff so later world learning cannot alter attestation.
        for t in ("operator_roles", "reference_forms", "control_symbols"):
            cols = [x[1] for x in self.db.execute(f"PRAGMA table_info({t})")]; rows = self.db.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {cols[0]}").fetchall(); material.append((t, [dict(r) for r in rows]))
        for t in ("atoms", "rules"):
            cols = [x[1] for x in self.db.execute(f"PRAGMA table_info({t})") if x[1] != "generation"]
            where = "generation<=?" + (" AND authority_scope='authority'" if t == "atoms" else "")
            rows = self.db.execute(f"SELECT {','.join(cols)} FROM {t} WHERE {where} ORDER BY {cols[0]}", (g,)).fetchall(); material.append((t, [dict(r) for r in rows]))
        rows = self.db.execute("""SELECT a.app_ref,a.operator_ref,b.role_ref,b.filler_kind,b.filler_value,c.stance,c.authority_status
          FROM applications a JOIN bindings b ON b.app_ref=a.app_ref JOIN claims c ON c.app_ref=a.app_ref JOIN observations o ON o.observation_ref=c.observation_ref
          WHERE a.generation<=? AND o.source_ref IN('seed','reviewed_acquisition') AND c.authority_status IN('reviewed','promoted') ORDER BY a.app_ref,b.role_ref,b.ordinal,c.stance""", (g,)).fetchall()
        material.append(("seed_semantics", [dict(r) for r in rows])); return hashlib.sha256(canonical(material).encode()).hexdigest()

    def exact(self, t, cols, vals, keys, ignore=()):
        try:
            self.db.execute(f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join('?' for _ in vals)})", vals)
        except sqlite3.IntegrityError:
            kv = [vals[cols.index(k)] for k in keys]; row = self.db.execute(f"SELECT * FROM {t} WHERE " + " AND ".join(f"{k}=?" for k in keys), kv).fetchone()
            if not row: raise
            for c, v in zip(cols, vals):
                if c not in ignore and row[c] != v: raise ValueError(f"immutable conflict {t}:{kv}:{c}")

    def atom(self, ref):
        return self.db.execute("SELECT * FROM atoms WHERE ref=?", (ref,)).fetchone()

    def foundational(self, ref):
        a = self.atom(ref); return bool(a and json.loads(a["metadata"]).get("foundational"))

    def symbol(self, role):
        r = self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role=?", (role,)).fetchone()
        if not r: raise ValueError(f"missing control symbol {role}")
        return str(r[0])

    def creatable_kinds(self):
        return {str(r[0]) for r in self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role LIKE 'new_kind.%'")}

    def roles(self, op):
        return {r["role_ref"]: r for r in self.db.execute("SELECT * FROM operator_roles WHERE operator_ref=?", (op,))}

    def encode_value(self, v):
        if isinstance(v, dict) and "literal" in v: return "literal", canonical(v["literal"])
        if isinstance(v, dict) and "app" in v: return "app", str(v["app"])
        return "atom", str(v)

    def decode_value(self, k, v):
        return {"literal": json.loads(v)} if k == "literal" else {"app": v} if k == "app" else v

    def _validate_filler(self, role, v, spec):
        fk, fv = self.encode_value(v); exp = spec["filler_kind"]
        if exp == "state_value":
            if fk == "atom" and not self.atom(fv): raise ValueError(f"unknown state atom {role}:{fv}")
            if fk == "app" and not self.db.execute("SELECT 1 FROM applications WHERE app_ref=?", (fv,)).fetchone(): raise ValueError(f"unknown state app {role}:{fv}")
            if fk not in {"atom", "literal", "app"}: raise ValueError(f"state value class {role}")
            return
        if exp and exp.startswith("literal:"):
            if fk != "literal" or json.loads(fv)["type"] != exp.split(":", 1)[1]: raise ValueError(f"literal kind {role}")
            return
        if fk == "atom" and not self.atom(fv): raise ValueError(f"unknown atom filler {role}:{fv}")
        if fk == "app" and not self.db.execute("SELECT 1 FROM applications WHERE app_ref=?", (fv,)).fetchone(): raise ValueError(f"unknown app filler {role}:{fv}")
        if exp in {"atom", "app"} and fk != exp: raise ValueError(f"filler class {role}")
        if exp and exp not in {"atom", "app"} and not exp.startswith("literal:"):
            a = self.atom(fv) if fk == "atom" else None
            if not a or a["kind"] != exp: raise ValueError(f"filler kind {role}: expected {exp}")

    def validate_app(self, op, args):
        if not self.atom(op): raise ValueError(f"unknown operator {op}")
        specs = self.roles(op)
        for role, v in args.items():
            if role not in specs: raise ValueError(f"{op} disallows {role}")
            self._validate_filler(role, v, specs[role])
        for role, s in specs.items():
            if s["required"] and role not in args: raise ValueError(f"missing {op}:{role}")
        try:
            state_op = self.symbol("operator.state"); dim_role = self.symbol("role.dimension"); val_role = self.symbol("role.value")
        except ValueError:
            state_op = dim_role = val_role = None
        if op == state_op and dim_role in args:
            d = self.atom(str(args[dim_role]))
            if not d or d["kind"] != "state_dimension": raise ValueError(f"invalid state dimension:{args[dim_role]}")
            if val_role in args: self.validate_state_value(str(args[dim_role]), args[val_role])

    def app_signature(self, op, args):
        return stable("app", op, sorted((r, *self.encode_value(v)) for r, v in args.items()))

    def insert_app(self, op, args, g, obs, stance="support", confidence=1., authority="reviewed", valid_from=None):
        self.validate_app(op, args); ar = self.app_signature(op, args); self.db.execute("INSERT OR IGNORE INTO applications VALUES(?,?,?)", (ar, op, g))
        for n, (role, v) in enumerate(sorted(args.items())):
            fk, fv = self.encode_value(v); br = stable("bind", ar, role, fk, fv, n); self.db.execute("INSERT OR IGNORE INTO bindings VALUES(?,?,?,?,?,?)", (br, ar, role, fk, fv, n))
        observed = self.db.execute("SELECT observed_at FROM observations WHERE observation_ref=?", (obs,)).fetchone()
        effective_from = valid_from or (str(observed[0]) if observed else now())
        cr = stable("claim", ar, obs, stance); self.db.execute("INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?)", (cr, ar, obs, stance, float(confidence), authority, effective_from, None, g)); self.db.execute("INSERT OR IGNORE INTO proof_links VALUES(?,?,?,?,?)", (stable("proof", cr), cr, obs, "assert", "[]")); self._supersede_state(ar, op, args, stance, effective_from, obs); return ar

    def _observation_context(self, observation_ref):
        row = self.db.execute("SELECT packet FROM observations WHERE observation_ref=?", (observation_ref,)).fetchone()
        if not row: return None
        try:
            packet = json.loads(row[0]); return packet.get("context_ref") or packet.get("qualifiers", {}).get("context")
        except Exception:
            return None

    def _supersede_state(self, new_ref, op, args, stance, effective_from, observation_ref):
        try:
            state_op = self.symbol("operator.state"); subj = self.symbol("role.subject"); dim = self.symbol("role.dimension"); val = self.symbol("role.value")
        except ValueError:
            return
        if stance != "support" or op != state_op or any(x not in args for x in (subj, dim, val)): return
        d = self.atom(str(args[dim])); meta = json.loads(d["metadata"]) if d else {}
        cardinality = meta.get("cardinality") or ("one" if meta.get("exclusive") else "many")
        if cardinality != "one": return
        new_context = self._observation_context(observation_ref)
        for c in self.state_claim_records(args[subj], args[dim]):
            if c["app_ref"] == new_ref or c["stance"] != "support" or c["valid_to"] is not None: continue
            if canonical(c["value"]) == canonical(args[val]): continue
            if c.get("context_ref") != new_context: continue
            self.db.execute("UPDATE claims SET valid_to=? WHERE claim_ref=?", (effective_from, c["claim_ref"]))

    def type_classes(self, referent_ref):
        rows = self.db.execute("""SELECT DISTINCT bc.filler_value FROM applications a
          JOIN bindings bi ON bi.app_ref=a.app_ref AND bi.role_ref='role:instance' AND bi.filler_kind='atom'
          JOIN bindings bc ON bc.app_ref=a.app_ref AND bc.role_ref='role:class' AND bc.filler_kind='atom'
          JOIN claims c ON c.app_ref=a.app_ref
          WHERE a.operator_ref='op:type' AND bi.filler_value=? AND c.stance='support' AND c.valid_to IS NULL""", (referent_ref,)).fetchall()
        return [str(r[0]) for r in rows]

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
        return [str(r[0]) for r in self.db.execute(sql, params).fetchall()]

    def state_dimension_domain_type(self, dimension_ref):
        try: relation = self.symbol("profile.dimension_domain_relation")
        except ValueError: return None
        domains = self.relation_objects(dimension_ref, relation, authority_only=True)
        if len(domains) != 1: return None
        a = self.atom(domains[0])
        return json.loads(a["metadata"]).get("domain_type") if a else None

    def validate_state_value(self, dimension_ref, value):
        d = self.atom(dimension_ref); meta = json.loads(d["metadata"]) if d else {}
        fk, fv = self.encode_value(value); domain = self.state_dimension_domain_type(dimension_ref) or meta.get("domain_type")
        allowed_fillers = set(meta.get("value_filler_kinds", []))
        if allowed_fillers and fk not in allowed_fillers: raise ValueError(f"state value filler {dimension_ref}:{fk}")
        if fk == "atom":
            a = self.atom(fv); allowed_kinds = set(meta.get("value_atom_kinds", []))
            if allowed_kinds and (not a or a["kind"] not in allowed_kinds): raise ValueError(f"state value atom kind {dimension_ref}:{fv}")
            if domain == "categorical" and (not a or a["kind"] != "value"): raise ValueError(f"categorical state requires value atom:{dimension_ref}")
        elif fk == "literal":
            q = json.loads(fv); expected = meta.get("literal_type")
            if expected and q.get("type") != expected: raise ValueError(f"state literal type {dimension_ref}:{q.get('type')}")
            if domain == "categorical": raise ValueError(f"categorical state requires semantic value atom:{dimension_ref}")
            if domain == "continuous" and q.get("type") not in {"int", "float"}: raise ValueError(f"continuous state requires numeric literal:{dimension_ref}")
            x = q.get("value")
            if isinstance(x, (int, float)):
                if "min" in meta and x < meta["min"]: raise ValueError(f"state value below minimum:{dimension_ref}")
                if "max" in meta and x > meta["max"]: raise ValueError(f"state value above maximum:{dimension_ref}")

    def state_claim_records(self, subject_ref=None, dimension_ref=None):
        state_op = self.symbol("operator.state"); subj = self.symbol("role.subject"); dim = self.symbol("role.dimension"); val = self.symbol("role.value")
        sql = """SELECT a.app_ref,c.claim_ref,c.stance,c.confidence,c.authority_status,c.valid_from,c.valid_to,c.generation,
          bs.filler_value subject_ref,bd.filler_value dimension_ref,o.observation_ref,o.source_ref,o.observed_at,o.packet,
          bv.filler_kind value_kind,bv.filler_value value_data,p.parent_refs
          FROM applications a
          JOIN bindings bs ON bs.app_ref=a.app_ref AND bs.role_ref=? AND bs.filler_kind='atom'
          JOIN bindings bd ON bd.app_ref=a.app_ref AND bd.role_ref=? AND bd.filler_kind='atom'
          JOIN bindings bv ON bv.app_ref=a.app_ref AND bv.role_ref=?
          JOIN claims c ON c.app_ref=a.app_ref JOIN observations o ON o.observation_ref=c.observation_ref
          LEFT JOIN proof_links p ON p.subject_ref=c.claim_ref WHERE a.operator_ref=?"""
        params = [subj, dim, val, state_op]
        if subject_ref is not None: sql += " AND bs.filler_value=?"; params.append(subject_ref)
        if dimension_ref is not None: sql += " AND bd.filler_value=?"; params.append(dimension_ref)
        out = []
        for r in self.db.execute(sql, params).fetchall():
            try: packet = json.loads(r["packet"])
            except Exception: packet = {}
            out.append({
                "app_ref": str(r["app_ref"]), "claim_ref": str(r["claim_ref"]), "subject_ref": str(r["subject_ref"]), "dimension_ref": str(r["dimension_ref"]),
                "value": self.decode_value(r["value_kind"], r["value_data"]), "stance": str(r["stance"]), "confidence": float(r["confidence"]),
                "authority_status": str(r["authority_status"]), "valid_from": r["valid_from"], "valid_to": r["valid_to"], "generation": int(r["generation"]),
                "observation_ref": str(r["observation_ref"]), "source_ref": str(r["source_ref"]), "observed_at": str(r["observed_at"]),
                "context_ref": packet.get("context_ref") or packet.get("qualifiers", {}).get("context"), "proof_parents": json.loads(r["parent_refs"] or "[]"),
            })
        return out

    def base_facts(self):
        out = []
        for a in self.db.execute("SELECT * FROM applications ORDER BY app_ref"):
            args = {}
            for b in self.db.execute("SELECT * FROM bindings WHERE app_ref=? ORDER BY role_ref,ordinal", (a["app_ref"],)):
                args[b["role_ref"]] = self.decode_value(b["filler_kind"], b["filler_value"])
            rows = self.db.execute("SELECT stance,confidence FROM claims WHERE app_ref=? AND valid_to IS NULL", (a["app_ref"],)).fetchall(); st = {r["stance"] for r in rows}
            if "support" in st: out.append(Fact(a["app_ref"], a["operator_ref"], args, "support", max(float(r["confidence"]) for r in rows if r["stance"] == "support")))
            if "deny" in st: out.append(Fact(a["app_ref"], a["operator_ref"], args, "deny", max(float(r["confidence"]) for r in rows if r["stance"] == "deny")))
        return out

    def add_observation(self, surface_, packet, lang, source, g, confidence=.95, occurrence_ref=None):
        ref = stable("obs", surface_, lang, source, packet, occurrence_ref or "dedup"); self.db.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?)", (ref, surface_, "language", lang, source, now(), canonical(packet), confidence, g)); return ref

    def validate_rule(self, x):
        ants = list(x.get("if", [])); cons = list(x.get("then", []))
        if not ants or not cons: raise ValueError("rule requires antecedent and consequent")
        if not 0 < float(x.get("confidence", 1)) <= 1: raise ValueError("rule confidence out of range")
        bound = {v for c in ants for v in c.get("args", {}).values() if isvar(v)}
        if any(isexist(v) for c in ants for v in c.get("args", {}).values()): raise ValueError("existential witness cannot appear in antecedent")
        for c in ants + cons:
            op = c.get("operator")
            if not self.atom(op): raise ValueError(f"rule unknown operator {op}")
            specs = self.roles(op)
            for role, v in c.get("args", {}).items():
                if role not in specs: raise ValueError(f"rule {op} disallows {role}")
                if isinstance(v, str) and (isvar(v) or isexist(v)):
                    if c in cons and isvar(v) and v not in bound: raise ValueError(f"unbound consequent variable {v}")
                    continue
                self._validate_filler(role, v, specs[role])
            if c in cons:
                for role, r in specs.items():
                    if r["required"] and role not in c.get("args", {}): raise ValueError(f"rule consequent missing {op}:{role}")

    def infer_state_dimension(self, value_ref):
        try:
            rv = self.symbol("policy.state_value_relation"); rd = self.symbol("policy.state_dimension_relation")
        except ValueError:
            return None
        specs = [f.args.get("role:subject") for f in self.base_facts() if f.operator == "op:relation" and f.stance == "support" and f.args.get("role:relation") == rv and f.args.get("role:object") == value_ref]
        dims = {f.args.get("role:object") for f in self.base_facts() if f.operator == "op:relation" and f.stance == "support" and f.args.get("role:subject") in specs and f.args.get("role:relation") == rd}
        return next(iter(dims)) if len(dims) == 1 else None

    def upsert_rule_candidate(self, rule, g, confidence=.9, min_evidence=2):
        self.validate_rule(rule); ant = canonical(rule["if"]); con = canonical(rule["then"]); kind = rule.get("rule_kind", "definition"); ref = stable("rulecand", kind, ant, con)
        row = self.db.execute("SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)).fetchone()
        if row: self.db.execute("UPDATE rule_candidates SET evidence_count=evidence_count+1,last_generation=?,confidence=max(confidence,?) WHERE candidate_ref=?", (g, float(confidence), ref))
        else: self.db.execute("INSERT INTO rule_candidates VALUES(?,?,?,?,?,?,?,?,?)", (ref, kind, ant, con, 1, "provisional", float(confidence), g, g))
        row = self.db.execute("SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)).fetchone(); promoted = False
        if int(row["evidence_count"]) >= int(min_evidence) and row["status"] != "promoted":
            rr = stable("rule", kind, ant, con); self.db.execute("INSERT OR IGNORE INTO rules VALUES(?,?,?,?,?,?,?)", (rr, kind, ant, con, float(row["confidence"]), "promoted", g)); self.db.execute("UPDATE rule_candidates SET status='promoted' WHERE candidate_ref=?", (ref,)); promoted = True
        return ref, promoted

    def add_rule_candidate(self, ref, kind, ant, con, confidence, g):
        """Insert or increment a rule candidate by explicit ref (no validation/promotion)."""
        row = self.db.execute("SELECT * FROM rule_candidates WHERE candidate_ref=?", (ref,)).fetchone()
        if row:
            self.db.execute("UPDATE rule_candidates SET evidence_count=evidence_count+1,last_generation=?,confidence=max(confidence,?) WHERE candidate_ref=?", (g, float(confidence), ref))
        else:
            self.db.execute("INSERT INTO rule_candidates VALUES(?,?,?,?,?,?,?,?,?)", (ref, kind, ant, con, 1, "provisional", float(confidence), g, g))
        return ref

    def import_data(self, path):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        with self.db:
            g = self.begin(f"import:{Path(path).name}")
            for x in d.get("atoms", []): self.exact("atoms", ["ref", "kind", "metadata", "generation"], [x["ref"], x["kind"], canonical(x.get("metadata", {})), g], ["ref"], {"generation"})
            for x in d.get("operator_roles", []):
                if x.get("cardinality", "one") != "one": raise ValueError("MVP supports one filler per role; represent multiplicity with repeated applications")
                self.exact("operator_roles", ["operator_ref", "role_ref", "required", "cardinality", "filler_kind"], [x["operator_ref"], x["role_ref"], int(x.get("required", False)), "one", x.get("filler_kind")], ["operator_ref", "role_ref"])
            for k, v in d.get("control_symbols", {}).items(): self.exact("control_symbols", ["role", "semantic_ref"], [k, v], ["role"])
            for x in d.get("reference_forms", []): self.exact("reference_forms", ["language", "surface", "features", "bound_ref", "weight"], [x.get("language", "en"), x["surface"], canonical(x.get("features", {})), x.get("bound_ref"), float(x.get("weight", 1))], ["language", "surface", "bound_ref"])
            for x in d.get("rules", []):
                self.validate_rule(x); rk = x.get("rule_kind", "entailment"); ant = canonical(x.get("if", [])); con = canonical(x.get("then", []))
                if self.db.execute("SELECT 1 FROM rules WHERE rule_kind=? AND antecedent=? AND consequent=?", (rk, ant, con)).fetchone(): continue
                self.exact("rules", ["rule_ref", "rule_kind", "antecedent", "consequent", "confidence", "authority_status", "generation"], [x["rule_ref"], rk, ant, con, float(x.get("confidence", 1)), x.get("authority_status", "reviewed"), g], ["rule_ref"], {"generation"})
            for x in d.get("facts", []):
                obs = self.add_observation(x.get("source_text", x.get("fact_ref", x["operator"])), x, "und", x.get("source_ref", "seed"), g, float(x.get("confidence", 1))); self.insert_app(x["operator"], x.get("args", {}), g, obs, x.get("stance", "support"), x.get("confidence", 1), x.get("authority_status", "reviewed"))
            self.rebuild_designations(); self.finish(g)
        return g

    def rebuild_designations(self):
        self.db.execute("DELETE FROM designation_index")
        try:
            op = self.symbol("operator.designation"); roles = {k: self.symbol(f"designation.{k}") for k in ("target", "type", "surface", "language", "script", "prior", "preferred", "context")}
        except ValueError:
            return
        for f in self.base_facts():
            if f.operator != op or f.stance != "support": continue

            def v(k, default=None):
                x = f.args.get(roles[k], default); return x.get("literal", {}).get("value") if isinstance(x, dict) and "literal" in x else x

            if not v("target") or not v("surface"): continue
            self.db.execute("INSERT OR REPLACE INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)", (f.ref, str(v("target")), str(v("type", "label:default")), str(v("surface")), str(v("language", "und")), str(v("script", "Zyyy")), float(v("prior", 1)), int(bool(v("preferred", False))), v("context")))

    def label_candidates(self, surf, lang, kind=None):
        rows = self.db.execute("""SELECT d.*,a.kind,coalesce(s.use_count,0) use_count,coalesce(e.salience,0) salience FROM designation_index d JOIN atoms a ON a.ref=d.target_ref LEFT JOIN label_stats s ON s.label_ref=d.label_ref LEFT JOIN discourse_entities e ON e.atom_ref=d.target_ref WHERE d.language IN (?, 'und')""", (lang,)).fetchall(); by = {}; needle = norm_text(surf.strip())
        for r in rows:
            if r["context_ref"] is not None: continue
            if norm_text(r["surface"]) != needle or (kind and r["kind"] != kind): continue
            score = float(r["prior"]) + .25 * int(r["preferred"]) + .05 * math.log1p(int(r["use_count"])) + .8 * float(r["salience"]) + (.08 if r["language"] == lang else 0); old = by.get(r["target_ref"])
            if not old or score > old[0]: by[r["target_ref"]] = (score, r)
        return sorted([(ref, *x) for ref, x in by.items()], key=lambda x: (-x[1], x[0]))

    def resolve_label(self, surf, lang, kind=None, margin=.18):
        cs = self.label_candidates(surf, lang, kind)
        if not cs: return None
        if len(cs) > 1 and cs[0][1] - cs[1][1] < margin: raise AmbiguousReferent(surf, [{"ref": x[0], "score": x[1]} for x in cs[:5]])
        return cs[0][0]

    def record_use(self, surf, lang, ref):
        rows = self.db.execute("SELECT label_ref,surface,preferred,prior FROM designation_index WHERE target_ref=? AND language IN (?, 'und') ORDER BY preferred DESC,prior DESC", (ref, lang)).fetchall(); needle = norm_text(surf); r = next((x for x in rows if norm_text(x["surface"]) == needle), None)
        if r: self.db.execute("INSERT INTO label_stats VALUES(?,1,?) ON CONFLICT(label_ref) DO UPDATE SET use_count=use_count+1,last_used=excluded.last_used", (r["label_ref"], now()))

    def preferred(self, ref, lang, context=None):
        rows = self.db.execute("SELECT d.*,coalesce(s.use_count,0) use_count FROM designation_index d LEFT JOIN label_stats s ON s.label_ref=d.label_ref WHERE target_ref=? AND language IN (?, 'und')", (ref, lang)).fetchall()
        if not rows: return ref

        def score(r):
            return float(r["prior"]) + .5 * int(r["preferred"]) + .04 * math.log1p(int(r["use_count"])) + (.1 if r["language"] == lang else 0) + (.7 if context and r["context_ref"] == context else 0) - (.15 if context and r["context_ref"] and r["context_ref"] != context else 0)

        return str(max(rows, key=score)["surface"])

    def touch(self, refs):
        self.db.execute("UPDATE discourse_entities SET salience=salience*.55"); turn = int(self.db.execute("SELECT coalesce(max(last_turn),0)+1 FROM discourse_entities").fetchone()[0])
        for ref in set(refs):
            a = self.atom(ref)
            if a and a["kind"] in {"entity", "participant", "resource", "source", "existential"}: self.db.execute("INSERT INTO discourse_entities VALUES(?,1,?) ON CONFLICT(atom_ref) DO UPDATE SET salience=min(3,salience+1),last_turn=excluded.last_turn", (ref, turn))

    def frontier(self, surface_, reason, details):
        ref = stable("frontier", surface_, reason, details, self.generation); self.db.execute("INSERT OR IGNORE INTO frontiers VALUES(?,?,?,?,?)", (ref, surface_, reason, canonical(details), self.generation)); self.db.commit(); return ref

    def find_relation_object(self, subject, relation):
        for f in self.base_facts():
            if f.stance == "support" and f.operator == "op:relation" and f.args.get("role:subject") == subject and f.args.get("role:relation") == relation: return f.args.get("role:object")
        return None

    def user_visible_fact(self, f):
        if f.operator == self.symbol("operator.designation"): return False
        if f.operator == "op:relation":
            rel = f.args.get("role:relation"); a = self.atom(rel) if isinstance(rel, str) else None
            if a and json.loads(a["metadata"]).get("user_visible") is False: return False
        return True
