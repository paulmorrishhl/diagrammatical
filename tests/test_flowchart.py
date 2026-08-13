from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from skills.diagrammatical.scripts.extract_svg import extract_svg_text
from skills.diagrammatical.scripts.self_check import run_self_check
from skills.diagrammatical.scripts.validate import load_structured_file, validate_document
from skills.diagrammatical.scripts.validate_svg import validate_html, validate_svg

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/diagrammatical/assets/examples/flowchart"
EXAMPLE_DIRS = tuple(sorted(path for path in EXAMPLES.iterdir() if path.is_dir()))


def flowchart_source(composition: str = "linear") -> dict:
    return {
        "schemaVersion": 1,
        "diagram": {
            "id": "sample-flow",
            "title": "Sample flow",
            "type": "flowchart",
            "audience": "mixed",
            "purpose": "Explain a representative process",
            "primaryMessage": "One action reaches a clear outcome",
        },
        "nodes": [
            {"id": "start", "label": "Start", "kind": "start"},
            {"id": "act", "label": "Do work", "kind": "process"},
            {"id": "done", "label": "Complete", "kind": "end"},
        ],
        "edges": [
            {"id": "start-act", "from": "start", "to": "act", "kind": "action", "path": "normal"},
            {"id": "act-done", "from": "act", "to": "done", "kind": "action", "path": "normal"},
        ],
        "groups": [],
        "presentation": {
            "composition": composition,
            "brand": "editorial-blueprint",
            "style": "neutral",
            "mode": "light",
            "detail": "balanced",
            "outputPreset": "document-wide",
            "focalNodes": [],
        },
        "fidelity": {"source": "Test fixture", "collapsed": [], "omitted": [], "assumptions": []},
    }


def branching_source(composition: str = "branching") -> dict:
    source = flowchart_source(composition)
    source["nodes"] = [
        {"id": "start", "label": "Start", "kind": "start"},
        {"id": "eligible", "label": "Eligible?", "kind": "decision"},
        {"id": "accepted", "label": "Accepted", "kind": "outcome"},
        {"id": "declined", "label": "Declined", "kind": "outcome"},
    ]
    source["edges"] = [
        {
            "id": "start-eligible",
            "from": "start",
            "to": "eligible",
            "kind": "action",
            "path": "normal",
        },
        {
            "id": "eligible-yes",
            "from": "eligible",
            "to": "accepted",
            "label": "Eligible",
            "kind": "action",
            "path": "conditional",
        },
        {
            "id": "eligible-no",
            "from": "eligible",
            "to": "declined",
            "label": "Not eligible",
            "kind": "action",
            "path": "failure",
            "status": "danger",
        },
    ]
    return source


def assert_valid(source: dict) -> None:
    result = validate_document(source, "diagram")
    assert result.valid, result.errors
    assert result.warnings == []


def test_valid_linear_flowchart() -> None:
    assert_valid(flowchart_source())


def test_valid_branching_flowchart() -> None:
    assert_valid(branching_source())


def test_valid_exception_path_flowchart() -> None:
    source = branching_source("exception-path")
    source["edges"][2]["path"] = "exception"
    source["edges"][2]["label"] = "Service unavailable"
    assert_valid(source)


def test_valid_paired_comparison_flowchart() -> None:
    source = load_structured_file(EXAMPLES / "policy-transition-comparison/diagram.yaml")
    assert_valid(source)


def test_missing_start_node_is_an_error() -> None:
    source = flowchart_source()
    source["nodes"][0]["kind"] = "process"
    result = validate_document(source, "diagram")
    assert not result.valid
    assert "flowchart needs at least one node with kind 'start'" in result.errors


def test_missing_reachable_outcome_is_an_error() -> None:
    source = flowchart_source()
    source["edges"][1]["from"] = "done"
    source["edges"][1]["to"] = "act"
    result = validate_document(source, "diagram")
    assert not result.valid
    assert "flowchart start 'start' has no reachable end or outcome node" in result.errors


