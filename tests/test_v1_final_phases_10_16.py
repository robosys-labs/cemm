from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cemm.acquisition import acquire_reviewed
from cemm.capability import CapabilityEvaluator, RuntimeObservationProvider
from cemm.compiler import ExactStructuredCompiler
from cemm.context import ParticipantFrame, SessionContext
from cemm.curriculum import CurriculumManifest, SemanticEpisode
from cemm.evidence import EvidenceEnvelope, EvidenceLattice
from cemm.interpreter import Delexer
from cemm.model import Fact, canonical, lit
from cemm.goals import AdapterRegistry, GoalCandidate, OperationPlan, OperationResult
from cemm.response import pointerize_fact
from cemm.runtime import MODE_NORMAL, MODE_READ_ONLY, Runtime
from cemm.store import Store
from cemm.state import StateProjector
from cemm.transitions import TransitionEngine


def pack_hash(data):
    return hashlib.sha256(canonical({k: v for k, v in data.items() if k != "pack_hash"}).encode()).hexdigest()


def base_payload():
    atoms = []
    def atom(ref, kind, **metadata):
        atoms.append({"ref": ref, "kind": kind, "metadata": metadata})
    for ref in ("op:designation", "op:type", "op:relation", "op:state", "op:event"):
        atom(ref, "operator", foundational=True)
    roles = [
        "role:target", "role:label_type", "role:surface", "role:language", "role:script", "role:prior", "role:preferred", "role:context",
        "role:instance", "role:class", "role:subject", "role:relation", "role:object", "role:dimension", "role:value", "role:event", "role:type", "role:actor", "role:time",
    ]
    for ref in roles: atom(ref, "role", foundational=True)
    atom("participant:user", "participant", foundational=True)
    atom("participant:system", "participant", foundational=True)
    atom("concept:digital_agent", "concept", foundational=True)
    atom("concept:cat", "concept")
    atom("concept:animal", "concept")
    atom("concept:device", "concept")
    atom("entity:milo", "entity")
    atom("entity:device", "entity")
    atom("event:charge_instance", "event")
    atom("event:charge", "event_type", foundational=True)
    atom("event:greeting", "event_type", foundational=True)
    for ref in (
        "rel:subtype_of", "rel:facet_of", "rel:entitles_state_dimension", "rel:dimension_domain",
        "rel:entitles_capability", "rel:entitles_resource", "rel:mechanism_applies_to", "rel:depends_on", "rel:handled_by_adapter", "rel:requires_capability", "rel:value_of_dimension",
    ): atom(ref, "relation_type", foundational=True, operational=True, user_visible=False)
    for ref, domain in (
        ("domain:continuous", "continuous"), ("domain:categorical", "categorical"), ("domain:set_valued", "set_valued")
    ): atom(ref, "concept", foundational=True, domain_type=domain)
    for ref, typ in (
        ("dim:runtime_process_support", "float"),
        ("dim:semantic_runtime_support", "float"),
        ("dim:language_realizer_support", "float"),
        ("dim:critical_blocker_count", "int"),
        ("dim:battery_support", "float"),
    ):
        atom(ref, "state_dimension", foundational=True, cardinality="one", domain_type="continuous", literal_type=typ, min=0, max=1 if typ == "float" else 100, positive_direction="higher")
    atom("value:battery_full", "value")
    for ref, kind in (
        ("cap:interpret", "capability"), ("cap:realize", "capability"), ("cap:respond", "capability"),
        ("adapter:test", "adapter"),
        ("resource:runtime_process", "resource"), ("resource:semantic_runtime", "resource"),
        ("resource:language_realizer", "resource"), ("resource:output_channel", "resource"),
    ): atom(ref, kind, foundational=True)
    for ref in ("label:lexical",): atom(ref, "label_type", foundational=True)

    operator_roles = []
    def op_role(op, role, required, kind): operator_roles.append({"operator_ref": op, "role_ref": role, "required": required, "filler_kind": kind})
    for role, req, kind in (
        ("role:target",1,"atom"),("role:label_type",1,"label_type"),("role:surface",1,"literal:text"),("role:language",0,"literal:text"),("role:script",0,"literal:text"),("role:prior",0,"literal:float"),("role:preferred",0,"literal:bool"),("role:context",0,"atom")
    ): op_role("op:designation",role,req,kind)
    op_role("op:type","role:instance",1,"atom"); op_role("op:type","role:class",1,"concept")
    op_role("op:relation","role:subject",1,"atom"); op_role("op:relation","role:relation",1,"relation_type"); op_role("op:relation","role:object",1,"atom")
    op_role("op:state","role:subject",1,"atom"); op_role("op:state","role:dimension",1,"state_dimension"); op_role("op:state","role:value",1,"state_value")
    op_role("op:event","role:event",1,"event"); op_role("op:event","role:type",1,"event_type"); op_role("op:event","role:actor",0,"atom"); op_role("op:event","role:time",0,"time")

    control = {
        "operator.designation":"op:designation", "operator.state":"op:state",
        "role.subject":"role:subject", "role.dimension":"role:dimension", "role.value":"role:value",
        "designation.target":"role:target", "designation.type":"role:label_type", "designation.surface":"role:surface",
        "designation.language":"role:language", "designation.script":"role:script", "designation.prior":"role:prior",
        "designation.preferred":"role:preferred", "designation.context":"role:context",
        "new_kind.entity":"entity", "new_kind.event":"event", "self.ref":"participant:system",
        "profile.subtype_relation":"rel:subtype_of", "profile.facet_relation":"rel:facet_of",
        "profile.entitles_dimension_relation":"rel:entitles_state_dimension", "profile.dimension_domain_relation":"rel:dimension_domain",
        "profile.entitles_capability_relation":"rel:entitles_capability", "profile.entitles_resource_relation":"rel:entitles_resource",
        "profile.mechanism_applies_relation":"rel:mechanism_applies_to", "profile.depends_on_relation":"rel:depends_on",
        "policy.adapter_relation":"rel:handled_by_adapter", "policy.required_capability_relation":"rel:requires_capability",
        "profile.value_dimension_relation":"rel:value_of_dimension", "event.greeting":"event:greeting",
    }
    refs = [
        {"language":"en","surface":"I","features":{"participant_role":"speaker","person":"first"}},
        {"language":"en","surface":"you","features":{"participant_role":"addressee","person":"second"}},
    ]
    facts = []
    def fact(operator, args, **extra): facts.append({"operator":operator,"args":args,**extra})
    fact("op:type", {"role:instance":"participant:system","role:class":"concept:digital_agent"})
    fact("op:type", {"role:instance":"entity:milo","role:class":"concept:cat"})
    fact("op:type", {"role:instance":"entity:device","role:class":"concept:device"})
    for dim in ("dim:runtime_process_support","dim:semantic_runtime_support","dim:language_realizer_support","dim:critical_blocker_count"):
        fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_state_dimension","role:object":dim})
        fact("op:relation", {"role:subject":dim,"role:relation":"rel:dimension_domain","role:object":"domain:continuous"})
    fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_capability","role:object":"cap:respond"})
    for resource in ("resource:runtime_process","resource:semantic_runtime","resource:language_realizer","resource:output_channel"):
        fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_resource","role:object":resource})
        fact("op:relation", {"role:subject":"cap:respond","role:relation":"rel:depends_on","role:object":resource})
    fact("op:relation", {"role:subject":"concept:device","role:relation":"rel:entitles_state_dimension","role:object":"dim:battery_support"})
    fact("op:relation", {"role:subject":"event:charge","role:relation":"rel:handled_by_adapter","role:object":"adapter:test"})
    fact("op:relation", {"role:subject":"event:charge","role:relation":"rel:requires_capability","role:object":"cap:respond"})
    fact("op:relation", {"role:subject":"value:battery_full","role:relation":"rel:value_of_dimension","role:object":"dim:battery_support"})
    fact("op:relation", {"role:subject":"dim:battery_support","role:relation":"rel:dimension_domain","role:object":"domain:continuous"})
    designations = {
        "participant:system":"CEMM", "participant:user":"user", "concept:cat":"cat", "entity:milo":"Milo",
        "entity:device":"device", "cap:respond":"response capability", "event:charge":"charge",
        "dim:battery_support":"battery level",
    }
    for target, surface in designations.items():
        fact("op:designation", {
            "role:target":target,"role:label_type":"label:lexical","role:surface":lit(surface),
            "role:language":lit("en"),"role:script":lit("Latn"),"role:prior":lit(1.0,"float"),"role:preferred":lit(True,"bool")
        })
    rules = [{
        "rule_ref":"rule:charge_actor_battery", "rule_kind":"causal", "authority_status":"reviewed", "confidence":0.95,
        "if":[{"operator":"op:event","args":{"role:event":"?event","role:type":"event:charge","role:actor":"?actor"}}],
        "then":[{"operator":"op:state","args":{"role:subject":"?actor","role:dimension":"dim:battery_support","role:value":lit(1.0,"float")}}],
    }]
    return {"atoms":atoms,"operator_roles":operator_roles,"control_symbols":control,"reference_forms":refs,"facts":facts,"rules":rules}


