from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cemm_mvp import AmbiguousReferent, Delexer, Inference, Runtime, Store, canonical  # noqa:E402

BASE = ROOT / "knowledge" / "base.json"
FAMILY = ROOT / "knowledge" / "family_knowledge.json"


def make_store(*, family: bool = True):
    td = tempfile.TemporaryDirectory()
    s = Store(Path(td.name) / "mvp.sqlite")
    s.import_data(BASE)
    if family:
        s.import_data(FAMILY)
    return td, s


def rules_in_proof(node):
    if not node:
        return set()
    out = {node["rule_ref"]} if node.get("rule_ref") else set()
    for p in node.get("parents", []):
        out |= rules_in_proof(p)
    return out


class MVPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Train once and populate the content-hash keyed model cache.
        td, s = make_store()
        Runtime(s)
        s.db.close(); td.cleanup()

    def test_kernel_has_no_family_domain_hardcoding(self):
        src = (ROOT / "cemm_mvp.py").read_text(encoding="utf-8").lower()
        for word in (
            "mother_in_law", "mother-in-law", "mother in-law", "spouse",
            "wife", "husband", "married", "family_relative", "partner-spouse",
            "president", "doctor",
        ):
            self.assertNotIn(word, src)

    def test_domain_import_does_not_expand_operator_schema(self):
        td, s = make_store(family=False)
        try:
            before_ops = s.db.execute("SELECT count(*) FROM atoms WHERE kind='operator'").fetchone()[0]
            before_roles = s.db.execute("SELECT count(*) FROM operator_roles").fetchone()[0]
            s.import_data(FAMILY)
            after_ops = s.db.execute("SELECT count(*) FROM atoms WHERE kind='operator'").fetchone()[0]
            after_roles = s.db.execute("SELECT count(*) FROM operator_roles").fetchone()[0]
            self.assertEqual((before_ops, before_roles), (after_ops, after_roles))
            self.assertEqual(before_ops, 5)
            self.assertEqual(before_roles, 20)
        finally:
            s.db.close(); td.cleanup()

    def test_surface_variants_converge_without_new_semantic_programs(self):
        for text in ("My mother in-law arrived today.", "My mother-in-law came today.", "My mother in law arrived today."):
            td, s = make_store()
            try:
                rt=Runtime(s); result=rt.process(text)
                self.assertEqual(result["status"],"learned",text)
                self.assertEqual(result["packet"]["apps"][0]["args"]["role:relation"],"rel:mother_in_law")
                self.assertEqual(result["packet"]["apps"][1]["args"]["role:type"],"event:arrive")
                self.assertEqual(rt.process("Am I married?")["result"],"supported")
            finally:
                s.db.close(); td.cleanup()

    def test_family_observation_infers_marriage_with_proof(self):
        td, s = make_store()
        try:
            rt = Runtime(s)
            learned = rt.process("My mother in-law arrived today.")
            self.assertEqual(learned["status"], "learned")
            ans = rt.process("Am I married?")
            self.assertEqual(ans["result"], "supported")
            self.assertEqual(ans["response"], "Yes.")
            rs = rules_in_proof(ans["proof"])
            self.assertIn("rule:mil-decompose", rs)
            self.assertIn("rule:subrelation-inheritance", rs)
            self.assertIn("rule:relation-object-state", rs)
        finally:
            s.db.close(); td.cleanup()

    def test_inference_is_ephemeral_and_repeated_queries_do_not_bloat_store(self):
        td, s = make_store()
        try:
            rt = Runtime(s); rt.process("My mother in-law arrived today.")
            def counts():
                return tuple(s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("applications","bindings","claims","proof_links"))
            before = counts()
            answers = [rt.process("Am I married?") for _ in range(5)]
            after = counts()
            self.assertEqual(before, after)
            self.assertTrue(all(a["result"] == "supported" for a in answers))
            self.assertGreater(answers[0]["ephemeral_fact_count"], 0)
        finally:
            s.db.close(); td.cleanup()

    def test_causal_rule_is_not_silently_asserted_as_actual_truth(self):
        td, s = make_store()
        try:
            rt = Runtime(s); learned = rt.process("My mother in-law arrived today.")
            mil = learned["packet"]["apps"][0]["args"]["role:subject"]
            facts, _ = Inference(s).closure()
            present = [f for f in facts if f.operator == "op:state" and
                       f.args.get("role:subject") == mil and
                       f.args.get("role:dimension") == "dim:location_status" and
                       f.args.get("role:value") == "value:present"]
            self.assertEqual(present, [])
            self.assertEqual(s.db.execute("SELECT rule_kind FROM rules WHERE rule_ref='rule:arrival-presence-causal'").fetchone()[0], "causal")
        finally:
            s.db.close(); td.cleanup()

    def test_mother_role_reuses_type_lattice(self):
        td, s = make_store()
        try:
            rt = Runtime(s); learned = rt.process("My mother in-law arrived today.")
            mil = learned["packet"]["apps"][0]["args"]["role:subject"]
            facts, _ = Inference(s).closure()
            classes = {f.args["role:class"] for f in facts if f.operator == "op:type" and f.args.get("role:instance") == mil}
            self.assertTrue({"concept:female", "concept:human", "concept:living_entity"}.issubset(classes))
            # No concept-specific mother->human/living rule should exist.
            refs = {r[0] for r in s.db.execute("SELECT rule_ref FROM rules")}
            self.assertNotIn("rule:mother-human", refs)
            self.assertNotIn("rule:mother-living", refs)
        finally:
            s.db.close(); td.cleanup()

    def test_wife_semantics_compose_through_generic_meta_rules(self):
        td, s = make_store()
        try:
            with s.db:
                g = s.begin("test-wife")
                obs = s.add_observation("semantic test", {}, "und", "test", g)
                s.insert_app("op:relation", {"role:subject":"entity:ada","role:relation":"rel:wife","role:object":"participant:user"}, g, obs)
                s.finish(g)
            facts, _ = Inference(s).closure()
            def has(op, **kw):
                return any(f.operator == op and all(f.args.get(k) == v for k,v in kw.items()) for f in facts)
            self.assertTrue(has("op:relation", **{"role:subject":"entity:ada","role:relation":"rel:spouse","role:object":"participant:user"}))
            self.assertTrue(has("op:type", **{"role:instance":"entity:ada","role:class":"concept:female"}))
            self.assertTrue(has("op:type", **{"role:instance":"entity:ada","role:class":"concept:human"}))
            self.assertTrue(has("op:type", **{"role:instance":"entity:ada","role:class":"concept:living_entity"}))
            self.assertTrue(has("op:state", **{"role:subject":"entity:ada","role:dimension":"dim:marriage_eligibility","role:value":"value:eligible"}))
            self.assertTrue(has("op:state", **{"role:subject":"participant:user","role:dimension":"dim:marital_status","role:value":"value:married"}))
        finally:
            s.db.close(); td.cleanup()

    def test_same_name_entities_remain_ambiguous_until_context_resolves(self):
        td, s = make_store()
        try:
            with self.assertRaises(AmbiguousReferent):
                s.resolve_label("Alex Kim", "en")
            self.assertEqual(s.resolve_label("Alex J. Kim", "en"), "entity:alex_a")
            s.touch(["entity:alex_a"])
            self.assertEqual(s.resolve_label("Alex Kim", "en"), "entity:alex_a")
        finally:
            s.db.close(); td.cleanup()

    def test_designations_are_semantic_facts_and_dynamic_ranking_is_not_authority(self):
        td, s = make_store()
        try:
            des_op = s.symbol("operator.designation")
            exact_count = s.db.execute("SELECT count(*) FROM applications WHERE operator_ref=?", (des_op,)).fetchone()[0]
            index_count = s.db.execute("SELECT count(*) FROM designation_index").fetchone()[0]
            self.assertEqual(exact_count, index_count)
            before = s.snapshot_hash()
            s.record_use("Alex J. Kim", "en", "entity:alex_a")
            s.touch(["entity:alex_a"])
            self.assertEqual(before, s.snapshot_hash())
        finally:
            s.db.close(); td.cleanup()

    def test_multisentence_coreference_reuses_same_exact_entity(self):
        td, s = make_store()
        try:
            rt = Runtime(s)
            result = rt.process("Ada is a doctor. She arrived today.")
            self.assertEqual(result["status"], "learned")
            facts = s.base_facts()
            self.assertTrue(any(f.operator=="op:type" and f.args.get("role:instance")=="entity:ada" and f.args.get("role:class")=="concept:doctor" for f in facts))
            self.assertTrue(any(f.operator=="op:event" and f.args.get("role:actor")=="entity:ada" and f.args.get("role:type")=="event:arrive" for f in facts))
            answer = rt.process("Who is Ada?")
            self.assertIn("Ada is a doctor.", answer["response"])
        finally:
            s.db.close(); td.cleanup()

    def test_learned_language_program_contains_only_foundational_structure(self):
        td, s = make_store()
        try:
            packet, news, uses, trace = Runtime(s).i.parse("My mother in-law arrived today.")
            self.assertIsNotNone(packet)
            program = trace["program"].lower()
            for forbidden in ("mother", "married", "spouse", "partner", "arrive", "today", "family"):
                self.assertNotIn(forbidden, program)
            self.assertIn("op:relation", program)
            self.assertIn("op:event", program)
            self.assertTrue(trace["verified"])
        finally:
            s.db.close(); td.cleanup()

    def test_universal_role_typing_rejects_wrong_semantic_kind(self):
        td, s = make_store()
        try:
            with s.db:
                g=s.begin("bad-kind"); obs=s.add_observation("bad",{},"und","test",g)
                with self.assertRaises(ValueError):
                    s.insert_app("op:relation", {"role:subject":"entity:ada","role:relation":"concept:doctor","role:object":"participant:user"}, g, obs)
        finally:
            s.db.rollback(); s.db.close(); td.cleanup()

    def test_exclusive_state_dimension_supersedes_previous_state_generically(self):
        td, s = make_store()
        try:
            with s.db:
                g=s.begin("state-supersession")
                s.exact("atoms", ["ref","kind","metadata","generation"], ["value:single","value","{}",g], ["ref"], {"generation"})
                o1=s.add_observation("state one",{},"und","test",g)
                a1=s.insert_app("op:state", {"role:subject":"participant:user","role:dimension":"dim:marital_status","role:value":"value:married"},g,o1)
                o2=s.add_observation("state two",{},"und","test",g)
                a2=s.insert_app("op:state", {"role:subject":"participant:user","role:dimension":"dim:marital_status","role:value":"value:single"},g,o2)
                s.finish(g)
            self.assertIsNotNone(s.db.execute("SELECT valid_to FROM claims WHERE app_ref=?",(a1,)).fetchone()[0])
            self.assertIsNone(s.db.execute("SELECT valid_to FROM claims WHERE app_ref=?",(a2,)).fetchone()[0])
        finally:
            s.db.close(); td.cleanup()

    def test_reimport_is_semantically_replay_stable(self):
        td, s = make_store()
        try:
            before=s.snapshot_hash(); s.import_data(FAMILY); after=s.snapshot_hash()
            self.assertEqual(before,after)
            self.assertEqual(s.db.execute("SELECT content_hash FROM generations ORDER BY generation DESC LIMIT 1").fetchone()[0],after)
        finally:
            s.db.close(); td.cleanup()


    def test_inferred_role_types_support_followup_queries_without_materialization(self):
        td, s = make_store()
        try:
            rt=Runtime(s); rt.process("My mother in-law arrived today.")
            before=s.db.execute("SELECT count(*) FROM applications").fetchone()[0]
            self.assertEqual(rt.process("Is she a female?")["result"], "supported")
            self.assertEqual(rt.process("Is she a human?")["result"], "supported")
            self.assertEqual(rt.process("Is she a living entity?")["result"], "supported")
            self.assertEqual(before,s.db.execute("SELECT count(*) FROM applications").fetchone()[0])
        finally:
            s.db.close(); td.cleanup()

    def test_multilingual_interface_reuses_same_semantic_rules(self):
        td, s = make_store()
        try:
            rt = Runtime(s, "es")
            learned = rt.process("Mi suegra llegó hoy.")
            self.assertEqual(learned["status"], "learned")
            ans = rt.process("¿Estoy casado?")
            self.assertEqual(ans["result"], "supported")
            self.assertEqual(ans["response"], "Sí.")
            self.assertIn("rule:mil-decompose", rules_in_proof(ans["proof"]))
        finally:
            s.db.close(); td.cleanup()

    def test_reference_resolution_can_use_inferred_semantic_type(self):
        td, s = make_store()
        try:
            rt = Runtime(s); learned = rt.process("My mother in-law arrived today.")
            mil = learned["packet"]["apps"][0]["args"]["role:subject"]
            self.assertEqual(Delexer(s, "en").reference("she"), mil)
        finally:
            s.db.close(); td.cleanup()

    def test_semantically_duplicate_rule_does_not_bloat_rule_store(self):
        td, s = make_store()
        try:
            original = s.db.execute("SELECT count(*) FROM rules").fetchone()[0]
            row = s.db.execute("SELECT rule_kind,antecedent,consequent,confidence,authority_status FROM rules WHERE rule_ref='rule:type-transitive'").fetchone()
            import tempfile as _tf
            payload = {"rules":[{
                "rule_ref":"rule:duplicate-name", "rule_kind":row["rule_kind"],
                "if":json.loads(row["antecedent"]), "then":json.loads(row["consequent"]),
                "confidence":row["confidence"], "authority_status":row["authority_status"]
            }]}
            q=Path(td.name)/"duplicate.json"; q.write_text(json.dumps(payload),encoding="utf-8")
            s.import_data(q)
            self.assertEqual(original, s.db.execute("SELECT count(*) FROM rules").fetchone()[0])
        finally:
            s.db.close(); td.cleanup()

    def test_rule_admission_rejects_unbound_variables_and_language_can_create_only_declared_kinds(self):
        td, s = make_store()
        try:
            self.assertEqual(s.creatable_kinds(), {"entity", "event"})
            bad={"rule_ref":"bad","rule_kind":"entailment",
                 "if":[{"operator":"op:type","args":{"role:instance":"?x","role:class":"concept:human"}}],
                 "then":[{"operator":"op:type","args":{"role:instance":"?z","role:class":"concept:living_entity"}}]}
            with self.assertRaises(ValueError): s.validate_rule(bad)
        finally:
            s.db.close(); td.cleanup()

    def test_unknown_is_not_false(self):
        td, s = make_store()
        try:
            ans=Runtime(s).process("Am I married?")
            self.assertEqual(ans["result"],"unknown")
            self.assertIn("not have enough evidence",ans["response"].lower())
        finally:
            s.db.close(); td.cleanup()

    def test_unicode_casefold_resolution_is_multilingual_safe(self):
        td, s = make_store()
        try:
            self.assertEqual(s.resolve_label("CÓNYUGE", "es"), "rel:spouse")
        finally:
            s.db.close(); td.cleanup()

    def test_denial_does_not_supersede_unrelated_positive_current_state(self):
        td, s = make_store()
        try:
            with s.db:
                g=s.begin("deny-does-not-supersede")
                s.exact("atoms", ["ref","kind","metadata","generation"], ["value:single","value","{}",g], ["ref"], {"generation"})
                o1=s.add_observation("married",{},"und","test",g)
                married=s.insert_app("op:state", {"role:subject":"participant:user","role:dimension":"dim:marital_status","role:value":"value:married"},g,o1,"support")
                o2=s.add_observation("not single",{},"und","test",g)
                s.insert_app("op:state", {"role:subject":"participant:user","role:dimension":"dim:marital_status","role:value":"value:single"},g,o2,"deny")
                s.finish(g)
            self.assertIsNone(s.db.execute("SELECT valid_to FROM claims WHERE app_ref=? AND stance='support'",(married,)).fetchone()[0])
        finally:
            s.db.close(); td.cleanup()

    def test_repeated_user_observations_are_distinct_but_reuse_grounded_referents(self):
        td, s = make_store()
        try:
            rt=Runtime(s)
            first=rt.process("My mother in-law arrived today.")
            second=rt.process("My mother in-law arrived today.")
            self.assertEqual(first["status"],"learned")
            self.assertEqual(second["status"],"learned")
            self.assertEqual(first["new_atoms"],second["new_atoms"])
            self.assertEqual(s.db.execute("SELECT count(*) FROM observations WHERE surface=?",("My mother in-law arrived today.",)).fetchone()[0],2)
            self.assertEqual(s.db.execute("SELECT count(*) FROM applications WHERE operator_ref='op:event'").fetchone()[0],1)
        finally:
            s.db.close(); td.cleanup()

    def test_provisional_rules_do_not_execute_as_authority(self):
        td, s = make_store()
        try:
            with s.db:
                g=s.begin("provisional-rule")
                obs=s.add_observation("Ada human",{},"und","test",g)
                s.insert_app("op:type", {"role:instance":"entity:ada","role:class":"concept:human"},g,obs)
                rule={"rule_ref":"rule:provisional-human-doctor","rule_kind":"entailment","authority_status":"provisional","if":[{"operator":"op:type","args":{"role:instance":"?x","role:class":"concept:human"}}],"then":[{"operator":"op:type","args":{"role:instance":"?x","role:class":"concept:doctor"}}]}
                s.validate_rule(rule)
                s.exact("rules",["rule_ref","rule_kind","antecedent","consequent","confidence","authority_status","generation"],[rule["rule_ref"],rule["rule_kind"],canonical(rule["if"]),canonical(rule["then"]),1.0,"provisional",g],["rule_ref"],{"generation"})
                s.finish(g)
            facts,_=Inference(s).closure()
            self.assertFalse(any(f.operator=="op:type" and f.args.get("role:instance")=="entity:ada" and f.args.get("role:class")=="concept:doctor" for f in facts))
        finally:
            s.db.close(); td.cleanup()

    def test_unsupported_multivalued_roles_fail_explicitly(self):
        td, s = make_store()
        try:
            payload={"operator_roles":[{"operator_ref":"op:type","role_ref":"role:context","required":False,"cardinality":"many","filler_kind":"atom"}]}
            q=Path(td.name)/"many.json"; q.write_text(json.dumps(payload),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"one filler per role"):
                s.import_data(q)
        finally:
            s.db.close(); td.cleanup()

    def test_input_codec_requires_independent_model_agreement(self):
        td, s = make_store()
        try:
            packet,news,uses,trace=Runtime(s).i.parse("Am I married?")
            self.assertIsNotNone(packet)
            self.assertTrue(trace["program_roundtrip"])
            self.assertTrue(trace["independent_agreement"])
            self.assertTrue(trace["placeholder_conservation"])
        finally:
            s.db.close(); td.cleanup()

    def test_internal_semantic_ids_are_never_emitted(self):
        td, s = make_store()
        try:
            rt=Runtime(s); rt.process("My mother in-law arrived today.")
            ans=rt.process("Who is she?")
            self.assertNotRegex(ans.get("response",""), r"(?:atom|existential|app|fact):[0-9a-fA-F]+")
        finally:
            s.db.close(); td.cleanup()

    def test_inference_limit_is_frontier_not_false_unknown(self):
        td, s = make_store()
        try:
            rt=Runtime(s); rt.process("My mother in-law arrived today.")
            rt.inf.max_facts=1
            ans=rt.process("Am I married?")
            self.assertEqual(ans["status"],"frontier")
            self.assertEqual(ans["frontier"]["reason"],"inference_incomplete")
        finally:
            s.db.close(); td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
