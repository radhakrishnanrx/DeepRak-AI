"""Tamper-evident append-only audit log with SHA-256 hash chain.

Each entry's ``prev_hash`` is the SHA-256 of the previous entry's serialized
form, so any historical tampering is detectable by walking the chain. The
log is plain JSONL on disk — readable by humans and standard tooling.

Designed for autonomous-agent operations where every routing decision,
operator approval, and policy gate must be recorded for after-the-fact
audit review (a common APTS / NIST AI RMF requirement).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import time
from typing import Any

from pydantic import BaseModel, Field

_GENESIS = "GENESIS"


class AuditEntry(BaseModel):
    timestamp: str
    event: str
    prev_hash: str
    details: dict[str, Any] = Field(default_factory=dict)


def _sha256_of(line: bytes) -> str:
    return hashlib.sha256(line).hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _serialize(entry: AuditEntry) -> str:
    return json.dumps(entry.model_dump(), separators=(",", ":"))


class AuditLog:
    """Append-only JSONL audit log with SHA-256 chain integrity."""

    def __init__(self, path: pathlib.Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)

    def _last_raw_line(self) -> bytes | None:
        last: bytes | None = None
        with self._path.open("rb") as fh:
            for line in fh:
                stripped = line.rstrip(b"\n")
                if stripped:
                    last = stripped
        return last

    def append(self, event: str, details: dict[str, Any] | None = None) -> AuditEntry:
        last = self._last_raw_line()
        prev_hash = _sha256_of(last) if last is not None else _GENESIS
        entry = AuditEntry(
            timestamp=_utc_now(),
            event=event,
            prev_hash=prev_hash,
            details=details or {},
        )
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(_serialize(entry) + "\n")
        return entry

    def verify(self) -> bool:
        with self._path.open("rb") as fh:
            raw_lines = [line.rstrip(b"\n") for line in fh if line.strip()]
        if not raw_lines:
            return True
        for i, raw in enumerate(raw_lines):
            entry = AuditEntry.model_validate_json(raw)
            if i == 0:
                if entry.prev_hash != _GENESIS:
                    return False
            else:
                expected = _sha256_of(raw_lines[i - 1])
                if entry.prev_hash != expected:
                    return False
        return True

    def read_all(self) -> list[AuditEntry]:
        entries: list[AuditEntry] = []
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    entries.append(AuditEntry.model_validate_json(stripped))
        return entries
