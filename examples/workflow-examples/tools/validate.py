#!/usr/bin/env python3
"""Validate a `kind = "workflow"` plugin package before it is published.

The layout rules come from the workflow package decision
(specs/decisions/desktop/plugin/category/workflow/0-workflow-package-format.md).
The per-document checks mirror the first-phase publish gate Cloud runs on
import (cloud/internal/core/workflow_graph.go). Cloud is the consumer that
turns a document into a runnable workflow, so a document that this script
accepts must be one Cloud accepts too.

One check is deliberately stricter than today's publish gate: a cycle is
refused, because no example should depend on a graph the scheduler cannot
settle. Every other rule matches the gate.

Usage:
    python3 tools/validate.py [PACKAGE_DIR]

Exit status is 0 when the package is valid and 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

# Node kinds the first phase executes.
EXECUTABLE_NODE_KINDS = {"start", "agent", "condition", "output"}

# Agent configuration fields the first phase does not execute. Cloud refuses a
# document that carries any of them with a non-null value -- an empty array or
# object counts, because the key is still a claim the author made.
UNSUPPORTED_AGENT_CONFIG_FIELDS = (
    "skills",
    "mcps",
    "interactive",
    "outputContract",
    "retry",
    "promptInactivity",
)

DEFAULT_SLOT = "default"
SLOT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

MIN_SLOT_DESCRIPTION_RUNES = 1
MAX_SLOT_DESCRIPTION_RUNES = 500
MAX_SLOT_HINT_RUNES = 200
MAX_DOCUMENT_NAME_BYTES = 200
MAX_DOCUMENTS = 256
WORKFLOW_DOCUMENT_DIR = Path("assets") / "workflows"


def as_text(value: object) -> str:
    """Return a string field the way Cloud reads it: anything else is empty."""
    return value if isinstance(value, str) else ""


def rune_count(text: str) -> int:
    """Count Unicode characters, the unit Cloud uses for slot bounds."""
    return len(text)


def has_control_characters(text: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in text)


def problem(code: str, *, source: Path | None = None, **fields: str) -> dict:
    """Build one stable, machine-readable validation problem."""
    out: dict = {"code": code}
    if source is not None:
        out["source"] = str(source)
    for key, value in fields.items():
        if value:
            out[key] = value
    return out


def validate_manifest(root: Path, problems: list[dict]) -> dict:
    """Read `orax.toml` and check the constraints that belong to this kind."""
    manifest_path = root / "orax.toml"
    if not manifest_path.is_file():
        problems.append(problem("manifest_missing", source=manifest_path))
        return {}
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        problems.append(problem("manifest_unreadable", source=manifest_path, detail=str(error)))
        return {}

    kind = manifest.get("kind")
    if kind != "workflow":
        problems.append(problem("manifest_kind_invalid", source=manifest_path, detail=repr(kind)))

    identifier = manifest.get("identifier")
    if not isinstance(identifier, str):
        problems.append(problem("manifest_identifier_missing", source=manifest_path))
    elif not valid_plugin_name(identifier):
        problems.append(problem("manifest_identifier_invalid", source=manifest_path, detail=identifier))

    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.match(version):
        problems.append(problem("manifest_version_invalid", source=manifest_path, detail=repr(version)))

    for field, limit in (("title", 128), ("description", 1000)):
        value = manifest.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value or value.strip() != value:
            problems.append(problem(f"manifest_{field}_invalid", source=manifest_path))
        elif len(value.encode("utf-8")) > limit or has_control_characters(value):
            problems.append(problem(f"manifest_{field}_invalid", source=manifest_path))

    license_value = manifest.get("license")
    if license_value is not None:
        if (
            not isinstance(license_value, str)
            or not license_value
            or len(license_value.encode("utf-8")) > 256
            or not license_value.isascii()
        ):
            problems.append(problem("manifest_license_invalid", source=manifest_path))

    # A workflow package is processless and universal: it may not ship a
    # platform-targeted artifact or any kind-specific section.
    for section in ("targets", "artifact", "webview", "workbench"):
        if section in manifest:
            problems.append(problem("manifest_section_not_allowed", source=manifest_path, field=section))

    return manifest


def valid_plugin_name(value: str) -> bool:
    """Check the canonical Plugin ID grammar: one or two slug segments, <=128 bytes."""
    if not value or len(value.encode("utf-8")) > 128:
        return False
    segments = value.split(".")
    if len(segments) > 2:
        return False
    return all(
        segment
        and len(segment.encode("utf-8")) <= 63
        and SLUG_PATTERN.match(segment)
        and "--" not in segment
        for segment in segments
    )


def workflow_documents(root: Path, problems: list[dict]) -> list[Path]:
    """List the direct `*.json` children of `assets/workflows/`, ignoring the rest."""
    directory = root / WORKFLOW_DOCUMENT_DIR
    if not directory.is_dir():
        problems.append(problem("workflows_directory_missing", source=directory))
        return []

    documents: list[Path] = []
    for entry in sorted(directory.iterdir(), key=lambda path: path.name):
        if entry.is_symlink() or not entry.is_file():
            continue
        if entry.suffix.lower() != ".json":
            continue
        documents.append(entry)

    if not documents:
        problems.append(problem("workflows_directory_empty", source=directory))
    elif len(documents) > MAX_DOCUMENTS:
        problems.append(
            problem("workflows_too_many", source=directory, detail=f"{len(documents)} > {MAX_DOCUMENTS}")
        )
    return documents


def validate_package(root: Path) -> list[dict]:
    """Validate one package directory and return every problem found."""
    problems: list[dict] = []
    validate_manifest(root, problems)
    for document in workflow_documents(root, problems):
        validate_document_file(document, problems)
    return problems


def validate_document_file(path: Path, problems: list[dict]) -> None:
    try:
        content = path.read_bytes()
    except OSError as error:
        problems.append(problem("document_unreadable", source=path, detail=str(error)))
        return
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        problems.append(problem("document_invalid_json", source=path, detail=str(error)))
        return
    if not isinstance(document, dict):
        problems.append(problem("document_not_an_object", source=path))
        return
    validate_document(document, path, problems)


def validate_document(document: dict, source: Path, problems: list[dict]) -> None:
    """Mirror Cloud's publish gate for one document."""
    name = as_text(document.get("name")).strip()
    if not name:
        problems.append(problem("document_name_missing", source=source))
    elif len(name.encode("utf-8")) > MAX_DOCUMENT_NAME_BYTES:
        problems.append(problem("document_name_too_long", source=source))

    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        problems.append(problem("nodes_not_a_list", source=source))
        nodes = []
    edges = document.get("edges")
    if not isinstance(edges, list):
        problems.append(problem("edges_not_a_list", source=source))
        edges = []

    nodes_by_id = validate_nodes(nodes, source, problems)
    validate_edges(edges, nodes_by_id, source, problems)
    declared_slots = validate_slots(document, source, problems)
    validate_slot_references(nodes, declared_slots, source, problems)
    validate_acyclic(nodes_by_id, edges, source, problems)