def test_decision_with_one_outgoing_edge_is_an_error() -> None:
    source = branching_source()
    source["edges"].pop()
    result = validate_document(source, "diagram")
    assert not result.valid
    assert any("needs at least 2 outgoing paths" in error for error in result.errors)


def test_unlabelled_decision_branch_is_an_error() -> None:
    source = branching_source()
    del source["edges"][1]["label"]
    result = validate_document(source, "diagram")
    assert not result.valid
    assert any("unlabelled outgoing edge 'eligible-yes'" in error for error in result.errors)


def test_unknown_edge_endpoint_fails_clearly() -> None:
    source = flowchart_source()
    source["edges"][0]["to"] = "missing-step"
    result = validate_document(source, "diagram")
    assert not result.valid
    assert any("unknown to node 'missing-step'" in error for error in result.errors)


def test_duplicate_node_or_edge_id_fails_clearly() -> None:
    source = flowchart_source()
    source["edges"][0]["id"] = "start"
    result = validate_document(source, "diagram")
    assert not result.valid
    assert "duplicate stable ID 'start' used by node and edge" in result.errors


def test_unreachable_and_rootless_steps_warn() -> None:
    source = flowchart_source()
    source["nodes"].append({"id": "orphan", "label": "Orphan", "kind": "process"})
    result = validate_document(source, "diagram")
    assert result.valid, result.errors
    assert any("unreachable" in warning and "orphan" in warning for warning in result.warnings)
    assert any("no incoming path" in warning and "orphan" in warning for warning in result.warnings)


@pytest.mark.parametrize("with_exit", (False, True))
def test_loop_with_and_without_exit(with_exit: bool) -> None:
    source = branching_source("exception-path")
    source["nodes"].extend(
        [
            {"id": "retry-one", "label": "Retry one", "kind": "process"},
            {"id": "retry-two", "label": "Retry two", "kind": "process"},
        ]
    )
    source["edges"][2]["to"] = "retry-one"
    source["edges"].extend(
        [
            {
                "id": "retry-next",
                "from": "retry-one",
                "to": "retry-two",
                "kind": "action",
                "path": "retry",
            },
            {
                "id": "retry-again",
                "from": "retry-two",
                "to": "retry-one",
                "kind": "action",
                "path": "retry",
            },
        ]
    )
    if with_exit:
        source["edges"].append(
            {
                "id": "retry-exit",
                "from": "retry-two",
                "to": "declined",
                "kind": "action",
                "path": "failure",
                "label": "Retries exhausted",
            }
        )
    result = validate_document(source, "diagram")
    assert result.valid, result.errors
    has_cycle_warning = any(
        "cycle with no represented exit" in warning for warning in result.warnings
    )
    assert has_cycle_warning is (not with_exit)


def test_flowchart_complexity_budgets_produce_actionable_warnings() -> None:
    source = branching_source()
    for index in range(8):
        source["nodes"].append(
            {"id": f"extra-{index}", "label": f"Extra {index}", "kind": "process"}
        )
    for index in range(12):
        source["edges"].append(
            {
                "id": f"extra-edge-{index}",
                "from": "accepted",
                "to": f"extra-{index % 8}",
                "kind": "action",
                "path": "normal",
            }
        )
    for index in range(4):
        source["nodes"].append(
            {"id": f"decision-{index}", "label": f"Decision {index}?", "kind": "decision"}
        )
        source["edges"].extend(
            [
                {
                    "id": f"decision-{index}-yes",
                    "from": f"decision-{index}",
                    "to": "accepted",
                    "label": "Yes",
                    "kind": "action",
                    "path": "conditional",
                },
                {
                    "id": f"decision-{index}-no",
                    "from": f"decision-{index}",
                    "to": "declined",
                    "label": "No",
                    "kind": "action",
                    "path": "conditional",
                },
            ]
        )
    result = validate_document(source, "diagram")
    assert result.valid, result.errors
    joined = " ".join(result.warnings)
    assert "nodes count" in joined and "budget of 10" in joined
    assert "edges count" in joined and "budget of 14" in joined
    assert "decision count 5" in joined and "budget of 4" in joined
    assert "rather than shrinking labels or nodes" in joined


