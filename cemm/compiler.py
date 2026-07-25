"""Exact structured compiler for CEMM v1.

Neural candidates may contain grounded fillers or query variables.  Exact role,
kind, state-domain and projection constraints remain authoritative here.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from cemm.cognition import QueryStructure, SemanticVariable
from cemm.model import canonical, isvar
from cemm.store import Store


class ExactStructuredCompiler:
    def __init__(self, s: Store):
        self.s = s

    def _kind_ok(self, spec, value, *, allow_variable=False):
        if allow_variable and isinstance(value, str) and isvar(value):
            return True
        expected = spec["filler_kind"]
        if expected == "state_value":
            if isinstance(value, dict) and "new" in value:
                return True
            if isinstance(value, dict) and ("literal" in value or "app" in value):
                return True
            return bool(isinstance(value, str) and self.s.atom(value))
        if isinstance(value, dict) and "new" in value:
            return expected in {None, "atom", value.get("kind")}
        if isinstance(value, dict) and "literal" in value:
            return bool(
                expected
                and expected.startswith("literal:")
                and value["literal"].get("type") == expected.split(":", 1)[1]
            )
        atom = self.s.atom(value) if isinstance(value, str) else None
        return bool(atom and (not expected or expected == "atom" or atom["kind"] == expected))

    @staticmethod
    def _rename(value, prefix, mapping):
        if isinstance(value, dict) and "new" in value:
            old = value["new"]
            if old not in mapping:
                mapping[old] = f"@X_{prefix}_{old.replace('@X_', '')}"
            return {"new": mapping[old], "kind": value.get("kind", "entity")}
        return value

    def _application(
        self,
        application: Mapping[str, Any],
        prefix: str,
        renames: dict[str, str],
        *,
        allow_variables: bool,
    ) -> dict[str, Any]:
        operator = str(application["operator"])
        specs = self.s.roles(operator)
        if not specs:
            raise ValueError(f"unknown/non-executable operator:{operator}")
        args = {
            role: self._rename(value, prefix, renames)
            for role, value in application.get("args", {}).items()
            if role in specs
        }

        # Unique value→dimension completion is a grounded normalization only.
        # It must never replace first-class query variables or ambiguous domains.
        if (
            operator == "op:state"
            and "role:dimension" not in args
            and "role:value" in args
            and isinstance(args["role:value"], str)
            and not isvar(args["role:value"])
        ):
            dimension = self.s.infer_state_dimension(args["role:value"])
            if dimension:
                args["role:dimension"] = dimension

        for role, spec in specs.items():
            if spec["required"] and role not in args:
                raise ValueError(f"missing {operator}:{role}")
        for role, value in args.items():
            if not self._kind_ok(specs[role], value, allow_variable=allow_variables):
                raise ValueError(f"invalid filler {operator}:{role}:{value}")

        if operator == "op:state" and "role:dimension" in args and "role:value" in args:
            dimension = args["role:dimension"]
            state_value = args["role:value"]
            if not (isinstance(dimension, str) and isvar(dimension)) and not (
                isinstance(state_value, str) and isvar(state_value)
            ) and not (isinstance(state_value, dict) and "new" in state_value):
                self.s.validate_state_value(str(dimension), state_value)
        return {"operator": operator, "args": args, "stance": application.get("stance", "support")}

    def _query(self, raw: Mapping[str, Any], prefix: str, renames: dict[str, str]) -> dict[str, Any]:
        if raw.get("operator"):
            raw = {"restrictions": [dict(raw)]}
        restrictions = [
            self._application(item, prefix, renames, allow_variables=True)
            for item in raw.get("restrictions", ())
        ]
        if not restrictions:
            raise ValueError("query requires at least one restriction")

        explicit = {
            str(item["ref"]): SemanticVariable(
                str(item["ref"]),
                str(item.get("filler_kind", "atom")),
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
                        SemanticVariable(value, str(specs[role]["filler_kind"] or "atom"), role),
                    )
        projection = tuple(raw.get("projection", ())) or tuple(sorted(explicit))
        if set(projection) - set(explicit):
            raise ValueError("query projection references undeclared variable")
        query = QueryStructure(
            query_ref=str(raw.get("query_ref") or ""),
            restrictions=tuple(restrictions),
            variables=tuple(explicit[k] for k in sorted(explicit)),
            projection=projection,
            qualifiers=dict(raw.get("qualifiers", {})),
        )
        if not query.query_ref:
            query = QueryStructure.from_dict(query.as_dict())
        return query.as_dict()

    def compile(self, packet, prefix="C0"):
        source = json.loads(canonical(packet))
        renames: dict[str, str] = {}
        news: list[dict[str, str]] = []
        force = source.get("force") or (
            "query" if source.get("query") else "description_request" if source.get("describe") else "claim"
        )
        apps = [
            self._application(item, prefix, renames, allow_variables=False)
            for item in source.get("apps", ())
        ]
        query = self._query(source["query"], prefix, renames) if source.get("query") else None
        directive = None
        if source.get("directive"):
            directive = {
                "content": [
                    self._application(item, prefix, renames, allow_variables=False)
                    for item in source["directive"].get("content", ())
                ]
            }
        describe = source.get("describe")
        if describe is not None and (not isinstance(describe, str) or not self.s.atom(describe)):
            raise ValueError("invalid describe referent")

        searchable = list(source.get("apps", ()))
        if source.get("query"):
            searchable += list(source["query"].get("restrictions", ())) if not source["query"].get("operator") else [source["query"]]
        if source.get("directive"):
            searchable += list(source["directive"].get("content", ()))
        for old, token in renames.items():
            kind = None
            for application in searchable:
                for value in application.get("args", {}).values():
                    if isinstance(value, dict) and value.get("new") == old:
                        kind = value.get("kind")
            news.append({"token": token, "kind": kind or "entity"})

        return {
            "force": force,
            "apps": apps,
            "query": query,
            "directive": directive,
            "describe": describe,
            "qualifiers": dict(source.get("qualifiers", {})),
            "modality": source.get("modality", "actual"),
        }, news
