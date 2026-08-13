from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from skills.diagrammatical.scripts.self_check import run_self_check
from skills.diagrammatical.scripts.validate import load_structured_file, validate_document

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/diagrammatical/assets/examples/architecture"
EXAMPLE_DIRS = tuple(sorted(path for path in EXAMPLES.iterdir() if path.is_dir()))


@pytest.mark.parametrize("example_dir", EXAMPLE_DIRS, ids=lambda path: path.name)
def test_architecture_semantic_sources_are_valid(example_dir: Path) -> None:
    result = validate_document(load_structured_file(example_dir / "diagram.yaml"), "diagram")
    assert result.valid, result.errors
    assert result.warnings == []


def test_invalid_architecture_composition_fails_schema() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["presentation"]["composition"] = "linear"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("linear" in error and "not one of" in error for error in result.errors)


def test_invalid_architecture_node_kind_fails_schema() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["nodes"][0]["kind"] = "decision"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("decision" in error and "not one of" in error for error in result.errors)


def test_architecture_unknown_edge_endpoint_fails_clearly() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["edges"][0]["to"] = "missing-component"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert (
        "edge 'partners-send-events' has unknown to node 'missing-component'; every edge "
        "endpoint must reference a declared node"
    ) in result.errors


def test_architecture_duplicate_ids_fail_clearly() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["edges"][0]["id"] = document["nodes"][0]["id"]
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("duplicate stable ID 'partner-systems'" in error for error in result.errors)


def test_architecture_complexity_budgets_produce_actionable_warnings() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    for index in range(3):
        document["nodes"].append(
            {"id": f"extra-node-{index}", "label": f"Extra {index}", "kind": "component"}
        )
    for index in range(7):
        document["edges"].append(
            {
                "id": f"extra-edge-{index}",
                "from": "partner-systems",
                "to": f"extra-node-{index % 3}",
                "kind": "dependency",
            }
        )
    for index in range(3):
        document["groups"].append(
            {"id": f"extra-group-{index}", "label": f"Extra {index}", "nodes": []}
        )
    result = validate_document(document, "diagram")
    assert result.valid, result.errors
    assert any(
        "nodes count 10" in warning and "budget of 9" in warning for warning in result.warnings
    )
    assert any(
        "edges count 13" in warning and "budget of 12" in warning for warning in result.warnings
    )
    assert any(
        "groups count 5" in warning and "budget of 4" in warning for warning in result.warnings
    )
    assert all("without silent omission" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "mutation",
    (
        "unknown-node-group",
        "missing-group-list-membership",
        "multiple-direct-groups",
        "unknown-parent",
        "parent-cycle",
    ),
)
def test_architecture_group_membership_is_validated(mutation: str) -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    if mutation == "unknown-node-group":
        document["nodes"][1]["group"] = "missing-group"
    elif mutation == "missing-group-list-membership":
        document["groups"][0]["nodes"].remove("edge-gateway")
    elif mutation == "multiple-direct-groups":
        document["groups"][1]["nodes"].append("edge-gateway")
    elif mutation == "unknown-parent":
        document["groups"][0]["parent"] = "missing-group"
    else:
        document["groups"][0]["parent"] = "insight-plane"
        document["groups"][1]["parent"] = "ingestion-platform"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("group" in error.lower() for error in result.errors)


def test_architecture_maximum_focal_elements_includes_node_emphasis() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["nodes"][1]["emphasis"] = "primary"
    document["nodes"][2]["emphasis"] = "primary"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("at most 2 focal elements" in error for error in result.errors)


def test_architecture_schema_maximum_focal_nodes() -> None:
    document = load_structured_file(EXAMPLES / "event-ingestion-pipeline/diagram.yaml")
    document["presentation"]["focalNodes"] = [
        "edge-gateway",
        "event-intake",
        "durable-stream",
    ]
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("too long" in error for error in result.errors)


def test_examples_are_materially_different_and_exercise_art_directions() -> None:
    documents = [load_structured_file(path / "diagram.yaml") for path in EXAMPLE_DIRS]
    assert {document["presentation"]["composition"] for document in documents} == {
        "linear-pipeline",
        "central-platform",
        "bounded-domains",
    }
    assert {document["presentation"]["style"] for document in documents} == {
        "editorial",
        "technical",
        "clinical",
    }
    assert len({tuple(node["id"] for node in document["nodes"]) for document in documents}) == 3
    assert all(document["groups"] for document in documents)
    assert all(document["presentation"]["focalNodes"] for document in documents)


def test_architecture_reference_integrates_every_art_direction_and_recipe() -> None:
    reference = (ROOT / "skills/diagrammatical/references/types/architecture.md").read_text(
        encoding="utf-8"
    )
    for recipe in (
        "linear-pipeline",
        "layered-stack",
        "central-platform",
        "hub-and-spoke",
        "bounded-domains",
        "current-future",
    ):
        assert f"### `{recipe}`" in reference
    for style in ("Editorial", "Technical", "Executive", "Clinical", "Neutral"):
        assert f"- {style}:" in reference


def test_natural_language_architecture_request_routes_to_complete_workflow() -> None:
    skill = (ROOT / "skills/diagrammatical/SKILL.md").read_text(encoding="utf-8")
    command = (ROOT / "commands/create.md").read_text(encoding="utf-8")
    reference = (ROOT / "skills/diagrammatical/references/types/architecture.md").read_text(
        encoding="utf-8"
    )
    assert "Generate an architecture diagram of this repository" in skill
    assert "references/types/architecture.md" in skill
    assert "references/types/architecture.md" in command
    for behavior in (
        "Read project orientation and dependency manifests",
        "audience, purpose, primary message",
        "create it non-destructively",
        "diagram.yaml",
        "minimal-light.html",
        "extract_svg.py",
        "self_check.py",
        "validation.json",
        "Never generate PNG by default",
        "collapsed, omitted, or assumed concept",
    ):
        assert behavior in reference
    assert "<skill-root>/scripts/validate.py" in reference
    assert "python skills/diagrammatical/scripts" not in reference


@pytest.mark.parametrize("example_dir", EXAMPLE_DIRS, ids=lambda path: path.name)
def test_checked_in_architecture_examples_pass_self_check(example_dir: Path) -> None:
    result = run_self_check(example_dir)
    assert result.valid, result.errors
    assert result.warnings == []
    expected = {
        "diagram.yaml",
        f"{example_dir.name}.html",
        f"{example_dir.name}.svg",
        "validation.json",
    }
    assert {path.name for path in example_dir.iterdir()} == expected


@pytest.mark.parametrize("example_dir", EXAMPLE_DIRS, ids=lambda path: path.name)
def test_validation_reports_match_examples(example_dir: Path) -> None:
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
    assert len(report["visualReview"]["findings"]) >= 2


def test_self_check_cli_passes_representative_example() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/diagrammatical/scripts/self_check.py"),
            str(EXAMPLES / "event-ingestion-pipeline"),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["valid"] is True


def test_architecture_validation_does_not_change_non_architecture_source() -> None:
    original = load_structured_file(ROOT / "tests/fixtures/valid-diagram.yaml")
    document = deepcopy(original)
    result = validate_document(document, "diagram")
    assert result.valid
    assert document == original