def language_pack():
    data = {
        "version":6,"language":"en",
        "forces":["claim","query","description_request","directive","correction","retraction","acknowledgment"],
        "source_classes":["NONE","FRAME_SPEAKER","FRAME_ADDRESSEE","A0","A1",*[f"DIM_OF_A{i}" for i in range(8)],"Q0","Q1","NEW_ENTITY_0","NEW_EVENT_0"],
        "rule_sources":["NONE","A0","A1","V0","V1","E0"],
        "operators":["op:event","op:state","op:type"],
        "roles":["role:actor","role:class","role:dimension","role:event","role:instance","role:subject","role:type","role:value"],
        "function_forms":["is","how","are","hello"],
        "structured_examples":[
            {"example_ref":"s1","input":"@A0<participant> is @A1<concept>","target":{"force":"claim","intent":"assert","describe_source":"NONE","apps":[{"operator":"op:type","bindings":{"role:instance":"A0","role:class":"A1"}}],"projection":[]}},
            {"example_ref":"s2","input":"how is @A0<participant> ?","target":{"force":"query","intent":"query","describe_source":"NONE","apps":[{"operator":"op:state","bindings":{"role:subject":"A0","role:dimension":"Q0","role:value":"Q1"}}],"projection":["Q0","Q1"]}},
            {"example_ref":"s3","input":"hello","target":{"force":"claim","intent":"assert","describe_source":"NONE","apps":[{"operator":"op:event","bindings":{"role:event":"NEW_EVENT_0"}}],"projection":[]}},
        ],
        "rule_examples":[],
        "realization_examples":[
            {"example_ref":"r1","semantic":"FACT support op:type role:class @A0 role:instance @A1","surface_plan":"@A1 is a @A0."},
        ],
        "response_examples":[
            {"example_ref":"q-confirm","semantic":"RESPONSE confirm","surface_plan":"Yes."},
            {"example_ref":"q-deny","semantic":"RESPONSE deny","surface_plan":"No."},
            {"example_ref":"q-conflict","semantic":"RESPONSE report_conflict","surface_plan":"The evidence conflicts."},
            {"example_ref":"q-unknown","semantic":"RESPONSE report_target_uncertainty","surface_plan":"I do not have enough evidence."},
            {"example_ref":"clarify","semantic":"RESPONSE request_targeted_clarification EVIDENCE @E0","surface_plan":"What does @E0 mean here?"},
            {"example_ref":"capability","semantic":"RESPONSE report_capability TARGET @A0 SCORE @N0","surface_plan":"My @A0 is at @N0 percent."},
            {"example_ref":"ack","semantic":"RESPONSE acknowledge_claim","surface_plan":"I recorded that claim."},
            {"example_ref":"decline","semantic":"RESPONSE decline_directive","surface_plan":"I cannot perform that action."},
            {"example_ref":"greet","semantic":"RESPONSE greet","surface_plan":"Hello."},
        ],
        "grammar_tokens":["yes","no",".","the","evidence","conflicts","i","do","not","have","enough","what","does","mean","here","?","my","is","at","percent","recorded","that","claim","cannot","perform","action","hello","a"],
    }
    data["pack_hash"] = pack_hash(data)
    return data


class FakeInterpreter:
    def __init__(self, packet, trace=None):
        self.packet = packet
        self.trace = trace or {"interpretation_assessment":{"status":"resolved","grounded_refs":[]}}
    def observe(self, text, frame):
        envelope = EvidenceEnvelope.text(text, frame.speaker_ref, language="en", channel="text")
        return EvidenceLattice((envelope,), {"delexicalized":text,"grounded_anchors":{},"clauses":[text],"uses":[]}, ())
    def compose(self, lattice, frame, state_projections=None):
        return self.packet, [], [], dict(self.trace)


class FinalPhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.base = root / "base.json"; self.base.write_text(json.dumps(base_payload()), encoding="utf-8")
        self.pack = root / "en.json"; self.pack.write_text(json.dumps(language_pack()), encoding="utf-8")
        self.store = Store(root / "cemm.sqlite")
        self.store.import_data(self.base)
        self.runtime = Runtime(self.store, self.pack)

    def tearDown(self):
        self.store.db.close(); self.tmp.cleanup()

    def test_participant_requirements_resolve_from_cycle_frame(self):
        inbound = ParticipantFrame(
            self_ref="participant:system",
            speaker_ref="participant:user",
            addressee_ref="participant:system",
        )
        _, inbound_anchors, _ = Delexer(self.store, "en").run("I asked you.", inbound)
        self.assertIn("participant:user", inbound_anchors.values())
        self.assertIn("participant:system", inbound_anchors.values())
        outbound = ParticipantFrame(
            self_ref="participant:system",
            speaker_ref="participant:system",
            addressee_ref="participant:user",
        )
        _, outbound_anchors, _ = Delexer(self.store, "en").run("I asked you.", outbound)
        self.assertIn("participant:system", outbound_anchors.values())
        self.assertIn("participant:user", outbound_anchors.values())
        rows = self.store.db.execute(
            "SELECT bound_ref,features FROM reference_forms WHERE language='en' "
            "AND lower(surface) IN ('i','you')"
        ).fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(not row["bound_ref"] for row in rows))
        self.assertTrue(all(json.loads(row["features"]).get("participant_role") for row in rows))

    def test_state_projection_preserves_native_domain_statuses(self):
        fixture = Path(self.tmp.name) / "native_state_fixture.json"
        fixture.write_text(json.dumps({
            "atoms":[
                {"ref":"concept:test_device","kind":"concept"},
                {"ref":"entity:test_device","kind":"entity"},
                {"ref":"dim:test_load","kind":"state_dimension","metadata":{"cardinality":"one","domain_type":"continuous","literal_type":"float","min":0,"max":1}},
                {"ref":"dim:test_tags","kind":"state_dimension","metadata":{"cardinality":"many","domain_type":"set_valued"}},
                {"ref":"dim:test_mode","kind":"state_dimension","metadata":{"cardinality":"one","domain_type":"categorical"}},
                {"ref":"dim:test_signal","kind":"state_dimension","metadata":{"cardinality":"one","domain_type":"categorical"}},
                {"ref":"dim:test_last_seen","kind":"state_dimension","metadata":{"cardinality":"one","domain_type":"categorical","stale_after_seconds":1}},
                {"ref":"dim:test_missing","kind":"state_dimension","metadata":{"cardinality":"one","domain_type":"categorical"}},
                {"ref":"value:test_red","kind":"value"},
                {"ref":"value:test_blue","kind":"value"},
                {"ref":"value:test_on","kind":"value"},
                {"ref":"value:test_weak","kind":"value"},
                {"ref":"value:test_seen","kind":"value"},
            ],
            "facts":[
                {"operator":"op:type","args":{"role:instance":"entity:test_device","role:class":"concept:test_device"}},
                *[
                    {"operator":"op:relation","args":{"role:subject":"concept:test_device","role:relation":"rel:entitles_state_dimension","role:object":dimension}}
                    for dimension in ("dim:test_load","dim:test_tags","dim:test_mode","dim:test_signal","dim:test_last_seen","dim:test_missing")
                ],
                {"operator":"op:relation","args":{"role:subject":"dim:test_load","role:relation":"rel:dimension_domain","role:object":"domain:continuous"}},
                {"operator":"op:relation","args":{"role:subject":"dim:test_tags","role:relation":"rel:dimension_domain","role:object":"domain:set_valued"}},
                *[
                    {"operator":"op:relation","args":{"role:subject":dimension,"role:relation":"rel:dimension_domain","role:object":"domain:categorical"}}
                    for dimension in ("dim:test_mode","dim:test_signal","dim:test_last_seen","dim:test_missing")
                ],
            ],
        }), encoding="utf-8")
        self.store.import_data(fixture)

        def add(dimension, value, stance="support", confidence=1.0):
            with self.store.db:
                generation = self.store.begin(f"state:{dimension}", expected_world_revision=self.store.revisions()["world_revision"])
                observation = self.store.add_observation(
                    dimension, {"context_ref":"context:test"}, "und", "test", generation,
                    occurrence_ref=f"state:{dimension}:{generation}",
                )
                app_ref = self.store.insert_app(
                    "op:state",
                    {"role:subject":"entity:test_device","role:dimension":dimension,"role:value":value},
                    generation, observation, stance, confidence,
                )
                self.store.finish(generation, world_delta=True, observation_delta=True)
            return app_ref, observation

        first, _ = add("dim:test_load", lit(0.2, "float"))
        add("dim:test_load", lit(0.8, "float"))
        self.assertIsNotNone(self.store.db.execute(
            "SELECT valid_to FROM claims WHERE app_ref=? AND stance='support'", (first,)
        ).fetchone()[0])
        add("dim:test_tags", "value:test_red")
        add("dim:test_tags", "value:test_blue")
        add("dim:test_mode", "value:test_on", "support")
        add("dim:test_mode", "value:test_on", "deny")
        add("dim:test_signal", "value:test_weak", confidence=0.3)
        _, stale_observation = add("dim:test_last_seen", "value:test_seen")
        self.store.db.execute(
            "UPDATE observations SET observed_at='2000-01-01T00:00:00+00:00' WHERE observation_ref=?",
            (stale_observation,),
        )
        self.store.db.commit()
        projection = StateProjector(
            self.store, authority_generation=self.store.generation
        ).project("entity:test_device")
        dimensions = {item.dimension_ref:item for item in projection.dimensions}
        self.assertEqual(dimensions["dim:test_load"].status, "resolved")
        self.assertEqual(dimensions["dim:test_load"].values, (lit(0.8, "float"),))
        self.assertEqual(set(dimensions["dim:test_tags"].values), {"value:test_red","value:test_blue"})
        self.assertEqual(dimensions["dim:test_mode"].status, "conflicting")
        self.assertTrue(dimensions["dim:test_mode"].contradiction_lineage)
        self.assertEqual(dimensions["dim:test_signal"].status, "uncertain")
        self.assertEqual(dimensions["dim:test_last_seen"].status, "stale")
        self.assertEqual(dimensions["dim:test_missing"].status, "missing")

    def test_web_reopen_does_not_reimport_authority_generations(self):
        import cemm.web_demo as web

        old = (web._runtime, web._store, web._config, web._db_path, web._pack_path, list(web._data_files))
        db_path = str(Path(self.tmp.name) / "web-reopen.sqlite")
        try:
            web._runtime = None
            web._store = None
            web._config = None
            web._db_path = db_path
            web._pack_path = str(self.pack)
            web._data_files = [str(self.base)]
            first = web._ensure_runtime()
            generation = first.s.generation
            first.s.db.close()
            web._runtime = None
            web._store = None
            second = web._ensure_runtime()
            self.assertEqual(second.s.generation, generation)
            self.assertEqual(
                second.s.db.execute("SELECT count(*) FROM generations").fetchone()[0],
                generation,
            )
            second.s.db.close()
            one = web.ChatResponse(status="ok", response="one")
            two = web.ChatResponse(status="ok", response="two")
            one.capability_assessments.append({"x": 1})
            self.assertEqual(two.capability_assessments, [])
        finally:
            web._runtime, web._store, web._config, web._db_path, web._pack_path, web._data_files = old

    def test_bounded_fact_hydration_uses_batch_queries_not_n_plus_one(self):
        refs = [
            str(row[0])
            for row in self.store.db.execute(
                "SELECT app_ref FROM applications ORDER BY app_ref LIMIT 24"
            ).fetchall()
        ]
        statements = []
        self.store.db.set_trace_callback(
            lambda sql: statements.append(sql) if sql.lstrip().upper().startswith("SELECT") else None
        )
        try:
            facts = self.store._facts_from_app_refs(refs)
        finally:
            self.store.db.set_trace_callback(None)
        self.assertTrue(facts)
        self.assertLessEqual(len(statements), 3, statements)

    def test_indexed_pattern_retrieval_matches_without_salience_fallback(self):
        facts = self.store.matching_facts((
            {"operator":"op:type","args":{"role:instance":"entity:milo","role:class":"?q0"},"stance":"support"},
        ), limit=8)
        self.assertEqual([(f.operator, f.args["role:class"]) for f in facts], [("op:type", "concept:cat")])

    def test_read_only_query_uses_sparse_retrieval_and_all_stages(self):
        packet = {
            "force":"query","apps":[],"directive":None,"describe":None,"qualifiers":{},"modality":"actual",
            "query":{"query_ref":"query:test","restrictions":[{"operator":"op:type","args":{"role:instance":"entity:milo","role:class":"?q0"},"stance":"support"}],"variables":[{"ref":"?q0","filler_kind":"concept","role_ref":"role:class"}],"projection":["?q0"],"qualifiers":{}},
        }
        self.runtime.i = FakeInterpreter(packet)
        self.store.base_facts = lambda: (_ for _ in ()).throw(AssertionError("full scan forbidden"))
        before = self.store.revisions().copy()
        result = self.runtime.process("what is Milo", mode=MODE_READ_ONLY)
        self.assertEqual(result["query_result"]["status"], "answered")
        self.assertEqual(result["query_result"]["bindings"][0]["values"]["?q0"], "concept:cat")
        self.assertEqual(before, self.store.revisions())
        stages = [row["stage"] for row in result["stage_trace"]["records"]]
        self.assertEqual(stages, list(range(23)))
        self.assertTrue(result["side_effect_free"])
        self.assertFalse(result["retrieval"]["trace"]["whole_store_scan"])

    def test_stage13_commit_is_incremental_and_cas_guarded(self):
        packet = {"force":"claim","apps":[{"operator":"op:type","args":{"role:instance":"entity:device","role:class":"concept:device"},"stance":"support"}],"query":None,"directive":None,"describe":None,"qualifiers":{},"modality":"actual"}
        self.runtime.i = FakeInterpreter(packet)
        self.store.snapshot_hash = lambda: (_ for _ in ()).throw(AssertionError("snapshot hashing forbidden on normal commit"))
        before = self.store.revisions()["world_revision"]
        result = self.runtime.process("device is device", mode=MODE_NORMAL)
        self.assertIn(result["status"], {"learned","recorded"})
        self.assertIsNotNone(result["commit"]["receipt"])
        self.assertEqual(self.store.revisions()["world_revision"], before + 1)
        self.assertEqual(result["commit"]["receipt"]["stage"], 13)

    def test_role_addressed_transition_and_query_no_delta(self):
        event_app = {"operator":"op:event","args":{"role:event":"event:charge_instance","role:type":"event:charge","role:actor":"entity:device"},"stance":"support"}
        projection = {"entity:device": self.runtime.state_projector.project("entity:device").as_dict()}
        retrieval = self.runtime.retriever.retrieve((event_app,), salient_refs=("entity:device",), include_causal=True)
        previews = self.runtime.transition_engine.preview((event_app,), retrieval.facts, projection)
        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0].deltas[0].subject_ref, "entity:device")
        self.assertEqual(previews[0].deltas[0].dimension_ref, "dim:battery_support")
        query_packet = {"force":"query","apps":[],"query":{"query_ref":"q","restrictions":[{"operator":"op:state","args":{"role:subject":"entity:device","role:dimension":"dim:battery_support","role:value":"?q0"}}],"variables":[{"ref":"?q0","filler_kind":"state_value"}],"projection":["?q0"],"qualifiers":{}},"directive":None,"describe":None,"qualifiers":{},"modality":"actual"}
        self.runtime.i = FakeInterpreter(query_packet)
        result = self.runtime.process("battery?", mode=MODE_READ_ONLY)
        self.assertEqual(result["transition_previews"], [])

    def test_concept_licenses_instance_state_but_does_not_receive_instance_state(self):
        concept_projection = self.runtime.state_projector.project("concept:device")
        instance_projection = self.runtime.state_projector.project("entity:device")
        self.assertEqual(concept_projection.type_facet_closure, ("concept:device",))
        self.assertEqual(concept_projection.dimensions, ())
        self.assertIn(
            "dim:battery_support",
            {item.dimension_ref for item in instance_projection.dimensions},
        )

    def test_self_capability_is_nonlexical_and_queryable(self):
        self.assertIsNone(self.store.atom("value:ready"))
        packet = {"force":"query","apps":[],"query":{"query_ref":"q:self","restrictions":[{"operator":"op:state","args":{"role:subject":"participant:system","role:dimension":"?q0","role:value":"?q1"}}],"variables":[{"ref":"?q0","filler_kind":"state_dimension"},{"ref":"?q1","filler_kind":"state_value"}],"projection":["?q0","?q1"],"qualifiers":{}},"directive":None,"describe":None,"qualifiers":{},"modality":"actual"}
        self.runtime.i = FakeInterpreter(packet, {"interpretation_assessment":{"status":"resolved","grounded_refs":["participant:system"]}})
        result = self.runtime.process("how are you", mode=MODE_READ_ONLY)
        assessment = next(item for item in result["capability_assessments"] if item["capability_ref"] == "cap:respond")
        self.assertEqual(assessment["score"], 1.0)
        self.assertEqual(result["response_csir"]["action"], "report_capability")
        self.assertEqual(result["response_csir"]["target_ref"], "cap:respond")
        self.assertIn("100 percent", result["response"].lower())

    def test_compiler_rejects_bare_query_application(self):
        compiler = ExactStructuredCompiler(self.store)
        with self.assertRaisesRegex(ValueError, "QueryStructure"):
            compiler.compile({"force":"query","apps":[],"query":{"operator":"op:type","args":{"role:instance":"entity:milo","role:class":"?q0"}},"directive":None,"describe":None})

    def test_curriculum_requires_no_transition_and_family_holdout(self):
        episode = SemanticEpisode.from_dict({
            "family":"query_state","pre":{},"input_evidence":[{"text":"How is it?"}],
            "target":{"stable_csir":{},"discourse_act":{"force":"query"},"epistemic_placement":{},"transition":"NO_TRANSITION","response_csir":{}},
        })
        manifest = CurriculumManifest(("query_state",),("directive_event",),(episode,),("transition_no_transition",))
        self.assertTrue(manifest.validate())
        leaking = CurriculumManifest(("query_state",),("query_state",),(episode,),())
        with self.assertRaisesRegex(ValueError, "leakage"):
            leaking.validate()


    def test_repeated_unknown_frontier_accumulates_instead_of_bloating_rows(self):
        trace = {
            "reason": "unknown_form",
            "unknown_form_evidence": [
                {"surface":"flarble","normalized":"flarble","semantic_kind_candidates":["concept","value"]}
            ],
            "interpretation_assessment": {
                "status":"unresolved",
                "unresolved_evidence":[{"surface":"flarble"}],
                "blockers":["unknown_form"],
            },
        }
        self.runtime.i = FakeInterpreter(None, trace)
        first = self.runtime.process("flarble", mode=MODE_NORMAL)
        second = self.runtime.process("flarble", mode=MODE_NORMAL)
        rows = self.store.db.execute(
            "SELECT frontier_ref,evidence_count,generation,last_generation FROM frontiers WHERE reason='unknown_form'"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["evidence_count"]), 2)
        self.assertLess(int(rows[0]["generation"]), int(rows[0]["last_generation"]))
        self.assertEqual(first["commit"]["frontier_refs"][0], second["commit"]["frontier_refs"][0])

    def test_unknown_frontier_is_targeted_and_does_not_mutate_self(self):
        self.runtime.i = FakeInterpreter(
            None,
            {
                "reason": "unknown_form",
                "unknown_form_evidence": [
                    {"surface": "flarble", "normalized": "flarble", "semantic_kind_candidates": ["concept", "value"]}
                ],
                "interpretation_assessment": {
                    "status": "unresolved",
                    "unresolved_evidence": [{"surface": "flarble"}],
                    "blockers": ["unknown_form"],
                },
            },
        )
        before = self.store.revisions().copy()
        result = self.runtime.process("flarble", mode=MODE_READ_ONLY)
        self.assertEqual(result["status"], "frontier")
        self.assertEqual(result["response_csir"]["action"], "request_targeted_clarification")
        self.assertIn("flarble", result["response"].lower())
        self.assertEqual(result["self_state"], {})
        self.assertEqual(before, self.store.revisions())

    def test_pre_final_populated_database_is_rejected(self):
        path = Path(self.tmp.name) / "legacy.sqlite"
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE atoms(ref TEXT PRIMARY KEY)")
        db.execute("INSERT INTO atoms VALUES('legacy')")
        db.commit(); db.close()
        with self.assertRaisesRegex(RuntimeError, "pre-v1-final"):
            Store(path)

    def test_world_and_common_ground_cas(self):
        original = self.store.revisions()
        with self.store.db:
            generation = self.store.begin("cas", expected_world_revision=original["world_revision"])
            self.store.finish(
                generation,
                cycle_ref="cycle:cas",
                stage=13,
                expected_world_revision=original["world_revision"],
                world_delta=True,
                payload={"test": True},
            )
        with self.assertRaisesRegex(RuntimeError, "world revision CAS failed"):
            self.store.begin("stale", expected_world_revision=original["world_revision"])
        discourse = self.store.revisions()["discourse_revision"]
        with self.store.db:
            self.store.commit_common_ground("conversation:test", "act:one", {"action":"confirm"}, expected_discourse_revision=discourse)
        with self.assertRaisesRegex(RuntimeError, "discourse revision CAS failed"):
            self.store.commit_common_ground("conversation:test", "act:two", {"action":"deny"}, expected_discourse_revision=discourse)

    def test_blocked_goal_cannot_be_authorized_even_with_adapter_and_permission(self):
        registry = AdapterRegistry()
        registry.register("adapter:test", lambda request: {"ok": True})
        goal = GoalCandidate(
            "goal:blocked",
            "handle_directive",
            "act:blocked",
            1.0,
            {},
            ("capability_unavailable:cap:required",),
        )
        plan = registry.plan(
            goal,
            permission_scope="operations:test",
            candidate_adapter_refs=("adapter:test",),
        )
        self.assertFalse(plan.authorized)
        self.assertTrue(plan.reason.startswith("goal_blocked:"))
        self.assertEqual(registry.execute(plan).status, "declined")

    def test_effect_journal_is_idempotent(self):
        plan = OperationPlan("plan:test", "goal:test", "adapter:test", {"x": 1}, True, "authorized", "idem:test")
        result = OperationResult("result:test", "plan:test", "succeeded", {"ok": True}, "2026-01-01T00:00:00+00:00")
        with self.store.db:
            first = self.store.journal_effect(plan, result)
        revision = self.store.revisions()["effect_revision"]
        with self.store.db:
            second = self.store.journal_effect(plan, result)
        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(revision, self.store.revisions()["effect_revision"])
        self.assertEqual(first["effect_ref"], second["effect_ref"])

    def test_directive_declines_without_registered_adapter(self):
        packet = {
            "force":"directive", "apps":[], "query":None, "describe":None, "qualifiers":{}, "modality":"actual",
            "directive":{"content":[{"operator":"op:event","args":{"role:event":"event:charge_instance","role:type":"event:charge","role:actor":"entity:device"},"stance":"support"}]},
        }
        self.runtime.i = FakeInterpreter(packet)
        result = self.runtime.process("charge the device", mode=MODE_NORMAL)
        self.assertEqual(result["status"], "declined")
        self.assertEqual(result["operation_plan"]["reason"], "authorized_adapter_not_registered")
        self.assertEqual(result["response_csir"]["action"], "decline_directive")
        self.assertNotEqual(result["operation_result"]["status"], "succeeded")

    def test_read_only_directive_never_calls_external_adapter(self):
        calls = []
        registry = AdapterRegistry()
        registry.register("adapter:test", lambda request: calls.append(request) or {"ok": True})
        session = SessionContext(
            "session:readonly", "conversation:readonly", "participant:system",
            "participant:user", "participant:system", permission_scope="operations:test",
        )
        runtime = Runtime(self.store, self.pack, session_context=session, adapter_registry=registry)
        packet = {
            "force":"directive", "apps":[], "query":None, "describe":None, "qualifiers":{}, "modality":"actual",
            "directive":{"content":[{"operator":"op:event","args":{"role:event":"event:charge_instance","role:type":"event:charge","role:actor":"entity:device"},"stance":"support"}]},
        }
        runtime.i = FakeInterpreter(packet)
        before = self.store.revisions().copy()
        result = runtime.process("charge the device", mode=MODE_READ_ONLY)
        self.assertEqual(calls, [])
        self.assertEqual(result["operation_result"]["status"], "not_executed")
        self.assertIsNone(result["effect_receipt"])
        self.assertEqual(before, self.store.revisions())
        stage16 = next(row for row in result["stage_trace"]["records"] if row["stage"] == 16)
        self.assertFalse(stage16["durable_write"])
        self.assertEqual(stage16["artifact_counts"]["executed"], 0)

    def test_directive_executes_only_semantically_authorized_registered_adapter(self):
        registry = AdapterRegistry()
        registry.register(
            "adapter:test",
            lambda request: {
                "semantic_observations": [
                    {"operator":"op:state","args":{"role:subject":"entity:device","role:dimension":"dim:battery_support","role:value":lit(1.0,"float")},"stance":"support"}
                ]
            },
        )
        session = SessionContext(
            "session:test", "conversation:test", "participant:system",
            "participant:user", "participant:system", permission_scope="operations:test",
        )
        runtime = Runtime(self.store, self.pack, session_context=session, adapter_registry=registry)
        packet = {
            "force":"directive", "apps":[], "query":None, "describe":None, "qualifiers":{}, "modality":"actual",
            "directive":{"content":[{"operator":"op:event","args":{"role:event":"event:charge_instance","role:type":"event:charge","role:actor":"entity:device"},"stance":"support"}]},
        }
        runtime.i = FakeInterpreter(packet)
        result = runtime.process("charge the device", mode=MODE_NORMAL)
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["operation_plan"]["adapter_ref"], "adapter:test")
        self.assertEqual(result["operation_plan"]["request"]["required_capability_refs"], ["cap:respond"])
        self.assertEqual(result["operation_plan"]["request"]["capability_score"], 1.0)
        self.assertEqual(result["operation_result"]["status"], "succeeded")
        self.assertEqual(result["response_csir"]["action"], "report_operation_result")
        self.assertTrue(result["effect_receipt"])
        self.assertTrue(result["operation_observation_receipt"])
        stage16 = next(row for row in result["stage_trace"]["records"] if row["stage"] == 16)
        stage17 = next(row for row in result["stage_trace"]["records"] if row["stage"] == 17)
        self.assertTrue(stage16["durable_write"])
        self.assertTrue(stage17["durable_write"])

    def test_retraction_is_source_owned(self):
        frame = ParticipantFrame("participant:system", "participant:user", "participant:system")
        packet = {"force":"claim","apps":[{"operator":"op:type","args":{"role:instance":"entity:milo","role:class":"concept:cat"},"stance":"support"}],"query":None,"directive":None,"describe":None,"qualifiers":{},"modality":"actual"}
        from cemm.cognition import build_discourse_act
        act = build_discourse_act(packet, frame, {})
        world = self.store.revisions()["world_revision"]
        with self.store.db:
            generation = self.store.begin("ownership", expected_world_revision=world)
            observation = self.store.add_observation("Milo is a cat", packet, "en", "participant:user", generation)
            occurrence = self.store.add_claim_occurrence(observation, act, generation)
            self.store.insert_app("op:type", packet["apps"][0]["args"], generation, observation)
            self.store.finish(generation, cycle_ref="cycle:ownership", stage=13, expected_world_revision=world, world_delta=True, observation_delta=True)
        with self.assertRaises(PermissionError):
            self.store.retract_claim_occurrence(occurrence, "participant:system")
        with self.store.db:
            closed = self.store.retract_claim_occurrence(occurrence, "participant:user")
        self.assertTrue(closed)

    def test_pointerization_is_order_invariant(self):
        one = Fact("f:1", "op:type", {"role:class":"concept:cat", "role:instance":"entity:milo"})
        two = Fact("f:2", "op:type", {"role:instance":"entity:milo", "role:class":"concept:cat"})
        self.assertEqual(pointerize_fact(one), pointerize_fact(two))

    def test_workspace_bounds_required_and_selected_slots(self):
        facts = [Fact(f"fact:{i}", "op:type", {"role:instance":"entity:milo", "role:class":"concept:cat"}) for i in range(100)]
        required = tuple(facts[:80])
        _, trace = self.runtime.workspace.build(facts, required_facts=required, proof_refs=[item.ref for item in required], cycle_turn=1)
        self.assertLessEqual(len(trace["selected"]), self.runtime.config.workspace_max_required + self.runtime.config.workspace_top_k)
        self.assertLessEqual(sum(1 for item in trace["selected"] if item["hard_required"]), self.runtime.config.workspace_max_required)

    def test_stage_trace_rejects_illegal_durable_write(self):
        from cemm.stages import Stage, StageTrace
        trace = StageTrace("cycle:test")
        with self.assertRaisesRegex(ValueError, "does not own durable effects"):
            trace.add(Stage.QUERY_EXPLAIN, durable_write=True)
        fresh = StageTrace("cycle:finalize")
        with self.assertRaisesRegex(ValueError, "does not own durable effects"):
            fresh.add(Stage.FINALIZE, durable_write=True)

    def test_reviewed_acquisition_requires_explicit_kind_and_indexes_incrementally(self):
        with self.assertRaisesRegex(ValueError, "explicit semantic kind"):
            acquire_reviewed(
                self.store,
                self.runtime,
                {"document_ref":"doc:missing-kind","mentions":[{"surface":"Glorp"}]},
            )
        self.store.rebuild_designations = lambda: (_ for _ in ()).throw(
            AssertionError("reviewed acquisition must not rebuild the full designation index")
        )
        before = self.store.revisions()["world_revision"]
        result = acquire_reviewed(
            self.store,
            self.runtime,
            {
                "document_ref":"doc:glorp",
                "language":"en",
                "mentions":[{"surface":"Glorp","kind":"concept"}],
            },
        )
        ref = result["created_or_resolved"]["Glorp"]
        self.assertEqual(self.store.atom(ref)["kind"], "concept")
        self.assertEqual(self.store.resolve_label("Glorp", "en", "concept"), ref)
        self.assertEqual(self.store.revisions()["world_revision"], before + 1)
        self.assertEqual(result["commit_receipt"]["stage"], 13)
        self.assertIsNone(result["result"])

    def test_acquisition_module_has_no_autonomous_or_concept_default_path(self):
        source = (Path(__file__).resolve().parents[1] / "cemm/acquisition.py").read_text(encoding="utf-8")
        self.assertNotIn("class AutonomousAcquirer", source)
        self.assertNotIn('defaulting to ``"concept"``', source)
        self.assertNotIn('get("kind", "concept")', source)
        self.assertNotIn('runtime.process(doc["text"],learn=', source)

    def test_compiler_requires_explicit_discourse_force(self):
        compiler = ExactStructuredCompiler(self.store)
        with self.assertRaisesRegex(ValueError, "explicit discourse force"):
            compiler.compile({"apps":[],"query":None,"directive":None,"describe":None})

    def test_final_authority_migration_is_deterministic_and_removes_sidecars(self):
        import importlib.util
        repo = Path(self.tmp.name) / "migration_repo"
        (repo / "cemm/data").mkdir(parents=True)
        (repo / "cemm/language_packs").mkdir(parents=True)
        base = base_payload()
        # Seed the obsolete self/outcome artifacts that the migration must quarantine.
        base["atoms"].extend([
            {"ref":"dim:response_state","kind":"state_dimension","metadata":{"foundational":True}},
            {"ref":"value:ready","kind":"value","metadata":{"foundational":True}},
            {"ref":"rel:response_goal","kind":"relation_type","metadata":{"foundational":True}},
            {"ref":"goal:confirm","kind":"goal","metadata":{"foundational":True}},
            {"ref":"rel:old_state_value","kind":"relation_type","metadata":{"foundational":True}},
            {"ref":"rel:old_state_dimension","kind":"relation_type","metadata":{"foundational":True}},
            {"ref":"spec:battery_full","kind":"state_spec","metadata":{"foundational":True}},
        ])
        base["control_symbols"].update({
            "self.response_state_dimension":"dim:response_state",
            "self.ready":"value:ready",
            "policy.response_goal_relation":"rel:response_goal",
            "policy.state_value_relation":"rel:old_state_value",
            "policy.state_dimension_relation":"rel:old_state_dimension",
        })
        base["facts"].extend([
            {"operator":"op:relation","args":{"role:subject":"value:supported","role:relation":"rel:response_goal","role:object":"goal:confirm"}},
            {"operator":"op:relation","args":{"role:subject":"spec:battery_full","role:relation":"rel:old_state_value","role:object":"value:battery_full"}},
            {"operator":"op:relation","args":{"role:subject":"spec:battery_full","role:relation":"rel:old_state_dimension","role:object":"dim:battery_support"}},
        ])
        (repo / "cemm/data/base.json").write_text(json.dumps(base), encoding="utf-8")
        en = language_pack()
        en["structured_examples"].extend([
            {
                "example_ref":"legacy:state",
                "input":"@A0<entity> is @A1<value>.",
                "target":{"force":"claim","intent":"assert","describe_source":"NONE","apps":[{"operator":"op:state","bindings":{"role:subject":"A0","role:value":"A1"}}],"projection":[]},
            },
            {
                "example_ref":"legacy:generic-concept",
                "input":"@A0<concept> is an @A1<concept>.",
                "target":{"force":"claim","intent":"assert","describe_source":"NONE","apps":[{"operator":"op:type","bindings":{"role:instance":"A0","role:class":"A1"}}],"projection":[]},
            },
        ])
        en.pop("pack_hash", None); en["pack_hash"] = pack_hash(en)
        (repo / "cemm/language_packs/en.json").write_text(json.dumps(en), encoding="utf-8")
        es = language_pack(); es["language"] = "es"; es["function_forms"] = ["es", "cómo"]
        es.pop("pack_hash", None); es["pack_hash"] = pack_hash(es)
        (repo / "cemm/language_packs/es.json").write_text(json.dumps(es), encoding="utf-8")
        (repo / "cemm/language_packs/en.v1.json").write_text("{}", encoding="utf-8")
        tool_path = Path(__file__).resolve().parents[1] / "tools/migrate_v1_final_authority.py"
        spec = importlib.util.spec_from_file_location("migrate_final", tool_path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        first = module.main(repo)
        migrated_base = json.loads((repo / "cemm/data/base.json").read_text(encoding="utf-8"))
        refs = {item["ref"] for item in migrated_base["atoms"]}
        self.assertNotIn("dim:response_state", refs)
        self.assertNotIn("value:ready", refs)
        self.assertIn("concept:digital_agent", refs)
        self.assertIn("rel:handled_by_adapter", refs)
        self.assertIn("rel:requires_capability", refs)
        self.assertEqual(migrated_base["control_symbols"]["policy.adapter_relation"], "rel:handled_by_adapter")
        self.assertEqual(migrated_base["control_symbols"]["policy.required_capability_relation"], "rel:requires_capability")
        value_links = [
            item for item in migrated_base["facts"]
            if item.get("operator") == "op:relation"
            and item.get("args", {}).get("role:relation") == "rel:value_of_dimension"
        ]
        self.assertTrue(any(
            item.get("args") == {"role:subject":"value:battery_full","role:relation":"rel:value_of_dimension","role:object":"dim:battery_support"}
            for item in value_links
        ))
        self.assertFalse((repo / "cemm/language_packs/en.v1.json").exists())
        migrated_en = json.loads((repo / "cemm/language_packs/en.json").read_text(encoding="utf-8"))
        legacy = next(item for item in migrated_en["structured_examples"] if item["example_ref"] == "legacy:state")
        self.assertEqual(legacy["target"]["apps"][0]["bindings"]["role:dimension"], "DIM_OF_A1")
        generic = next(item for item in migrated_en["structured_examples"] if item["example_ref"] == "legacy:generic-concept")
        generic_app = generic["target"]["apps"][0]
        self.assertEqual(generic_app["operator"], "op:relation")
        self.assertEqual(generic_app["bindings"]["role:subject"], "A0")
        self.assertEqual(generic_app["bindings"]["role:object"], "A1")
        constant_source = generic_app["bindings"]["role:relation"]
        self.assertEqual(migrated_en["constant_sources"][constant_source], "rel:subtype_of")
        en_report = next(item for item in first["packs"] if item["language"] == "en")
        self.assertGreater(en_report["patched_state_dimensions"], 0)
        self.assertGreater(en_report["patched_generic_subtypes"], 0)
        migrated_es = json.loads((repo / "cemm/language_packs/es.json").read_text(encoding="utf-8"))
        self.assertIn("estoy", migrated_es["function_forms"])
        self.assertNotIn("USER", migrated_es["source_classes"])
        self.assertNotIn("SYSTEM", migrated_es["source_classes"])
        self.assertEqual(migrated_es["pack_hash"], pack_hash(migrated_es))
        snapshot = (repo / "cemm/data/base.json").read_text(encoding="utf-8")
        second = module.main(repo)
        self.assertEqual(snapshot, (repo / "cemm/data/base.json").read_text(encoding="utf-8"))
        self.assertEqual(first["base"]["self_ref"], second["base"]["self_ref"])

    def test_final_runtime_source_has_no_removed_compatibility_paths(self):
        root = Path(__file__).resolve().parents[1] / "cemm"
        forbidden = {
            "SessionSelf": "global semantic self compatibility facade",
            ".v1.json": "language sidecar merge",
            "infer_state_dimension": "value-to-dimension semantic shim",
            "LEGACY_FORCE": "implicit discourse-force shim",
            "text.rstrip().endswith": "punctuation force override",
        }
        checked = (
            "runtime.py", "compiler.py", "codec.py", "interpreter.py", "inference.py",
            "retrieval.py", "workspace.py", "realizer.py", "trainer.py", "response.py",
        )
        for filename in checked:
            text = (root / filename).read_text(encoding="utf-8")
            for needle, description in forbidden.items():
                self.assertNotIn(needle, text, f"{filename} retained {description}")
        runtime_text = (root / "runtime.py").read_text(encoding="utf-8")
        self.assertNotIn("base_facts(", runtime_text)
        self.assertNotIn("snapshot_hash(", runtime_text)
        self.assertFalse((root / "selfstate.py").exists(), "final payload must delete selfstate.py")



    def test_reviewed_constant_source_is_pinned_to_authority_generation(self):
        codec = self.runtime.i.codec
        codec.constant_sources["CONST0"] = "rel:subtype_of"
        self.assertEqual(
            codec._source_value(
                "CONST0", {}, self.runtime.session.input_frame(), self.store,
                self.runtime.runtime_attestation["authority_generation"],
            ),
            "rel:subtype_of",
        )
        with self.store.db:
            generation = self.store.begin("future-authority")
            self.store.exact(
                "atoms", ["ref", "kind", "metadata", "generation", "authority_scope"],
                ["rel:future", "relation_type", "{}", generation, "authority"],
                ["ref"], {"generation"},
            )
            self.store.finish(generation, world_delta=False)
        codec.constant_sources["CONST1"] = "rel:future"
        self.assertIsNone(
            codec._source_value(
                "CONST1", {}, self.runtime.session.input_frame(), self.store,
                self.runtime.runtime_attestation["authority_generation"],
            )
        )

    def test_trainer_compiles_generic_predication_with_reviewed_constant_source(self):
        from cemm.trainer import compile_corpus
        root = Path(self.tmp.name) / "trainer_constants"
        root.mkdir()
        knowledge = root / "knowledge.json"
        knowledge.write_text(json.dumps(base_payload()), encoding="utf-8")
        corpus = root / "corpus.json"
        corpus.write_text(json.dumps({
            "language":"en",
            "constant_refs":["rel:subtype_of"],
            "function_forms":["is", "an"],
            "interpretation_examples":[{
                "example_ref":"generic:subtype",
                "surface":"Cat is an animal.",
                "mentions":[
                    {"surface":"Cat", "ref":"concept:cat", "kind":"concept"},
                    {"surface":"animal", "ref":"concept:animal", "kind":"concept"},
                ],
                "semantic":{
                    "force":"claim",
                    "apps":[{
                        "operator":"op:relation",
                        "args":{
                            "role:subject":"concept:cat",
                            "role:relation":"rel:subtype_of",
                            "role:object":"concept:animal",
                        },
                    }],
                },
            }],
        }), encoding="utf-8")
        compiled = compile_corpus(corpus, [knowledge])
        self.assertEqual(compiled["constant_sources"], {"CONST0":"rel:subtype_of"})
        app = compiled["structured_examples"][0]["target"]["apps"][0]
        self.assertEqual(app["operator"], "op:relation")
        self.assertEqual(app["bindings"], {
            "role:subject":"A0", "role:relation":"CONST0", "role:object":"A1",
        })

    def test_explicit_value_dimension_source_resolves_through_authority(self):
        value = self.runtime.i.codec._source_value(
            "DIM_OF_A0",
            {"@A0":"value:battery_full"},
            self.runtime.session.input_frame(),
            self.store,
            self.runtime.runtime_attestation["authority_generation"],
        )
        self.assertEqual(value, "dim:battery_support")
        self.assertEqual(self.store.dimensions_for_value("value:battery_full"), ("dim:battery_support",))



if __name__ == "__main__":
    unittest.main(verbosity=2)