def test_excess_focal_elements_are_an_error() -> None:
    source = flowchart_source()
    for node in source["nodes"]:
        node["emphasis"] = "primary"
    result = validate_document(source, "diagram")
    assert not result.valid
    assert any("at most 2 focal elements" in error for error in result.errors)


@pytest.mark.parametrize("example_dir", EXAMPLE_DIRS, ids=lambda path: path.name)
def test_checked_in_flowcharts_pass_every_mechanical_check(example_dir: Path) -> None:
    result = run_self_check(example_dir)
    assert result.valid, result.errors
    assert result.warnings == []
    assert validate_html(example_dir / f"{example_dir.name}.html").valid
    assert validate_svg(example_dir / f"{example_dir.name}.svg", slug=example_dir.name).valid
    html = (example_dir / f"{example_dir.name}.html").read_text(encoding="utf-8")
    svg = (example_dir / f"{example_dir.name}.svg").read_text(encoding="utf-8")
    assert extract_svg_text(html).strip() == svg.strip()


@pytest.mark.parametrize("example_dir", EXAMPLE_DIRS, ids=lambda path: path.name)
def test_saved_reports_match_flowchart_examples(example_dir: Path) -> None:
    report = json.loads((example_dir / "validation.json").read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["warnings"] == []
    assert {check["name"] for check in report["checks"]} == {
        "schema",
        "brand",
        "htmlSafety",
        "svg",
        "extraction",
    }
    assert report["visualReview"]["status"] == "completed"
    assert len(report["visualReview"]["findings"]) >= 3


def test_examples_are_structurally_different_and_use_semantic_tokens() -> None:
    documents = [load_structured_file(path / "diagram.yaml") for path in EXAMPLE_DIRS]
    assert {item["presentation"]["composition"] for item in documents} == {
        "decision-spine",
        "exception-path",
        "paired-comparison",
    }
    assert {item["presentation"]["style"] for item in documents} == {
        "editorial",
        "technical",
        "executive",
    }
    for path in EXAMPLE_DIRS:
        svg = (path / f"{path.name}.svg").read_text(encoding="utf-8")
        for role in (
            "--canvas",
            "--surface",
            "--ink",
            "--connector",
            "--emphasis-primary",
            "--danger",
        ):
            assert role in svg
        assert "<desc" in svg and 'data-emphasis="primary"' in svg


def test_flowchart_reference_contains_every_recipe_and_workflow_contract() -> None:
    reference = (ROOT / "skills/diagrammatical/references/types/flowchart.md").read_text(
        encoding="utf-8"
    )
    for recipe in ("linear", "decision-spine", "branching", "exception-path", "paired-comparison"):
        assert f"### `{recipe}`" in reference
    for phrase in (
        "When to use",
        "When not to use",
        "Suitable process shapes",
        "Reading direction",
        "Decision placement",
        "Branch and merge behaviour",
        "Exception-path treatment",
        "Connector routing",
        "Appropriate audiences",
        "Complexity constraints",
        "Common failure modes",
        "Create a flowchart for this process",
        "diagram.yaml",
        "extract_svg.py",
        "validation.json",
        "Never generate PNG by default",
        "visual inspection",
        "fidelity ledger",
    ):
        assert phrase in reference


def test_existing_architecture_examples_remain_valid() -> None:
    architecture = ROOT / "skills/diagrammatical/assets/examples/architecture"
    for example_dir in sorted(path for path in architecture.iterdir() if path.is_dir()):
        result = run_self_check(example_dir)
        assert result.valid, result.errors
        assert result.warnings == []


def test_flowchart_validation_does_not_mutate_source() -> None:
    source = flowchart_source()
    original = deepcopy(source)
    validate_document(source, "diagram")
    assert source == original