def validate_nodes(nodes: list, source: Path, problems: list[dict]) -> dict[str, dict]:
    """Check node identity and kind; return the first node seen for each id."""
    seen: dict[str, dict] = {}
    starts = 0
    for raw in nodes:
        if not isinstance(raw, dict):
            problems.append(problem("node_not_an_object", source=source))
            continue
        node_id = as_text(raw.get("id"))
        if not node_id:
            problems.append(problem("node_id_missing", source=source))
            continue
        if node_id in seen:
            problems.append(problem("node_id_duplicate", source=source, nodeId=node_id))
            continue
        seen[node_id] = raw
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        kind = as_text(data.get("kind"))
        if not kind:
            problems.append(problem("node_kind_missing", source=source, nodeId=node_id))
        elif kind not in EXECUTABLE_NODE_KINDS:
            problems.append(problem("node_kind_unsupported", source=source, nodeId=node_id, kind=kind))
        elif kind == "start":
            starts += 1
        elif kind == "agent":
            validate_agent_config(data, source, node_id, problems)
    if starts != 1:
        problems.append(problem("start_node_count", source=source, detail=str(starts)))
    return seen


def validate_agent_config(data: dict, source: Path, node_id: str, problems: list[dict]) -> None:
    config = data.get("agentConfig")
    if not isinstance(config, dict):
        return
    for field in UNSUPPORTED_AGENT_CONFIG_FIELDS:
        if field in config and config[field] is not None:
            problems.append(
                problem("node_config_unsupported", source=source, nodeId=node_id, field=field)
            )


