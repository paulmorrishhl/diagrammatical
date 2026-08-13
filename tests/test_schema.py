from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from skills.diagrammatical.scripts.validate import (
    SCHEMA_FILES,
    load_schema,
    load_structured_file,
    resolve_configuration,
    validate_document,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
BRAND_PATH = (
    ROOT / "skills/diagrammatical/assets/brands/editorial-blueprint.yaml"
)


@pytest.mark.parametrize("kind", tuple(SCHEMA_FILES))
def test_json_schemas_are_valid_draft_2020_12(kind: str) -> None:
    Draft202012Validator.check_schema(load_schema(kind))


def test_example_diagram_configuration_and_brand_validate() -> None:
    documents = (
        ("diagram", FIXTURES / "valid-diagram.yaml"),
        ("config", FIXTURES / "valid-config.yaml"),
        ("brand", BRAND_PATH),
    )
    for kind, path in documents:
        result = validate_document(load_structured_file(path), kind, source=str(path))
        assert result.valid, result.errors


@pytest.mark.parametrize(
    ("document", "expected_error"),
    (
        ({}, "schemaVersion"),
        ({"schemaVersion": 2}, "1 was expected"),
        ({"schemaVersion": 1, "defaults": {"style": "neon"}}, "not one of"),
        ({"schemaVersion": 1, "output": {"directory": "../outside"}}, "does not match"),
        ({"schemaVersion": 1, "output": {"png": "yes"}}, "not of type 'boolean'"),
    ),
)
def test_invalid_project_configuration_fails(document: dict, expected_error: str) -> None:
    result = validate_document(document, "config")
    assert not result.valid
    assert expected_error in " ".join(result.errors)


def test_unknown_project_configuration_keys_warn_usefully() -> None:
    document = {
        "schemaVersion": 1,
        "defaults": {"style": "editorial", "mysteryMode": True},
        "surprise": "value",
    }
    result = validate_document(document, "config")
    assert result.valid
    assert result.warnings == [
        "unknown configuration key 'defaults.mysteryMode'; it will be ignored",
        "unknown configuration key 'surprise'; it will be ignored",
    ]


def test_invalid_edge_reference_names_edge_endpoint_and_missing_node() -> None:
    document = load_structured_file(FIXTURES / "invalid-edge-diagram.yaml")
    result = validate_document(document, "diagram")
    assert not result.valid
    assert result.errors == [
        "edge 'broken-edge' has unknown to node 'missing-node'; every edge endpoint must "
        "reference a declared node"
    ]


def test_invalid_edge_reference_cli_fails_with_structured_diagnostic() -> None:
    command = [
        sys.executable,
        str(ROOT / "skills/diagrammatical/scripts/validate.py"),
        str(FIXTURES / "invalid-edge-diagram.yaml"),
        "--schema",
        "diagram",
        "--json",
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 1
    assert '"valid": false' in completed.stdout
    assert "edge 'broken-edge' has unknown to node 'missing-node'" in completed.stdout


def test_duplicate_stable_ids_fail_clearly() -> None:
    document = load_structured_file(FIXTURES / "valid-diagram.yaml")
    document["edges"][0]["id"] = "patient"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert "duplicate stable ID 'patient' used by node and edge" in result.errors


def test_configuration_precedence_and_immutable_safety() -> None:
    resolved = resolve_configuration(
        safety={"accessibility": {"statusRequiresNonColourCue": True}, "scripts": False},
        diagram_type={"density": "balanced", "connector": {"kind": "orthogonal"}},
        art_direction={"density": "generous"},
        brand={"connector": {"weight": 2}, "accent": "blue"},
        project={"accent": "green"},
        diagram={"density": "compact", "scripts": True},
        output_preset={"connector": {"weight": 3}},
    )
    assert resolved["density"] == "compact"
    assert resolved["accent"] == "green"
    assert resolved["connector"] == {"kind": "orthogonal", "weight": 3}
    assert resolved["scripts"] is False
    assert resolved["accessibility"]["statusRequiresNonColourCue"] is True


def test_safe_yaml_loader_does_not_construct_python_objects(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.yaml"
    source.write_text("!!python/object/apply:os.system ['echo unsafe']", encoding="utf-8")
    with pytest.raises(ValueError, match="could not safely parse"):
        load_structured_file(source)


def test_sequence_and_gantt_type_data_are_conditionally_required() -> None:
    document = yaml.safe_load((FIXTURES / "valid-diagram.yaml").read_text())
    document["diagram"]["type"] = "sequence"
    result = validate_document(document, "diagram")
    assert not result.valid
    assert any("sequence" in error and "required property" in error for error in result.errors)
