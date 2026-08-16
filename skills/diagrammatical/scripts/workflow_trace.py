#!/usr/bin/env python3
"""Record privacy-preserving stage outcomes for an installed creation smoke test."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGES = (
    "inspect-model",
    "select-presentation",
    "semantic-source",
    "render",
    "mechanical-validation",
    "visual-review",
    "correction",
    "final-validation",
    "handoff",
)
STATUSES = {"pending", "completed", "not-performed", "not-needed", "failed", "blocked"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_trace(project: Path, slug: str) -> Path:
    return project / ".diagrammatical" / "workflow-runs" / f"{slug}.json"


def start_trace(project: Path, slug: str, diagram_type: str, max_turns: int) -> dict[str, Any]:
    """Create a trace containing bounded metadata, never source text or the user prompt."""

    return {
        "schemaVersion": 1,
        "diagram": slug,
        "diagramType": diagram_type,
        "configuredMaxTurns": max_turns,
        "startedAt": _now(),
        "updatedAt": _now(),
        "stages": {stage: "pending" for stage in STAGES},
    }


def update_trace(trace: dict[str, Any], updates: list[str]) -> dict[str, Any]:
    stages = trace.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("trace is missing stages")
    for update in updates:
        try:
            stage, status = update.split("=", 1)
        except ValueError as exc:
            raise ValueError(f"invalid stage update: {update}") from exc
        if stage not in STAGES:
            raise ValueError(f"unknown workflow stage: {stage}")
        if status not in STATUSES:
            raise ValueError(f"invalid workflow status: {status}")
        stages[stage] = status
    trace["updatedAt"] = _now()
    return trace


def infer_artifact_stages(trace: dict[str, Any], diagram_directory: Path) -> dict[str, Any]:
    """Infer durable milestones without storing or echoing artifact content."""

    stages = trace["stages"]
    slug = trace["diagram"]
    if (diagram_directory / "diagram.yaml").is_file():
        stages["semantic-source"] = "completed"
    if (diagram_directory / f"{slug}.html").is_file() and (
        diagram_directory / f"{slug}.svg"
    ).is_file():
        stages["render"] = "completed"
    validation = diagram_directory / "validation.json"
    if validation.is_file():
        try:
            payload = json.loads(validation.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            stages["mechanical-validation"] = "failed"
        else:
            stages["mechanical-validation"] = (
                "completed" if payload.get("valid") is True else "failed"
            )
            review = payload.get("visualReview")
            if isinstance(review, dict):
                status = review.get("status")
                stages["visual-review"] = (
                    "completed" if status in {"passed", "completed"} else "not-performed"
                )
    trace["updatedAt"] = _now()
    return trace


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("project", type=Path)
    start.add_argument("slug")
    start.add_argument("--type", required=True, dest="diagram_type")
    start.add_argument("--max-turns", required=True, type=int)
    start.add_argument("--output", type=Path)
    update = subparsers.add_parser("update")
    update.add_argument("trace", type=Path)
    update.add_argument("--diagram-directory", type=Path)
    update.add_argument("--stage", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "start":
            if args.max_turns < 1:
                raise ValueError("max turns must be positive")
            output = args.output or _default_trace(args.project, args.slug)
            payload = start_trace(args.project, args.slug, args.diagram_type, args.max_turns)
        else:
            output = args.trace
            payload = json.loads(output.read_text(encoding="utf-8"))
            if args.diagram_directory:
                payload = infer_artifact_stages(payload, args.diagram_directory)
            payload = update_trace(payload, args.stage)
        _write(output, payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    print(json.dumps({"valid": True, "trace": str(output), "stages": payload["stages"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