def validate_edges(edges: list, nodes_by_id: dict[str, dict], source: Path, problems: list[dict]) -> None:
    for raw in edges:
        if not isinstance(raw, dict):
            problems.append(problem("edge_not_an_object", source=source))
            continue
        for endpoint in ("source", "target"):
            value = as_text(raw.get(endpoint))
            if not value or value not in nodes_by_id:
                problems.append(
                    problem("edge_endpoint_unknown", source=source, nodeId=value or f"<{endpoint}>")
                )


def validate_slots(document: dict, source: Path, problems: list[dict]) -> set[str]:
    """Check declared slots; return the names Cloud would consider declared."""
    declared: set[str] = set()
    raw_slots = document.get("executorSlots")
    slots = raw_slots if isinstance(raw_slots, list) else []
    for raw in slots:
        if not isinstance(raw, dict):
            continue
        name = as_text(raw.get("name"))
        if not name:
            problems.append(problem("slot_name_missing", source=source))
        elif not SLOT_NAME_PATTERN.match(name):
            problems.append(problem("slot_name_invalid", source=source, slot=name))
        elif name == DEFAULT_SLOT:
            problems.append(problem("slot_name_reserved", source=source, slot=name))
        elif name in declared:
            problems.append(problem("slot_name_duplicate", source=source, slot=name))
        if name:
            # Cloud records the name even when another check already refused it, so a
            # duplicate reference is not reported twice.
            declared.add(name)

        description = as_text(raw.get("description")).strip()
        if not (MIN_SLOT_DESCRIPTION_RUNES <= rune_count(description) <= MAX_SLOT_DESCRIPTION_RUNES):
            problems.append(problem("slot_description_invalid", source=source, slot=name))

        hint = raw.get("hint")
        if "hint" in raw and hint is not None and not valid_slot_hint(hint):
            problems.append(problem("slot_hint_invalid", source=source, slot=name))
    return declared


def valid_slot_hint(hint: object) -> bool:
    if not isinstance(hint, dict):
        return False
    for key in ("agentCli", "modelId"):
        if key not in hint or hint[key] is None:
            continue
        value = hint[key]
        if not isinstance(value, str) or not value or rune_count(value) > MAX_SLOT_HINT_RUNES:
            return False
    return True


def validate_slot_references(
    nodes: list, declared: set[str], source: Path, problems: list[dict]
) -> None:
    """Refuse an agent node that names a slot the graph never declares."""
    references: dict[str, list[str]] = {}
    for raw in nodes:
        if not isinstance(raw, dict):
            continue
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        if as_text(data.get("kind")) != "agent":
            continue
        node_id = as_text(raw.get("id"))
        if not node_id:
            continue
        config = data.get("agentConfig") if isinstance(data.get("agentConfig"), dict) else {}
        slot = as_text(config.get("executorSlot")) or DEFAULT_SLOT
        references.setdefault(slot, []).append(node_id)
    for slot, node_ids in references.items():
        if slot == DEFAULT_SLOT or slot in declared:
            continue
        for node_id in node_ids:
            problems.append(problem("slot_not_declared", source=source, nodeId=node_id, slot=slot))


def validate_acyclic(
    nodes_by_id: dict[str, dict], edges: list, source: Path, problems: list[dict]
) -> None:
    """Refuse a cycle. The gate may not check this yet; an example must be executable."""
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
    indegree = {node_id: 0 for node_id in nodes_by_id}
    for raw in edges:
        if not isinstance(raw, dict):
            continue
        upstream = as_text(raw.get("source"))
        downstream = as_text(raw.get("target"))
        if upstream not in adjacency or downstream not in adjacency:
            continue
        adjacency[upstream].append(downstream)
        indegree[downstream] += 1

    ready = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node_id = ready.pop()
        visited += 1
        for downstream in adjacency[node_id]:
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)
    if visited != len(adjacency):
        problems.append(problem("graph_cycle", source=source))


def format_problem(item: dict) -> str:
    location = item.get("source", "")
    detail = item.get("detail", "")
    fields = " ".join(
        f"{key}={value}" for key, value in item.items() if key not in {"code", "source", "detail"}
    )
    suffix = " ".join(part for part in (fields, detail) if part)
    return f"{location}: {item['code']}" + (f" ({suffix})" if suffix else "")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate a workflow plugin package.")
    parser.add_argument(
        "package",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1]),
        help="package directory (default: the package containing this tool)",
    )
    args = parser.parse_args(argv)

    root = Path(args.package).resolve()
    problems = validate_package(root)
    for item in problems:
        print(format_problem(item), file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s) in {root}", file=sys.stderr)
        return 1
    print(f"{root}: valid workflow package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
