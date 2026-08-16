from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills.diagrammatical.scripts.workflow_trace import (
    infer_artifact_stages,
    start_trace,
    update_trace,
)


def test_trace_records_only_bounded_metadata(tmp_path: Path) -> None:
    trace = start_trace(tmp_path, "service-map", "architecture", 16)

    assert trace["diagram"] == "service-map"
    assert trace["configuredMaxTurns"] == 16
    assert "prompt" not in trace
    assert "source" not in trace
    assert set(trace["stages"]) == {
        "inspect-model",
        "select-presentation",
        "semantic-source",
        "render",
        "mechanical-validation",
        "visual-review",
        "correction",
        "final-validation",
        "handoff",
    }


def test_trace_infers_completed_artifacts_and_truthful_visual_status(tmp_path: Path) -> None:
    trace = start_trace(tmp_path, "service-map", "architecture", 16)
    output = tmp_path / "diagrams/service-map"
    output.mkdir(parents=True)
    (output / "diagram.yaml").write_text("diagram: {}\n", encoding="utf-8")
    (output / "service-map.html").write_text("<svg></svg>\n", encoding="utf-8")
    (output / "service-map.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (output / "validation.json").write_text(
        json.dumps(
            {
                "valid": True,
                "visualReview": {"status": "not-performed", "reason": "No browser."},
            }
        ),
        encoding="utf-8",
    )

    inferred = infer_artifact_stages(trace, output)

    assert inferred["stages"]["semantic-source"] == "completed"
    assert inferred["stages"]["render"] == "completed"
    assert inferred["stages"]["mechanical-validation"] == "completed"
    assert inferred["stages"]["visual-review"] == "not-performed"


def test_trace_rejects_unknown_stage_or_status(tmp_path: Path) -> None:
    trace = start_trace(tmp_path, "service-map", "architecture", 16)
    with pytest.raises(ValueError, match="unknown workflow stage"):
        update_trace(trace, ["invent-layout=completed"])
    with pytest.raises(ValueError, match="invalid workflow status"):
        update_trace(trace, ["handoff=looping"])
