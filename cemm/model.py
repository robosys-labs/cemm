"""Core model types and helper functions for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 51-69).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Import TOK from constants if available, otherwise define inline from v4 line 48.
try:
    from cemm.constants import TOK
except ImportError:
    TOK = re.compile(
        r"@[aAxX][0-9]+|@[0-9]+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]",
        re.UNICODE,
    )


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def stable(prefix, *parts):
    return f"{prefix}:{hashlib.sha256(canonical(parts).encode()).hexdigest()[:24]}"


def norm_text(s):
    return unicodedata.normalize("NFKC", str(s)).casefold()


def toks(s):
    return TOK.findall(unicodedata.normalize("NFKC", str(s)).strip())


def surface(ts):
    s = " ".join(ts)
    s = re.sub(r"\s+([.,!?;:])", r"\1", s)
    s = re.sub(r"([('¿¡])\s+", r"\1", s)
    s = re.sub(r"\s+([)'])", r"\1", s)
    return s[:1].upper() + s[1:] if s else s


def lit(value, typ="text"):
    return {"literal": {"type": typ, "value": value}}


def isvar(x):
    return isinstance(x, str) and x.startswith("?")


def isexist(x):
    return isinstance(x, str) and x.startswith("!")


class AmbiguousReferent(ValueError):
    def __init__(self, surface, candidates):
        self.surface = surface
        self.candidates = candidates
        super().__init__(surface)


@dataclass(frozen=True)
class Fact:
    ref: str
    operator: str
    args: dict[str, Any]
    stance: str = "support"
    confidence: float = 1.0
    derived: bool = False
    proof: dict[str, Any] | None = None

    def signature(self):
        return stable(
            "fact",
            self.operator,
            sorted(self.args.items(), key=lambda x: x[0]),
            self.stance,
        )
