from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import yaml

from skills.diagrammatical.scripts.contrast import validate_brand_contrast
from skills.diagrammatical.scripts.validate import load_structured_file, validate_document

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills/diagrammatical/assets"
BRAND_PATH = ASSETS / "brands/editorial-blueprint.yaml"


class CalibrationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.calibration_roles: set[str] = set()
        self.semantic_roles: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("data-calibration-role"):
            self.calibration_roles.add(attributes["data-calibration-role"] or "")
        if attributes.get("data-semantic-role"):
            self.semantic_roles.add(attributes["data-semantic-role"] or "")


def test_default_identity_passes_all_declared_contrast_checks() -> None:
    brand = load_structured_file(BRAND_PATH)
    checks = validate_brand_contrast(brand)
    failures = [
        f"{check.variant}:{check.foreground_role}/{check.background_role} "
        f"{check.ratio:.2f} < {check.minimum:.2f}"
        for check in checks
        if not check.passes
    ]
    assert checks
    assert failures == []


def test_every_art_direction_is_independent_and_uses_no_raw_colours() -> None:
    expected = {"editorial", "technical", "executive", "clinical", "neutral"}
    found: set[str] = set()
    for path in sorted((ASSETS / "styles").glob("*.yaml")):
        style = yaml.safe_load(path.read_text(encoding="utf-8"))
        found.add(style["id"])
        assert style["name"]
        assert style["description"]
        assert "#" not in path.read_text(encoding="utf-8")
    assert found == expected


def test_calibration_sheet_contains_every_required_visual_role() -> None:
    required = {
        "page-title",
        "subtitle",
        "annotation",
        "standard-node",
        "focal-node",
        "actor-input",
        "process-service",
        "data-store-state",
        "external-service",
        "optional-async-node",
        "group-boundary",
        "default-connector",
        "primary-connector",
        "external-connector",
        "dashed-connector",
        "success-state",
        "warning-state",
        "danger-state",
        "deprecated-state",
        "architecture-composition",
        "flowchart-composition",
        "dark-preview",
    }
    parser = CalibrationParser()
    parser.feed(
        (ASSETS / "templates/calibration-sheet.html").read_text(encoding="utf-8")
    )
    assert parser.calibration_roles == required


def test_calibration_sheet_exercises_all_light_semantic_roles() -> None:
    brand = load_structured_file(BRAND_PATH)
    parser = CalibrationParser()
    parser.feed(
        (ASSETS / "templates/calibration-sheet.html").read_text(encoding="utf-8")
    )
    assert set(brand["variants"]["light"]["roles"]) <= parser.semantic_roles


def test_base_templates_are_static_accessible_inline_svg() -> None:
    for name in ("minimal-light.html", "minimal-dark.html"):
        content = (ASSETS / "templates" / name).read_text(encoding="utf-8")
        lowered = content.lower()
        assert "<svg" in lowered
        assert 'role="img"' in lowered
        assert "aria-labelledby=" in lowered
        assert "<title" in lowered and "<desc" in lowered
        assert "<script" not in lowered
        assert "<iframe" not in lowered
        assert " onload=" not in lowered and " onclick=" not in lowered
        assert "--canvas:" in lowered and "--emphasis-primary:" in lowered


def test_brand_file_is_built_in_not_project_owned_configuration() -> None:
    brand = load_structured_file(BRAND_PATH)
    assert validate_document(brand, "brand").valid
    assert brand["name"] == "Editorial Blueprint"
    assert not any(path.name == ".diagrammatical" for path in ROOT.rglob(".diagrammatical"))
