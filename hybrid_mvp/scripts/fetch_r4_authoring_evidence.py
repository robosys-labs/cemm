#!/usr/bin/env python3
"""Fetch one pinned R4 advisory-evidence source into an offline snapshot."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import sys
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cemm_authoritative_hybrid.r4_authoring_evidence import (  # noqa: E402
    EVIDENCE_LICENSE_POLICIES,
    EVIDENCE_SOURCE_FAMILIES,
    MAX_EVIDENCE_BYTES,
    MAX_EVIDENCE_SOURCES,
    EvidenceSource,
    write_evidence_snapshot,
)


def _exact_string(value: object, name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be an exact nonempty string")
    return value


def _exact_sha256(value: object) -> str:
    digest = _exact_string(value, "expected_sha256")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("expected_sha256 must be lowercase SHA-256")
    return digest


@dataclass(frozen=True)
class FetchRequest:
    source_family: str
    url: str
    revision: str
    expected_sha256: str
    expected_byte_limit: int
    license_id: str
    license_policy: str
    output_directory: Path

    @classmethod
    def from_dict(cls, value: object) -> "FetchRequest":
        fields = {
            "source_family",
            "url",
            "revision",
            "expected_sha256",
            "expected_byte_limit",
            "license_id",
            "license_policy",
            "output_directory",
        }
        if type(value) is not dict or set(value) != fields:
            raise ValueError("fetch request has unknown or missing fields")
        family = _exact_string(value["source_family"], "source_family")
        if family not in EVIDENCE_SOURCE_FAMILIES:
            raise ValueError("unsupported evidence source family")
        url = _exact_string(value["url"], "url")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("evidence URL must be an unauthenticated HTTPS URL")
        if parsed.fragment:
            raise ValueError("evidence URL must not contain a fragment")
        limit = value["expected_byte_limit"]
        if type(limit) is not int or not 0 < limit <= MAX_EVIDENCE_BYTES:
            raise ValueError("expected_byte_limit is outside the evidence bound")
        policy = _exact_string(value["license_policy"], "license_policy")
        if policy not in EVIDENCE_LICENSE_POLICIES:
            raise ValueError("unsupported evidence license policy")
        return cls(
            source_family=family,
            url=url,
            revision=_exact_string(value["revision"], "revision"),
            expected_sha256=_exact_sha256(value["expected_sha256"]),
            expected_byte_limit=limit,
            license_id=_exact_string(value["license_id"], "license_id"),
            license_policy=policy,
            output_directory=Path(
                _exact_string(value["output_directory"], "output_directory")
            ),
        )


def validate_redirect(source_url: str, target_url: str) -> None:
    source = urlparse(source_url)
    target = urlparse(target_url)
    if source.scheme != "https" or target.scheme != "https" or not target.netloc:
        raise ValueError("redirect must retain an HTTPS origin")
    if target.username or target.password or target.fragment:
        raise ValueError("redirect target contains forbidden URL components")


class StrictHttpsRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_redirect(req.full_url, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_zip_bytes(payload: bytes) -> None:
    if not zipfile.is_zipfile(io.BytesIO(payload)):
        return
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_EVIDENCE_SOURCES:
            raise ValueError("ZIP file-count bound exceeded")
        total = 0
        for info in infos:
            name = info.filename
            parsed = PurePosixPath(name)
            if (
                "\\" in name
                or parsed.is_absolute()
                or any(part in {"", ".", ".."} for part in parsed.parts)
            ):
                raise ValueError("unsafe ZIP path")
            unix_mode = info.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ValueError("ZIP link entries are forbidden")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted ZIP entries are forbidden")
            total += info.file_size
            if total > MAX_EVIDENCE_BYTES:
                raise ValueError("ZIP expanded-byte bound exceeded")


def _download(request: FetchRequest) -> bytes:
    opener = build_opener(StrictHttpsRedirectHandler())
    http_request = Request(
        request.url,
        headers={"User-Agent": "CEMM-R4-evidence-fetch/1"},
        method="GET",
    )
    chunks: list[bytes] = []
    total = 0
    with opener.open(http_request, timeout=30) as response:
        final_url = response.geturl()
        validate_redirect(request.url, final_url)
        length = response.headers.get("Content-Length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if declared < 0 or declared > request.expected_byte_limit:
                raise ValueError("declared evidence byte bound exceeded")
        while True:
            chunk = response.read(min(64 * 1024, request.expected_byte_limit + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > request.expected_byte_limit:
                raise ValueError("downloaded evidence byte bound exceeded")
            chunks.append(chunk)
    return b"".join(chunks)


def fetch(request: FetchRequest) -> EvidenceSource:
    if type(request) is not FetchRequest:
        raise TypeError("request must be exact FetchRequest")
    payload = _download(request)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != request.expected_sha256:
        raise ValueError("downloaded evidence SHA-256 mismatch")
    validate_zip_bytes(payload)
    suffix = ".zip" if zipfile.is_zipfile(io.BytesIO(payload)) else ".bin"
    source = EvidenceSource.create(
        source_family=request.source_family,
        revision=request.revision,
        sha256=digest,
        byte_length=len(payload),
        license_id=request.license_id,
        license_policy=request.license_policy,
        relative_path=f"raw/{request.source_family}{suffix}",
    )
    write_evidence_snapshot(request.output_directory, ((source, payload),))
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.request.stat().st_size > 64 * 1024:
        raise ValueError("fetch request byte bound exceeded")
    raw = args.request.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("fetch request must be valid UTF-8 JSON") from exc
    request = FetchRequest.from_dict(value)
    source = fetch(request)
    print(json.dumps(source.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
