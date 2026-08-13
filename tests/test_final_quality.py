from __future__ import annotations

import json
from pathlib import Path

from skills.diagrammatical.scripts.self_check import run_self_check
from skills.diagrammatical.scripts.validate import load_structured_file
from skills.diagrammatical.scripts.validate_brand import validate_brand_document
from skills.diagrammatical.scripts.validate_svg import validate_html, validate_svg

ROOT = Path(__file__).resolve().parents[1]
IMPORTED = ROOT / "skills/diagrammatical/assets/examples/imported-mermaid"
CALIBRATIONS = ROOT / "tests/visual/fixtures"


def test_canonical_self_check_result_model_and_review_truthfulness(tmp_path: Path) -> None:
    source = ROOT / "skills/diagrammatical/assets/examples/architecture/event-ingestion-pipeline"
    result = run_self_check(source)
    payload = result.to_dict()
    assert result.valid
    assert set(payload) >= {
        "valid",
        "visualReview",
        "checks",
        "warnings",
        "errors",
        "outputs",
        "fidelity",
    }
    assert isinstance(payload["checks"], list)
    assert payload["visualReview"]["status"] == "completed"

    empty = run_self_check(tmp_path)
    assert empty.to_dict()["visualReview"]["status"] == "not-performed"


def test_checked_in_mermaid_redraws_pass_and_have_complete_ledgers() -> None:
    required = {
        "source",
        "selectedBlock",
        "detectedGrammar",
        "originalCount",
        "finalVisibleCount",
        "preserved",
        "normalisedLabels",
        "merged",
        "collapsed",
        "omitted",
        "unsupported",
        "assumptions",
        "requestedTypeChange",
    }
    assert len(list(IMPORTED.iterdir())) == 4
    for directory in IMPORTED.iterdir():
        assert run_self_check(directory).valid, directory
        report = json.loads((directory / "validation.json").read_text(encoding="utf-8"))
        ledger = report["fidelity"]["import"]
        assert required <= ledger.keys()
        semantic = load_structured_file(directory / "diagram.yaml")
        if semantic["diagram"]["type"] == "sequence":
            assert ledger["finalVisibleCount"] == {
                "participants": len(semantic["nodes"]),
                "messages": len(semantic["sequence"]["messages"]),
            }
        elif semantic["diagram"]["type"] == "gantt":
            assert ledger["finalVisibleCount"] == {
                "tasks": len(semantic["gantt"]["tasks"])
            }
        else:
            assert ledger["finalVisibleCount"] == {
                "nodes": len(semantic["nodes"]),
                "edges": len(semantic["edges"]),
            }


def test_custom_calibration_fixtures_validate_without_png() -> None:
    for directory in (
        CALIBRATIONS / "care-purple",
        CALIBRATIONS / "care-purple-dark",
        CALIBRATIONS / "harbour-green",
    ):
        assert validate_brand_document(
            load_structured_file(directory / "brand.yaml"), brand_directory=directory
        ).valid
        assert validate_html(directory / "calibration.html").valid
        assert validate_svg(directory / "calibration.svg", slug=directory.name).valid
        assert not list(directory.glob("*.png"))


def test_explicit_png_can_be_checked_but_is_never_required(tmp_path: Path) -> None:
    result = run_self_check(tmp_path, require_validation=False, png_requested=True)
    assert not result.valid
    assert "missing diagram.yaml" in result.errors
