#!/usr/bin/env python3
"""Safely extract supported Mermaid meaning for Diagrammatical editorial redraw."""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 200_000
MAX_BLOCKS = 20
MAX_NODES = 100
MAX_EDGES = 200
MAX_PARTICIPANTS = 30
MAX_MESSAGES = 200
MAX_TASKS = 100
FENCE = re.compile(r"```\s*mermaid\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)
GRAMMAR = re.compile(r"^\s*(flowchart|graph|sequenceDiagram|gantt)\b(?:\s+([^\n]+))?", re.I)
ID = re.compile(r"[^a-z0-9]+")
EXTERNAL_URL = re.compile(r"(?:https?|javascript|data):", re.I)
UNSAFE_DIRECTIVE = re.compile(r"^\s*(?:click|callback|linkStyle)\b", re.I)
INIT_DIRECTIVE = re.compile(r"^\s*%%\{")


class MermaidImportError(ValueError):
    """Named bounded importer failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _slug(value: str, fallback: str) -> str:
    result = ID.sub("-", value.lower()).strip("-")
    return result[:80] or fallback


def _clean_label(value: str) -> tuple[str, bool]:
    raw = value.strip().strip("\"'")
    decoded = html.unescape(raw)
    cleaned = re.sub(r"<[^>]*>", "", decoded).strip()
    return cleaned, cleaned != raw


def _lines(text: str) -> list[str]:
    output: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if UNSAFE_DIRECTIVE.match(line):
            code = "external-reference" if EXTERNAL_URL.search(line) else "unsafe-directive"
            raise MermaidImportError(
                code, f"interactive Mermaid directive is not supported: {line}"
            )
        if EXTERNAL_URL.search(line):
            raise MermaidImportError(
                "external-reference", "Mermaid external URLs are not followed or imported"
            )
        output.append(line)
    return output


def extract_blocks(text: str, suffix: str = "") -> list[str]:
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise MermaidImportError(
            "input-too-large", f"Mermaid input exceeds the {MAX_INPUT_BYTES:,}-byte limit"
        )
    if suffix.lower() in {".md", ".markdown"} or "```" in text:
        blocks = [block.strip() for block in FENCE.findall(text)]
        if not blocks:
            raise MermaidImportError("missing-mermaid-block", "Markdown contains no Mermaid fence")
        if len(blocks) > MAX_BLOCKS:
            raise MermaidImportError(
                "resource-limit",
                f"Markdown contains {len(blocks)} Mermaid blocks; maximum is {MAX_BLOCKS}",
            )
        return blocks
    return [text.strip()]


def _fidelity(source: str, block_index: int, grammar: str) -> dict[str, Any]:
    return {
        "source": source,
        "selectedBlock": block_index,
        "detectedGrammar": grammar,
        "originalCount": 0,
        "finalVisibleCount": 0,
        "preserved": [],
        "normalisedLabels": [],
        "merged": [],
        "collapsed": [],
        "omitted": [],
        "unsupported": [],
        "assumptions": [],
        "requestedTypeChange": None,
    }


def _base_diagram(
    *, diagram_id: str, title: str, diagram_type: str, composition: str, direction: str
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "diagram": {
            "id": diagram_id,
            "title": title,
            "description": f"Editorial redraw of imported Mermaid {diagram_type} content.",
            "type": diagram_type,
            "audience": "mixed",
            "purpose": "Explain the imported structure clearly",
            "primaryMessage": title,
        },
        "nodes": [],
        "edges": [],
        "groups": [],
        "presentation": {
            "composition": composition,
            "direction": direction,
            "brand": "editorial-blueprint",
            "style": "editorial",
            "mode": "light",
            "detail": "balanced",
            "outputPreset": "document-wide",
            "focalNodes": [],
        },
        "fidelity": {"source": "Mermaid import", "collapsed": [], "omitted": [], "assumptions": []},
    }


NODE_TOKEN = re.compile(
    r"^([A-Za-z0-9_-]+)(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|\[\((.*?)\)\])?$"
)
EDGE = re.compile(r"^(.+?)\s*(-->|---|-.->|==>|--x|--o)\s*(?:\|([^|]*)\|\s*)?(.+?)$")


def _parse_node(token: str) -> tuple[str, str, str, bool]:
    token = token.strip()
    match = NODE_TOKEN.match(token)
    if not match:
        raise MermaidImportError("malformed-syntax", f"unsupported flowchart node syntax: {token}")
    node_id = _slug(match.group(1), "node")
    raw_label = next((value for value in match.groups()[1:] if value is not None), match.group(1))
    label, normalised = _clean_label(raw_label)
    kind = (
        "decision" if match.group(4) is not None else "data-store" if match.group(5) else "process"
    )
    if node_id in {"start", "begin"}:
        kind = "start"
    elif node_id in {"end", "done", "finish", "complete"}:
        kind = "end"
    return node_id, label or node_id, kind, normalised


def _parse_flowchart(
    block: str, source: str, block_index: int, grammar_name: str, direction_raw: str | None
) -> dict[str, Any]:
    direction_map = {
        "LR": "left-to-right",
        "RL": "right-to-left",
        "TB": "top-to-bottom",
        "TD": "top-to-bottom",
        "BT": "bottom-to-top",
    }
    direction = direction_map.get((direction_raw or "TD").upper(), "top-to-bottom")
    lines = _lines(block)[1:]
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    group_stack: list[dict[str, Any]] = []
    normalised_labels: list[dict[str, str]] = []
    for line in lines:
        if line.lower().startswith(("direction ", "classdef ", "class ", "style ")):
            continue
        if line.lower().startswith("subgraph "):
            raw = line.split(None, 1)[1]
            group_id, label, _, changed = _parse_node(raw)
            group = {"id": group_id, "label": label, "kind": "section", "nodes": []}
            groups.append(group)
            group_stack.append(group)
            if changed:
                normalised_labels.append({"source": raw, "resolved": label})
            continue
        if line.lower() == "end":
            if not group_stack:
                raise MermaidImportError("malformed-syntax", "subgraph end has no matching start")
            group_stack.pop()
            continue
        match = EDGE.match(line)
        if match:
            left, arrow, edge_label, right = match.groups()
            from_id, from_label, from_kind, from_changed = _parse_node(left)
            to_id, to_label, to_kind, to_changed = _parse_node(right)
            for node_id, label, kind in (
                (from_id, from_label, from_kind),
                (to_id, to_label, to_kind),
            ):
                nodes.setdefault(node_id, {"id": node_id, "label": label, "kind": kind})
                if group_stack and node_id not in group_stack[-1]["nodes"]:
                    group_stack[-1]["nodes"].append(node_id)
            label, label_changed = _clean_label(edge_label or "")
            edge_id = _slug(f"{from_id}-{label or 'to'}-{to_id}", f"edge-{len(edges) + 1}")
            edges.append(
                {
                    "id": edge_id,
                    "from": from_id,
                    "to": to_id,
                    "label": label,
                    "kind": "action",
                    "path": "conditional" if from_kind == "decision" else "normal",
                    "direction": "forward" if arrow not in {"---"} else "none",
                    "optional": arrow == "-.->",
                }
            )
            for raw, resolved, changed in (
                (left, from_label, from_changed),
                (right, to_label, to_changed),
                (edge_label or "", label, label_changed),
            ):
                if changed:
                    normalised_labels.append({"source": raw, "resolved": resolved})
            continue
        node_id, label, kind, changed = _parse_node(line)
        nodes.setdefault(node_id, {"id": node_id, "label": label, "kind": kind})
        if group_stack and node_id not in group_stack[-1]["nodes"]:
            group_stack[-1]["nodes"].append(node_id)
        if changed:
            normalised_labels.append({"source": line, "resolved": label})
    if group_stack:
        raise MermaidImportError("malformed-syntax", "subgraph is missing an end")
    if len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        raise MermaidImportError(
            "resource-limit",
            f"flowchart contains {len(nodes)} nodes/{len(edges)} edges; limits are "
            f"{MAX_NODES}/{MAX_EDGES}",
        )
    if not nodes:
        raise MermaidImportError("malformed-syntax", "flowchart contains no supported nodes")
    has_decision = any(node["kind"] == "decision" for node in nodes.values())
    diagram_type = "flowchart" if has_decision else "architecture"
    composition = "decision-spine" if has_decision else "linear-pipeline"
    title = "Imported decision flow" if has_decision else "Imported system graph"
    semantic = _base_diagram(
        diagram_id=f"imported-{grammar_name.lower()}",
        title=title,
        diagram_type=diagram_type,
        composition=composition,
        direction=direction,
    )
    semantic["nodes"] = list(nodes.values())
    semantic["edges"] = edges
    semantic["groups"] = groups
    fidelity = _fidelity(source, block_index, grammar_name)
    fidelity.update(
        originalCount=len(nodes),
        finalVisibleCount=len(nodes),
        preserved=["nodes", "relationships", "edge direction", "edge labels", "basic subgraphs"],
        normalisedLabels=normalised_labels,
    )
    fidelity["assumptions"].append(
        "Mermaid graph was classified as flowchart because it contains a decision"
        if has_decision
        else "Mermaid graph was classified as architecture because it contains no decision"
    )
    semantic["fidelity"]["source"] = f"{source}, Mermaid block {block_index}"
    semantic["fidelity"]["assumptions"] = list(fidelity["assumptions"])
    return {
        "grammar": grammar_name,
        "diagramType": diagram_type,
        "semantic": semantic,
        "fidelity": fidelity,
    }


MESSAGE = re.compile(r"^([A-Za-z0-9_-]+)\s*(-{1,2}>>|--?>|-)\s*([A-Za-z0-9_-]+)\s*:\s*(.+)$")


def _parse_sequence(block: str, source: str, block_index: int) -> dict[str, Any]:
    participants: dict[str, dict[str, Any]] = {}
    messages: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    fragments: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    normalised: list[dict[str, str]] = []
    for line in _lines(block)[1:]:
        participant = re.match(r"^(participant|actor)\s+([\w-]+)(?:\s+as\s+(.+))?$", line, re.I)
        if participant:
            kind, participant_id, raw_label = participant.groups()
            label, changed = _clean_label(raw_label or participant_id)
            stable = _slug(participant_id, "participant")
            participants[stable] = {
                "id": stable,
                "label": label,
                "kind": "actor" if kind.lower() == "actor" else "service",
            }
            if changed:
                normalised.append({"source": raw_label or participant_id, "resolved": label})
            continue
        fragment = re.match(r"^(loop|opt|alt)\s+(.+)$", line, re.I)
        if fragment:
            kind, guard = fragment.groups()
            stack.append(
                {
                    "id": f"fragment-{len(fragments) + 1}",
                    "kind": {"alt": "alternative", "opt": "optional"}.get(kind.lower(), "loop"),
                    "label": guard.strip(),
                    "guard": guard.strip(),
                    "startOrder": len(messages) + 1,
                }
            )
            continue
        if line.lower().startswith("else"):
            if not stack or stack[-1]["kind"] != "alternative":
                raise MermaidImportError("malformed-syntax", "sequence else appears outside alt")
            continue
        if line.lower() == "end":
            if not stack:
                raise MermaidImportError("malformed-syntax", "sequence end has no fragment")
            item = stack.pop()
            item["endOrder"] = len(messages)
            if item["endOrder"] < item["startOrder"]:
                raise MermaidImportError(
                    "malformed-syntax", "sequence fragment contains no messages"
                )
            fragments.append(item)
            continue
        note = re.match(
            r"^Note\s+(?:left of|right of|over)\s+([\w-]+)(?:,[\w-]+)?\s*:\s*(.+)$", line, re.I
        )
        if note:
            participant_id, label = note.groups()
            notes.append(
                {
                    "id": f"note-{len(notes) + 1}",
                    "participant": _slug(participant_id, "participant"),
                    "label": _clean_label(label)[0],
                    "order": max(1, len(messages)),
                }
            )
            continue
        match = MESSAGE.match(line)
        if not match:
            raise MermaidImportError("malformed-syntax", f"unsupported sequence syntax: {line}")
        from_raw, arrow, to_raw, raw_label = match.groups()
        from_id, to_id = _slug(from_raw, "participant"), _slug(to_raw, "participant")
        if from_id not in participants or to_id not in participants:
            raise MermaidImportError(
                "unknown-reference",
                f"message references undeclared participant: {from_raw} -> {to_raw}",
            )
        label, changed = _clean_label(raw_label)
        kind = "return" if arrow.startswith("--") else "async" if arrow == ")>>" else "sync"
        message = {
            "id": f"message-{len(messages) + 1}",
            "from": from_id,
            "to": to_id,
            "label": label,
            "order": len(messages) + 1,
            "kind": kind,
        }
        messages.append(message)
        if changed:
            normalised.append({"source": raw_label, "resolved": label})
    if stack:
        raise MermaidImportError("malformed-syntax", "sequence fragment is missing end")
    if len(participants) > MAX_PARTICIPANTS or len(messages) > MAX_MESSAGES:
        raise MermaidImportError("resource-limit", "sequence participant or message limit exceeded")
    semantic = _base_diagram(
        diagram_id="imported-sequence",
        title="Imported interaction sequence",
        diagram_type="sequence",
        composition="standard",
        direction="top-to-bottom",
    )
    semantic["nodes"] = list(participants.values())
    semantic["sequence"] = {"messages": messages, "fragments": fragments, "notes": notes}
    fidelity = _fidelity(source, block_index, "sequenceDiagram")
    fidelity.update(
        originalCount=len(messages),
        finalVisibleCount=len(messages),
        preserved=[
            "participants",
            "message order",
            "message direction",
            "message line forms",
            "notes",
            "fragments",
        ],
        normalisedLabels=normalised,
    )
    semantic["fidelity"]["source"] = f"{source}, Mermaid block {block_index}"
    return {
        "grammar": "sequenceDiagram",
        "diagramType": "sequence",
        "semantic": semantic,
        "fidelity": fidelity,
    }


def _parse_duration(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)d", value.strip(), re.I)
    return int(match.group(1)) if match else None


def _parse_gantt(block: str, source: str, block_index: int) -> dict[str, Any]:
    title = "Imported delivery plan"
    date_format = "YYYY-MM-DD"
    section = "delivery"
    tasks: list[dict[str, Any]] = []
    workstreams: list[str] = []
    end_by_id: dict[str, date] = {}
    for line in _lines(block)[1:]:
        if line.lower().startswith("title "):
            title = _clean_label(line[6:])[0]
            continue
        if line.lower().startswith("dateformat "):
            date_format = line.split(None, 1)[1].strip()
            if date_format != "YYYY-MM-DD":
                raise MermaidImportError(
                    "unsupported-construct", "only dateFormat YYYY-MM-DD is supported"
                )
            continue
        if line.lower().startswith("axisformat "):
            continue
        if line.lower().startswith("section "):
            section = _slug(line.split(None, 1)[1], "delivery")
            if section not in workstreams:
                workstreams.append(section)
            continue
        if ":" not in line:
            raise MermaidImportError("malformed-syntax", f"unsupported Gantt syntax: {line}")
        raw_label, raw_spec = line.split(":", 1)
        tokens = [token.strip() for token in raw_spec.split(",") if token.strip()]
        statuses = {"done", "active", "crit", "milestone"}
        status_tokens = [token for token in tokens if token.lower() in statuses]
        values = [token for token in tokens if token.lower() not in statuses]
        task_id = (
            _slug(values.pop(0), f"task-{len(tasks) + 1}")
            if values and not re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+d|after\s+.+", values[0], re.I)
            else f"task-{len(tasks) + 1}"
        )
        dependencies: list[str] = []
        if values and values[0].lower().startswith("after "):
            dependency = _slug(values.pop(0).split(None, 1)[1], "task")
            dependencies.append(dependency)
            if dependency not in end_by_id:
                raise MermaidImportError(
                    "unknown-reference", f"Gantt task references unknown dependency '{dependency}'"
                )
            start = end_by_id[dependency] + timedelta(days=1)
        elif values and re.fullmatch(r"\d{4}-\d{2}-\d{2}", values[0]):
            start = date.fromisoformat(values.pop(0))
        else:
            raise MermaidImportError(
                "malformed-syntax",
                f"Gantt task '{raw_label.strip()}' needs a start date or after dependency",
            )
        end: date
        duration = _parse_duration(values[0]) if values else None
        if duration is not None:
            end = start + timedelta(days=duration - 1)
        elif values and re.fullmatch(r"\d{4}-\d{2}-\d{2}", values[0]):
            end = date.fromisoformat(values[0])
            duration = (end - start).days + 1
        else:
            raise MermaidImportError(
                "malformed-syntax",
                f"Gantt task '{raw_label.strip()}' needs an end date or duration",
            )
        if end < start:
            raise MermaidImportError(
                "malformed-syntax", f"Gantt task '{raw_label.strip()}' ends before it starts"
            )
        milestone = "milestone" in [value.lower() for value in status_tokens]
        if milestone:
            end = start
            duration = 1
        task = {
            "id": task_id,
            "label": _clean_label(raw_label)[0],
            "start": start.isoformat(),
            "end": end.isoformat(),
            "durationDays": duration,
            "dependencies": dependencies,
            "workstream": section,
            "milestone": milestone,
            "status": "success"
            if "done" in status_tokens
            else "warning"
            if "active" in status_tokens
            else "default",
            "critical": "crit" in status_tokens,
        }
        tasks.append(task)
        end_by_id[task_id] = end
    if not tasks:
        raise MermaidImportError("malformed-syntax", "Gantt diagram contains no supported tasks")
    if len(tasks) > MAX_TASKS:
        raise MermaidImportError(
            "resource-limit", f"Gantt contains {len(tasks)} tasks; maximum is {MAX_TASKS}"
        )
    plan_start = min(date.fromisoformat(task["start"]) for task in tasks)
    plan_end = max(date.fromisoformat(task["end"]) for task in tasks)
    semantic = _base_diagram(
        diagram_id="imported-gantt",
        title=title,
        diagram_type="gantt",
        composition="workstreams" if len(workstreams) > 1 else "phased-plan",
        direction="left-to-right",
    )
    semantic["gantt"] = {
        "dateFormat": date_format,
        "planStart": plan_start.isoformat(),
        "planEnd": plan_end.isoformat(),
        "scale": "week",
        "tasks": tasks,
        "workstreams": workstreams,
    }
    fidelity = _fidelity(source, block_index, "gantt")
    fidelity.update(
        originalCount=len(tasks),
        finalVisibleCount=len(tasks),
        preserved=[
            "title",
            "ISO dates",
            "inclusive durations",
            "sections",
            "tasks",
            "milestones",
            "dependencies",
            "status markers",
        ],
    )
    semantic["fidelity"]["source"] = f"{source}, Mermaid block {block_index}"
    return {"grammar": "gantt", "diagramType": "gantt", "semantic": semantic, "fidelity": fidelity}


def parse_mermaid(
    block: str, *, source: str = "direct text", block_index: int = 0
) -> dict[str, Any]:
    if INIT_DIRECTIVE.search(block):
        raise MermaidImportError(
            "unsafe-directive", "Mermaid initialisation/theme directives are not imported"
        )
    match = GRAMMAR.match(block)
    if not match:
        token = block.strip().split(None, 1)[0] if block.strip() else "empty"
        raise MermaidImportError("unsupported-grammar", f"unsupported Mermaid grammar: {token}")
    grammar, remainder = match.groups()
    canonical = "sequenceDiagram" if grammar.lower() == "sequencediagram" else grammar.lower()
    if canonical in {"flowchart", "graph"}:
        return _parse_flowchart(block, source, block_index, canonical, remainder)
    if canonical == "sequenceDiagram":
        return _parse_sequence(block, source, block_index)
    return _parse_gantt(block, source, block_index)


def import_mermaid_text(
    text: str,
    *,
    source: str = "direct text",
    suffix: str = "",
    block: int | None = None,
    all_blocks: bool = False,
) -> dict[str, Any]:
    blocks = extract_blocks(text, suffix)
    if all_blocks:
        selected = list(enumerate(blocks))
    else:
        index = 0 if block is None else block
        if index < 0 or index >= len(blocks):
            raise MermaidImportError(
                "block-index",
                f"Mermaid block index {index} is out of range for {len(blocks)} block(s)",
            )
        selected = [(index, blocks[index])]
    imports = [parse_mermaid(value, source=source, block_index=index) for index, value in selected]
    return {"valid": True, "source": source, "blockCount": len(blocks), "imports": imports}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--text", help="direct Mermaid text")
    parser.add_argument("--block", type=int, help="zero-based Mermaid fence index")
    parser.add_argument("--all", action="store_true", help="import every supported fence")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if (args.source is None) == (args.text is None):
            raise MermaidImportError("input", "provide exactly one source file or --text")
        if args.source:
            if args.source.suffix.lower() not in {".mmd", ".mermaid", ".md", ".markdown"}:
                raise MermaidImportError(
                    "unsupported-source", "source must be .mmd, .mermaid, or Markdown"
                )
            text = args.source.read_text(encoding="utf-8")
            source, suffix = str(args.source), args.source.suffix
        else:
            text, source, suffix = args.text or "", "direct text", ""
        result = import_mermaid_text(
            text, source=source, suffix=suffix, block=args.block, all_blocks=args.all
        )
    except (OSError, UnicodeError, MermaidImportError) as exc:
        code = exc.code if isinstance(exc, MermaidImportError) else "source-read"
        result = {"valid": False, "error": {"code": code, "message": str(exc)}}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
