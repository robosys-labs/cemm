"""Exact structured compiler with bounded candidate-local application graphs.

Flat packets and recursive packets share one compiler.  Application-valued
fillers are accepted only when the exact operator role expects ``app`` or a
reviewed semantic frame explicitly licenses proposition content on that role.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from cemm.cognition import QueryStructure, SemanticVariable
from cemm.model import canonical, isvar
from cemm.semantic_contributions import SemanticAffordanceIndex
from cemm.store import Store


class ExactStructuredCompiler:
    def __init__(self, s: Store):
        self.s = s
        self.affordances = SemanticAffordanceIndex(
            s, getattr(s, "generation", None), max_profiles_per_target=8
        )

    @staticmethod
    def _predicate_ref(operator: str, args: Mapping[str, Any]) -> str | None:
        role = {
            "op:event": "role:type",
            "op:relation": "role:relation",
            "op:state": "role:dimension",
            "op:type": "role:class",
        }.get(operator)
        value = args.get(role) if role else None
        return value if isinstance(value, str) and not value.startswith(("?", "!")) else None

    def _persisted_app_exists(self, app_ref: str) -> bool:
        db = getattr(self.s, "db", None)
        if db is None:
            return False
        try:
            return bool(db.execute(
                "SELECT 1 FROM applications WHERE app_ref=?", (str(app_ref),)
            ).fetchone())
        except Exception:
            return False

    def _frame_allows_app(self, operator: str, role_ref: str, args: Mapping[str, Any]) -> bool:
        predicate = self._predicate_ref(operator, args)
        if not predicate:
            return False
        return any(
            profile.metadata.get("kernel_operator_ref") == operator
            and bool(profile.metadata.get("proposition_taking"))
            and any(
                role.role_ref == role_ref and "app" in set(role.filler_kinds)
                for role in profile.roles
            )
            for profile in self.affordances.profiles_for(predicate)
        )

    def _kind_ok(
        self,
        spec: Mapping[str, Any],
        value: Any,
        *,
        operator: str,
        role_ref: str,
        args: Mapping[str, Any],
        local_app_refs: set[str],
        allow_variable: bool,
    ) -> bool:
        spec = dict(spec)
        if allow_variable and isinstance(value, str) and isvar(value):
            return True
        expected = spec.get("filler_kind")
        if isinstance(value, Mapping) and set(value) == {"app"}:
            ref = value.get("app")
            if not isinstance(ref, str) or not ref:
                return False
            exists = ref in local_app_refs or self._persisted_app_exists(ref)
            if not exists:
                return False
            return expected in {"app", "state_value"} or self._frame_allows_app(
                operator, role_ref, args
            )
        if expected == "state_value":
            if isinstance(value, Mapping) and "new" in value:
                return True
            if isinstance(value, Mapping) and "literal" in value:
                return True
            return bool(isinstance(value, str) and self.s.atom(value))
        if isinstance(value, Mapping) and "new" in value:
            return expected in {None, "atom", value.get("kind")}
        if isinstance(value, Mapping) and "literal" in value:
            return bool(
                expected
                and str(expected).startswith("literal:")
                and value["literal"].get("type") == str(expected).split(":", 1)[1]
            )
        atom = self.s.atom(value) if isinstance(value, str) else None
        return bool(atom and (not expected or expected == "atom" or atom["kind"] == expected))

    @staticmethod
    def _rename(value: Any, prefix: str, mapping: dict[str, str]) -> Any:
        if isinstance(value, Mapping) and "new" in value:
            old = str(value["new"])
            mapping.setdefault(old, f"@X_{prefix}_{old.replace('@X_', '')}")
            return {"new": mapping[old], "kind": value.get("kind", "entity")}
        return value

    @staticmethod
    def _application_ref(value: Mapping[str, Any]) -> str | None:
        ref = value.get("application_ref")
        return str(ref) if isinstance(ref, str) and ref else None

    def _assert_application_graph(self, applications: list[Mapping[str, Any]]) -> set[str]:
        """Validate bounded local links while permitting exact persisted app roots.

        Candidate-local applications must all carry refs when any local link is
        present.  A link may also point to an already persisted exact application;
        such external roots are leaves for cycle detection and are never rewritten.
        """
        app_links = {
            str(value["app"])
            for item in applications
            for value in item.get("args", {}).values()
            if isinstance(value, Mapping) and set(value) == {"app"}
        }
        explicit = [self._application_ref(item) for item in applications]
        explicit_values = [ref for ref in explicit if ref]
        explicit_refs = set(explicit_values)
        if len(explicit_refs) != len(explicit_values):
            raise ValueError("duplicate candidate-local application_ref")
        local_links = app_links & explicit_refs
        if local_links and any(ref is None for ref in explicit):
            raise ValueError(
                "every application in an app-valued candidate requires application_ref"
            )
        missing = {ref for ref in app_links - explicit_refs if not self._persisted_app_exists(ref)}
        if missing:
            raise ValueError(
                "app binding references absent local/persisted application: "
                + ",".join(sorted(missing))
            )
        edges = {
            str(item["application_ref"]): {
                str(value["app"])
                for value in item.get("args", {}).values()
                if isinstance(value, Mapping)
                and set(value) == {"app"}
                and str(value["app"]) in explicit_refs
            }
            for item in applications if self._application_ref(item)
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(ref: str) -> None:
            if ref in visiting:
                raise ValueError("candidate-local application cycle")
            if ref in visited:
                return
            visiting.add(ref)
            for child in edges.get(ref, ()):
                walk(child)
            visiting.remove(ref)
            visited.add(ref)

        for ref in sorted(explicit_refs):
            walk(ref)
        return explicit_refs

    def _application(
        self,
        application: Mapping[str, Any],
        prefix: str,
        renames: dict[str, str],
        *,
        allow_variables: bool,
        local_app_refs: set[str],
    ) -> dict[str, Any]:
        operator = str(application["operator"])
        specs = self.s.roles(operator)
        if not specs:
            raise ValueError(f"unknown/non-executable operator:{operator}")
        raw_args = dict(application.get("args", {}))
        unknown_roles = set(raw_args) - set(specs)
        if unknown_roles:
            raise ValueError(f"{operator} disallows roles:{sorted(unknown_roles)}")
        args = {
            role: self._rename(value, prefix, renames)
            for role, value in raw_args.items()
        }
        for role, spec in specs.items():
            if spec["required"] and role not in args:
                raise ValueError(f"missing {operator}:{role}")
        for role, value in args.items():
            if not self._kind_ok(
                specs[role], value, operator=operator, role_ref=role,
                args=args, local_app_refs=local_app_refs,
                allow_variable=allow_variables,
            ):
                raise ValueError(f"invalid filler {operator}:{role}:{value}")
        if operator == "op:state" and "role:dimension" in args and "role:value" in args:
            dimension, state_value = args["role:dimension"], args["role:value"]
            if not (isinstance(dimension, str) and isvar(dimension)) and not (
                isinstance(state_value, str) and isvar(state_value)
            ) and not (
                isinstance(state_value, Mapping)
                and ("new" in state_value or "app" in state_value)
            ):
                self.s.validate_state_value(str(dimension), state_value)
        result = {
            "operator": operator,
            "args": args,
            "stance": application.get("stance", "support"),
        }
        ref = self._application_ref(application)
        if ref:
            result["application_ref"] = ref
        return result

    def _query(
        self,
        raw: Mapping[str, Any],
        prefix: str,
        renames: dict[str, str],
        local_app_refs: set[str],
    ) -> dict[str, Any]:
        if raw.get("operator"):
            raise ValueError("query must use QueryStructure.restrictions")
        restrictions = [
            self._application(
                item, prefix, renames, allow_variables=True,
                local_app_refs=local_app_refs,
            )
            for item in raw.get("restrictions", ())
        ]
        if not restrictions:
            raise ValueError("query requires at least one restriction")
        explicit = {
            str(item["ref"]): SemanticVariable(
                str(item["ref"]), str(item.get("filler_kind", "atom")),
                item.get("role_ref"),
            )
            for item in raw.get("variables", ())
        }
        for restriction in restrictions:
            specs = self.s.roles(restriction["operator"])
            for role, value in restriction.get("args", {}).items():
                if isinstance(value, str) and isvar(value):
                    explicit.setdefault(
                        value,
                        SemanticVariable(
                            value, str(dict(specs[role]).get("filler_kind") or "atom"), role
                        ),
                    )
        raw_projection = raw.get("projection")
        projection = (
            tuple(raw_projection) if raw_projection is not None
            else tuple(sorted(explicit))
        )
        if set(projection) - set(explicit):
            raise ValueError("query projection references undeclared variable")
        query = QueryStructure(
            str(raw.get("query_ref") or ""), tuple(restrictions),
            tuple(explicit[key] for key in sorted(explicit)), projection,
            dict(raw.get("qualifiers", {})),
        )
        if not query.query_ref:
            query = QueryStructure.from_dict(query.as_dict())
        return query.as_dict()

    def compile(self, packet: Mapping[str, Any], prefix: str = "C0"):
        source = json.loads(canonical(packet))
        if "force" not in source:
            raise ValueError("semantic packet requires explicit discourse force")
        raw_apps = list(source.get("apps", ()))
        raw_query = list((source.get("query") or {}).get("restrictions", ()))
        raw_directive = list((source.get("directive") or {}).get("content", ()))
        all_raw = raw_apps + raw_query + raw_directive
        local_app_refs = self._assert_application_graph(all_raw)
        renames: dict[str, str] = {}
        apps = [
            self._application(
                item, prefix, renames, allow_variables=False,
                local_app_refs=local_app_refs,
            )
            for item in raw_apps
        ]
        query = self._query(
            source["query"], prefix, renames, local_app_refs
        ) if source.get("query") else None
        directive = None
        if source.get("directive"):
            directive = {
                "content": [
                    self._application(
                        item, prefix, renames, allow_variables=False,
                        local_app_refs=local_app_refs,
                    )
                    for item in raw_directive
                ]
            }
        describe = source.get("describe")
        if isinstance(describe, Mapping):
            target = describe.get("target_ref")
            if not isinstance(target, str) or not self.s.atom(target):
                raise ValueError("invalid description target")
            describe = dict(describe)
        elif describe is not None and (
            not isinstance(describe, str) or not self.s.atom(describe)
        ):
            raise ValueError("invalid describe referent")

        news: list[dict[str, str]] = []
        for old, token in renames.items():
            kind = None
            for application in all_raw:
                for value in application.get("args", {}).values():
                    if isinstance(value, Mapping) and value.get("new") == old:
                        kind = value.get("kind")
            news.append({"token": token, "kind": str(kind or "entity")})
        return {
            "force": str(source["force"]),
            "apps": apps,
            "query": query,
            "directive": directive,
            "describe": describe,
            "qualifiers": dict(source.get("qualifiers", {})),
            "modality": source.get("modality", "actual"),
        }, news
