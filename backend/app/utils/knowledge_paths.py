"""Canonical knowledge-base source_doc paths and matching."""

from __future__ import annotations

from pathlib import Path


def canonical_knowledge_source_doc(rel_folder: str, relative_path: str) -> str:
    """Return stable source_doc: knowledge_base/{engagement_folder}/{file}."""
    rel = str(relative_path).replace("\\", "/").lstrip("/")
    folder = str(rel_folder).replace("\\", "/").strip("/")
    if rel.startswith("knowledge_base/"):
        return rel
    return f"knowledge_base/{folder}/{rel}"


def source_doc_aliases(source_doc: str) -> set[str]:
    """Expand a source_doc into comparable aliases (full / relative / basename)."""
    raw = str(source_doc).replace("\\", "/").strip()
    if not raw:
        return set()
    aliases = {raw, Path(raw).name}
    prefix = "knowledge_base/"
    if raw.startswith(prefix):
        aliases.add(raw[len(prefix) :])
    return {a for a in aliases if a}


def is_document_source_indexed(
    indexed_sources: set[str],
    rel_folder: str,
    doc_path: str,
) -> bool:
    """True if any indexed source_doc aliases overlap this manifest document."""
    wanted: set[str] = set()
    for candidate in (
        canonical_knowledge_source_doc(rel_folder, doc_path),
        f"{rel_folder}/{doc_path}".replace("\\", "/"),
        str(doc_path).replace("\\", "/"),
    ):
        wanted |= source_doc_aliases(candidate)
    have: set[str] = set()
    for src in indexed_sources:
        have |= source_doc_aliases(src)
    return bool(wanted & have)
