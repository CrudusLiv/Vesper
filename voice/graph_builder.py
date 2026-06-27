"""Parse the Dynamous/Memory vault into a vis.js node/edge graph.

Walks all .md files recursively, extracts [[wikilinks]] as edges.
Skips noisy directories: daily/, finance/, inbox/, state/.
Returns {"nodes": [...], "edges": [...]} ready for vis.js Network.
"""
from __future__ import annotations

import re
from pathlib import Path

_VAULT = Path(__file__).resolve().parents[1] / "Dynamous" / "Memory"
_WIKILINK = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]')

# Directories to skip (too noisy or personal)
_SKIP_DIRS = {"daily", "finance", "inbox", "state", "_processed"}


def build() -> dict:
    """Return vis.js graph data from the full vault."""
    if not _VAULT.exists():
        return {"nodes": [], "edges": []}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for md in _VAULT.rglob("*.md"):
        # Skip excluded directories
        parts = {p.name for p in md.parents}
        if parts & _SKIP_DIRS:
            continue

        # Node id = path relative to vault, label = stem
        rel = md.relative_to(_VAULT)
        node_id = str(rel).replace("\\", "/")
        label = md.stem.replace("_", " ")

        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "title": node_id,
                "group": rel.parts[0] if len(rel.parts) > 1 else "root",
            }

        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for m in _WIKILINK.finditer(text):
            raw = m.group(1).strip()
            if not raw:
                continue
            # Resolve target: could be a stem or a partial path
            target_id = _resolve(raw, nodes)
            if target_id == node_id:
                continue
            key = (node_id, target_id)
            if key not in seen:
                edges.append({"from": node_id, "to": target_id})
                seen.add(key)
                if target_id not in nodes:
                    nodes[target_id] = {
                        "id": target_id,
                        "label": raw.replace("_", " "),
                        "title": raw,
                        "group": "unresolved",
                    }

    return {"nodes": list(nodes.values()), "edges": edges}


def _resolve(raw: str, existing: dict[str, dict]) -> str:
    """Try to match a wikilink target to an existing node id by stem."""
    # Exact match
    if raw in existing:
        return raw
    # Stem match (case-insensitive)
    raw_lower = raw.lower()
    for nid in existing:
        stem = Path(nid).stem.lower()
        if stem == raw_lower:
            return nid
    # Fall back to raw as a virtual node
    return raw
