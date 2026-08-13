#!/usr/bin/env python3
"""Safely validate Diagrammatical YAML or JSON source documents."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = SKILL_ROOT / "schemas"
SCHEMA_FILES = {
    "diagram": SCHEMA_ROOT / "diagram.schema.json",
    "brand": SCHEMA_ROOT / "brand.schema.json",
    "config": SCHEMA_ROOT / "config.schema.json",
}
MAX_SOURCE_BYTES = 1_000_000
COMPLEXITY_CAPS = {
    "architecture": {"nodes": 9, "edges": 12, "groups": 4},
    "flowchart": {"nodes": 10, "edges": 14},
    "sequence": {"nodes": 5, "edges": 12, "groups": 1},
    "sitemap": {"nodes": 16, "edges": 20, "groups": 4},
    "gantt": {"nodes": 12, "edges": 20, "groups": 4},
}
ARCHITECTURE_NODE_KINDS = {
    "actor",
    "input",
    "process",
    "service",
    "component",
    "external-service",
    "data-store",
    "state",
    "note",
}
FLOWCHART_NODE_KINDS = {
    "start",
    "end",
    "outcome",
    "process",
    "decision",
    "state",
    "note",
    "input",
}
FLOWCHART_TERMINAL_KINDS = {"end", "outcome"}


class SourceLoadError(ValueError):
    """Raised when a structured source cannot be loaded safely."""


@dataclass
class ValidationResult:
    schema: str
    source: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["valid"] = self.valid
        return result


def load_structured_file(path: Path) -> dict[str, Any]:
    """Load bounded YAML/JSON using PyYAML's safe loader."""

    try:
        size = path.stat().st_size
    except OSError as exc:
        raise SourceLoadError(f"cannot read {path}: {exc}") from exc
    if size > MAX_SOURCE_BYTES:
        raise SourceLoadError(
            f"source exceeds the {MAX_SOURCE_BYTES:,}-byte validation limit: {path}"
        )
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SourceLoadError(f"could not safely parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceLoadError(f"expected a top-level object in {path}")
    return value


def load_schema(kind: str) -> dict[str, Any]:
    try:
        schema_path = SCHEMA_FILES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown schema kind: {kind}") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _path_label(path: Sequence[Any]) -> str:
    if not path:
        return "$"
    label = "$"
    for part in path:
        label += f"[{part}]" if isinstance(part, int) else f".{part}"
    return label


def _schema_errors(document: Mapping[str, Any], kind: str) -> list[str]:
    validator = Draft202012Validator(load_schema(kind), format_checker=FormatChecker())
    return [
        f"{_path_label(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    ]


def _duplicate_id_errors(document: Mapping[str, Any]) -> list[str]:
    seen: dict[str, str] = {}
    errors: list[str] = []
    collections = (
        ("node", document.get("nodes", [])),
        ("edge", document.get("edges", [])),
        ("group", document.get("groups", [])),
        ("sequence message", document.get("sequence", {}).get("messages", [])),
        ("Gantt task", document.get("gantt", {}).get("tasks", [])),
    )
    for kind, items in collections:
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            item_id = item["id"]
            if item_id in seen:
                errors.append(f"duplicate stable ID '{item_id}' used by {seen[item_id]} and {kind}")
            else:
                seen[item_id] = kind
    return errors


def _reference_errors(document: Mapping[str, Any]) -> list[str]:
    nodes = document.get("nodes", [])
    node_ids = {
        node.get("id")
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    errors: list[str] = []
    for index, edge in enumerate(document.get("edges", [])):
        if not isinstance(edge, dict):
            continue
        edge_label = edge.get("id", f"at index {index}")
        for endpoint in ("from", "to"):
            reference = edge.get(endpoint)
            if isinstance(reference, str) and reference not in node_ids:
                errors.append(
                    f"edge '{edge_label}' has unknown {endpoint} node '{reference}'; "
                    "every edge endpoint must reference a declared node"
                )
    for index, group in enumerate(document.get("groups", [])):
        if not isinstance(group, dict):
            continue
        group_label = group.get("id", f"at index {index}")
        for reference in group.get("nodes", []):
            if reference not in node_ids:
                errors.append(f"group '{group_label}' references unknown node '{reference}'")
    group_ids = {
        group.get("id")
        for group in document.get("groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str)
    }
    for node in nodes:
        if not isinstance(node, dict):
            continue
        reference = node.get("group")
        if isinstance(reference, str) and reference not in group_ids:
            errors.append(f"node '{node.get('id')}' references unknown group '{reference}'")
        position_hint = node.get("positionHint")
        if isinstance(position_hint, dict):
            near = position_hint.get("near")
            if isinstance(near, str) and near not in node_ids:
                errors.append(
                    f"node '{node.get('id')}' positionHint.near references unknown node '{near}'"
                )
    for group in document.get("groups", []):
        if not isinstance(group, dict):
            continue
        parent = group.get("parent")
        group_id = group.get("id")
        if isinstance(parent, str) and parent not in group_ids:
            errors.append(f"group '{group_id}' references unknown parent group '{parent}'")
        elif parent == group_id:
            errors.append(f"group '{group_id}' cannot be its own parent")
    presentation = document.get("presentation", {})
    if isinstance(presentation, dict):
        for reference in presentation.get("focalNodes", []):
            if reference not in node_ids:
                errors.append(f"presentation focalNodes references unknown node '{reference}'")
        constraints = presentation.get("constraints")
        if isinstance(constraints, dict):
            for reference in constraints.get("separate", []):
                if reference not in node_ids:
                    errors.append(
                        f"presentation constraints.separate references unknown node '{reference}'"
                    )
            for cluster in constraints.get("keepTogether", []):
                for reference in cluster:
                    if reference not in node_ids:
                        errors.append(
                            "presentation constraints.keepTogether references unknown node "
                            f"'{reference}'"
                        )
    sequence = document.get("sequence", {})
    if isinstance(sequence, dict):
        for index, message in enumerate(sequence.get("messages", [])):
            if not isinstance(message, dict):
                continue
            message_label = message.get("id", f"at index {index}")
            for endpoint in ("from", "to"):
                reference = message.get(endpoint)
                if isinstance(reference, str) and reference not in node_ids:
                    errors.append(
                        f"sequence message '{message_label}' has unknown {endpoint} node "
                        f"'{reference}'"
                    )
    gantt = document.get("gantt", {})
    if isinstance(gantt, dict):
        tasks = gantt.get("tasks", [])
        task_ids = {
            task.get("id")
            for task in tasks
            if isinstance(task, dict) and isinstance(task.get("id"), str)
        }
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            task_label = task.get("id", f"at index {index}")
            for dependency in task.get("dependencies", []):
                if dependency not in task_ids:
                    errors.append(
                        f"Gantt task '{task_label}' references unknown dependency '{dependency}'"
                    )
    return errors


def _architecture_errors(document: Mapping[str, Any]) -> list[str]:
    metadata = document.get("diagram", {})
    if not isinstance(metadata, dict) or metadata.get("type") != "architecture":
        return []

    errors: list[str] = []
    nodes = [node for node in document.get("nodes", []) if isinstance(node, dict)]
    groups = [group for group in document.get("groups", []) if isinstance(group, dict)]
    memberships: dict[str, list[str]] = {}
    for group in groups:
        group_id = group.get("id")
        if not isinstance(group_id, str):
            continue
        for node_id in group.get("nodes", []):
            if isinstance(node_id, str):
                memberships.setdefault(node_id, []).append(group_id)

    for node in nodes:
        node_id = node.get("id")
        node_kind = node.get("kind")
        if isinstance(node_kind, str) and node_kind not in ARCHITECTURE_NODE_KINDS:
            errors.append(
                f"architecture node '{node_id}' uses unsupported kind '{node_kind}'"
            )
        direct_groups = memberships.get(node_id, [])
        if len(direct_groups) > 1:
            errors.append(
                f"architecture node '{node_id}' belongs to multiple direct groups: "
                f"{', '.join(direct_groups)}"
            )
        declared_group = node.get("group")
        if isinstance(declared_group, str) and declared_group not in direct_groups:
            errors.append(
                f"node '{node_id}' declares group '{declared_group}' but that group does not "
                "include the node in its nodes list"
            )
        if direct_groups and isinstance(declared_group, str) and declared_group != direct_groups[0]:
            errors.append(
                f"node '{node_id}' group '{declared_group}' conflicts with membership in "
                f"'{direct_groups[0]}'"
            )

    presentation = document.get("presentation", {})
    focal_ids = set()
    if isinstance(presentation, dict):
        focal_ids.update(
            reference
            for reference in presentation.get("focalNodes", [])
            if isinstance(reference, str)
        )
    focal_ids.update(
        node["id"]
        for node in nodes
        if node.get("emphasis") == "primary" and isinstance(node.get("id"), str)
    )
    if len(focal_ids) > 2:
        errors.append(
            "architecture diagrams allow at most 2 focal elements; found "
            f"{len(focal_ids)} ({', '.join(sorted(focal_ids))})"
        )

    parents = {
        group.get("id"): group.get("parent")
        for group in groups
        if isinstance(group.get("id"), str) and isinstance(group.get("parent"), str)
    }
    for group_id in parents:
        visited: set[str] = set()
        current: str | None = group_id
        while current in parents:
            if current in visited:
                errors.append(f"group parent cycle includes '{group_id}'")
                break
            visited.add(current)
            parent = parents[current]
            current = parent if isinstance(parent, str) else None
    return errors


def _flowchart_checks(document: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    metadata = document.get("diagram", {})
    if not isinstance(metadata, dict) or metadata.get("type") != "flowchart":
        return [], []

    errors: list[str] = []
    warnings: list[str] = []
    nodes = [node for node in document.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in document.get("edges", []) if isinstance(edge, dict)]
    node_by_id = {
        node["id"]: node for node in nodes if isinstance(node.get("id"), str)
    }
    starts = [node_id for node_id, node in node_by_id.items() if node.get("kind") == "start"]
    terminals = {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("kind") in FLOWCHART_TERMINAL_KINDS
    }
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}
    incoming: dict[str, int] = {node_id: 0 for node_id in node_by_id}
    outgoing_edges: dict[str, list[dict[str, Any]]] = {
        node_id: [] for node_id in node_by_id
    }
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if isinstance(source, str) and isinstance(target, str):
            if source in adjacency and target in adjacency:
                adjacency[source].append(target)
                incoming[target] += 1
                outgoing_edges[source].append(edge)
        path_role = edge.get("path")
        if path_role in {"failure", "exception"} and not str(edge.get("label", "")).strip():
            errors.append(
                f"flowchart {path_role} edge '{edge.get('id')}' needs a text label as a "
                "non-colour path cue"
            )

    for node_id, node in node_by_id.items():
        node_kind = node.get("kind")
        if isinstance(node_kind, str) and node_kind not in FLOWCHART_NODE_KINDS:
            errors.append(f"flowchart node '{node_id}' uses unsupported kind '{node_kind}'")
        if node_kind == "decision":
            branches = outgoing_edges[node_id]
            if len(branches) < 2:
                errors.append(
                    f"flowchart decision '{node_id}' needs at least 2 outgoing paths; "
                    f"found {len(branches)}"
                )
            for edge in branches:
                if not str(edge.get("label", "")).strip():
                    errors.append(
                        f"flowchart decision '{node_id}' has unlabelled outgoing edge "
                        f"'{edge.get('id')}'; every decision branch needs a plain-language label"
                    )

    if not starts:
        errors.append("flowchart needs at least one node with kind 'start'")
    if not terminals:
        errors.append("flowchart needs at least one node with kind 'end' or 'outcome'")

    def reachable_from(origin: str) -> set[str]:
        reached: set[str] = set()
        pending = [origin]
        while pending:
            current = pending.pop()
            if current in reached:
                continue
            reached.add(current)
            pending.extend(adjacency.get(current, []))
        return reached

    reached_from_starts: set[str] = set()
    for start in starts:
        reached = reachable_from(start)
        reached_from_starts.update(reached)
        if terminals and not reached.intersection(terminals):
            errors.append(
                f"flowchart start '{start}' has no reachable end or outcome node"
            )

    for node_id in sorted(node_by_id.keys() - reached_from_starts):
        warnings.append(
            f"flowchart node '{node_id}' is unreachable from every declared start"
        )
    for node_id in sorted(node_by_id):
        if node_id not in starts and incoming[node_id] == 0:
            warnings.append(
                f"flowchart node '{node_id}' has no incoming path and is not a declared start"
            )

    cycle_nodes: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def find_cycles(node_id: str, trail: list[str]) -> None:
        if node_id in visiting:
            cycle_nodes.update(trail[trail.index(node_id) :])
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        trail.append(node_id)
        for target in adjacency.get(node_id, []):
            find_cycles(target, trail)
        trail.pop()
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_by_id:
        find_cycles(node_id, [])
    no_exit = sorted(
        node_id
        for node_id in cycle_nodes
        if not reachable_from(node_id).intersection(terminals)
    )
    if no_exit:
        warnings.append(
            "flowchart contains a cycle with no represented exit to an end or outcome: "
            + ", ".join(no_exit)
        )

    decision_count = sum(node.get("kind") == "decision" for node in nodes)
    if decision_count > 4:
        warnings.append(
            f"flowchart decision count {decision_count} exceeds the default complexity budget "
            "of 4; preserve every decision and split overview and detail flows rather than "
            "shrinking labels or nodes"
        )

    presentation = document.get("presentation", {})
    focal_ids = {
        node["id"]
        for node in nodes
        if node.get("emphasis") == "primary" and isinstance(node.get("id"), str)
    }
    if isinstance(presentation, dict):
        focal_ids.update(
            node_id
            for node_id in presentation.get("focalNodes", [])
            if isinstance(node_id, str)
        )
    if len(focal_ids) > 2:
        errors.append(
            "flowchart diagrams allow at most 2 focal elements; found "
            f"{len(focal_ids)} ({', '.join(sorted(focal_ids))})"
        )
    return errors, warnings


def _complexity_warnings(document: Mapping[str, Any]) -> list[str]:
    metadata = document.get("diagram", {})
    diagram_type = metadata.get("type") if isinstance(metadata, dict) else None
    caps = COMPLEXITY_CAPS.get(diagram_type)
    if not caps:
        return []
    warnings: list[str] = []
    for collection, cap in caps.items():
        value = document.get(collection, [])
        if isinstance(value, list) and len(value) > cap:
            warnings.append(
                f"{diagram_type} {collection} count {len(value)} exceeds the default complexity "
                f"budget of {cap}; "
                + (
                    "preserve the successful path and material exceptions, then split overview "
                    "and detail flows rather than shrinking labels or nodes; record every "
                    "simplification in the fidelity ledger"
                    if diagram_type == "flowchart"
                    else "simplify explicitly or split the diagram without silent omission"
                )
            )
    return warnings


def _unknown_config_warnings(
    value: Any, schema: Mapping[str, Any], path: tuple[str, ...] = ()
) -> list[str]:
    if not isinstance(value, dict):
        return []
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return []
    warnings: list[str] = []
    for key, child in value.items():
        child_path = (*path, key)
        if key not in properties:
            warnings.append(
                f"unknown configuration key '{'.'.join(child_path)}'; it will be ignored"
            )
            continue
        child_schema = properties[key]
        if isinstance(child_schema, dict):
            warnings.extend(_unknown_config_warnings(child, child_schema, child_path))
    return warnings


def validate_document(
    document: Mapping[str, Any], kind: str, *, source: str | None = None
) -> ValidationResult:
    """Validate a loaded document and apply semantic checks not expressible in JSON Schema."""

    result = ValidationResult(schema=kind, source=source)
    result.errors.extend(_schema_errors(document, kind))
    if kind == "diagram":
        result.errors.extend(_duplicate_id_errors(document))
        result.errors.extend(_reference_errors(document))
        result.errors.extend(_architecture_errors(document))
        flowchart_errors, flowchart_warnings = _flowchart_checks(document)
        result.errors.extend(flowchart_errors)
        result.warnings.extend(flowchart_warnings)
        result.warnings.extend(_complexity_warnings(document))
    elif kind == "config":
        result.warnings.extend(_unknown_config_warnings(document, load_schema("config")))
    return result


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def resolve_configuration(
    *,
    safety: Mapping[str, Any],
    diagram_type: Mapping[str, Any] | None = None,
    art_direction: Mapping[str, Any] | None = None,
    brand: Mapping[str, Any] | None = None,
    project: Mapping[str, Any] | None = None,
    diagram: Mapping[str, Any] | None = None,
    output_preset: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve documented precedence while applying safety as a final immutable overlay."""

    resolved: dict[str, Any] = {}
    for layer in (diagram_type, art_direction, brand, project, diagram, output_preset):
        if layer:
            resolved = _deep_merge(resolved, layer)
    return _deep_merge(resolved, safety)


def infer_schema(path: Path) -> str:
    name = path.name.lower()
    if "brand" in name:
        return "brand"
    if "config" in name:
        return "config"
    return "diagram"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="YAML or JSON document to validate")
    parser.add_argument("--schema", choices=tuple(SCHEMA_FILES), help="schema to apply")
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kind = args.schema or infer_schema(args.source)
    try:
        document = load_structured_file(args.source)
        result = validate_document(document, kind, source=str(args.source))
    except (SourceLoadError, ValueError, json.JSONDecodeError) as exc:
        result = ValidationResult(schema=kind, source=str(args.source), errors=[str(exc)])
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "passed" if result.valid else "failed"
        print(f"{kind} validation {status}: {args.source}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
