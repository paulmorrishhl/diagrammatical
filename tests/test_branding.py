from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from skills.diagrammatical.scripts.brand_workflow import (
    plugin_tree_digest,
    prepare_brand,
)
from skills.diagrammatical.scripts.config_resolution import (
    resolve_configuration_with_provenance,
)
from skills.diagrammatical.scripts.inspect_brand import (
    InspectionResult,
    TokenReferenceError,
    inspect_brand_pack,
    inspect_manual,
    inspect_repository,
    resolve_token_references,
)
from skills.diagrammatical.scripts.resolve_brand import (
    map_inspection_to_brand,
    resolve_diagram_brand,
    validate_diagram_overrides,
)
from skills.diagrammatical.scripts.self_check import run_calibration_self_check
from skills.diagrammatical.scripts.validate import load_structured_file, validate_document
from skills.diagrammatical.scripts.validate_brand import (
    validate_brand_document,
    validate_svg_asset,
)

ROOT = Path(__file__).resolve().parents[1]
BUILT_IN_BRAND = ROOT / "skills/diagrammatical/assets/brands/editorial-blueprint.yaml"
REQUIRED_CALIBRATION_ROLES = {
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
}


class _RoleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.roles: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        value = dict(attrs).get("data-calibration-role")
        if value:
            self.roles.add(value)


def _manual_inspection(*, dark: bool = False) -> dict:
    result = InspectionResult(root="conversation")
    inspect_manual(
        {
            "colours": {
                "canvas": "#F8FAFC",
                "surface": "#FFFFFF",
                "ink": "#192033",
                "muted-foreground": "#586174",
                "primary": "#6758E8",
                "secondary": "#237F70",
                "success": "#198754",
                "warning": "#9A510E",
                "danger": "#B83A42",
            },
            "fonts": {"heading": "Sora", "body": "Inter", "label": "Inter"},
        },
        result,
    )
    if dark:
        result.colours.extend(
            [
                {
                    "name": "canvas",
                    "value": "#10151E",
                    "source": "conversation",
                    "context": "manual",
                    "variant": "dark",
                },
                {
                    "name": "surface",
                    "value": "#19212D",
                    "source": "conversation",
                    "context": "manual",
                    "variant": "dark",
                },
                {
                    "name": "ink",
                    "value": "#F5F7FA",
                    "source": "conversation",
                    "context": "manual",
                    "variant": "dark",
                },
                {
                    "name": "muted-foreground",
                    "value": "#BEC7D5",
                    "source": "conversation",
                    "context": "manual",
                    "variant": "dark",
                },
                {
                    "name": "primary",
                    "value": "#B2A8FF",
                    "source": "conversation",
                    "context": "manual",
                    "variant": "dark",
                },
            ]
        )
    return result.to_dict()


def _brand(name: str = "CARE", *, dark: bool = False) -> tuple[dict, dict]:
    return map_inspection_to_brand(
        _manual_inspection(dark=dark), name=name, include_dark=dark
    )


def test_manual_values_are_extracted_and_mapped_semantically() -> None:
    brand, receipt = _brand()
    roles = brand["variants"]["light"]["roles"]
    assert brand["id"] == "care"
    assert roles["canvas"] == "#F8FAFC"
    assert roles["emphasisPrimary"] == "#6758E8"
    assert roles["emphasisPrimaryTint"] != "#E7ECFF"
    assert roles["connector"] == roles["inkMuted"]
    assert brand["typography"]["heading"]["family"] == "Sora"
    assert receipt["sources"] == [{"type": "manual", "path": "conversation"}]
    assert receipt["policies"]["maximumPrimaryFocalElements"] == 2
    assert receipt["typography"]["heading"]["weight"] == 600


def test_repository_css_extracts_light_dark_fonts_and_css_first_tailwind(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/theme.css").write_text(
        """
        :root { --background: #FAFAF8; --foreground: #17202A; --primary: #2457D6;
                --success: #19735E; --font-heading: Sora; }
        .dark { --background: #10141B; --foreground: #F5F6F8; --primary: #9CB2FF; }
        @theme { --color-accent: #3567E0; --font-body: Inter; }
        """,
        encoding="utf-8",
    )
    result = inspect_repository(tmp_path)
    assert result.valid
    assert {item["variant"] for item in result.colours} == {"light", "dark"}
    assert any(item["family"] == "Sora" for item in result.fonts)
    assert any(item["name"] == "color-accent" for item in result.colours)


def test_static_tailwind_tokens_are_read_without_executing_config(tmp_path: Path) -> None:
    (tmp_path / "tailwind.config.ts").write_text(
        "export default { theme: { colors: { primary: '#2244AA', danger: '#B83A42' }, "
        "fontFamily: { sans: ['Inter'] } }, value: process.env.SECRET }",
        encoding="utf-8",
    )
    result = inspect_repository(tmp_path)
    assert {item["value"] for item in result.colours} == {"#2244AA", "#B83A42"}
    assert any(item["family"] == "Inter" for item in result.fonts)
    assert any("no code was executed" in warning for warning in result.warnings)


def test_supported_design_tokens_and_nested_references_are_resolved(tmp_path: Path) -> None:
    (tmp_path / "design-tokens.json").write_text(
        json.dumps(
            {
                "colour": {
                    "brand": {"primary": {"$value": "#6758E8"}},
                    "action": {"value": "{colour.brand.primary}"},
                },
                "typography": {"heading": {"value": "Sora"}},
                "radius": {"card": {"value": "8px"}},
            }
        ),
        encoding="utf-8",
    )
    result = inspect_repository(tmp_path)
    assert [item["value"] for item in result.colours].count("#6758E8") == 2
    assert result.fonts[0]["family"] == "Sora"
    assert result.shape[0]["value"] == "8px"


def test_circular_token_reference_fails_clearly() -> None:
    with pytest.raises(TokenReferenceError, match="circular design-token reference"):
        resolve_token_references({"a": "{b}", "b": "{a}"})


def test_generated_directories_are_ignored_and_empty_source_warns(tmp_path: Path) -> None:
    generated = tmp_path / "node_modules/package"
    generated.mkdir(parents=True)
    (generated / "theme.css").write_text(":root { --primary: #FF00FF; }", encoding="utf-8")
    result = inspect_repository(tmp_path)
    assert result.colours == []
    assert result.warnings == ["no useful supported brand tokens were found"]


def test_malformed_css_and_token_files_report_without_crashing(tmp_path: Path) -> None:
    (tmp_path / "theme.css").write_bytes(b"\xff\xfe")
    (tmp_path / "design-tokens.json").write_text("{not json", encoding="utf-8")
    result = inspect_repository(tmp_path)
    assert not result.valid
    assert len(result.errors) == 2


def test_existing_brand_pack_is_validated_before_extraction(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "brand.yaml").write_text(BUILT_IN_BRAND.read_text(encoding="utf-8"), encoding="utf-8")
    result = InspectionResult(root=str(tmp_path))
    inspect_brand_pack(pack, tmp_path, result)
    assert result.valid
    assert result.sources == [{"type": "brand-pack", "path": "pack/brand.yaml"}]
    assert len(result.colours) == 30


def test_mapping_retains_statuses_defaults_missing_statuses_and_ambiguity() -> None:
    inspection = _manual_inspection()
    inspection["colours"].append(
        {
            "name": "primary-alt",
            "value": "#5544CC",
            "source": "other.css",
            "context": "manual",
            "variant": "light",
        }
    )
    brand, receipt = map_inspection_to_brand(inspection, name="CARE")
    roles = brand["variants"]["light"]["roles"]
    assert roles["success"] == "#198754"
    assert any(item["role"] == "emphasisPrimary" for item in receipt["ambiguities"])
    no_status = _manual_inspection()
    no_status["colours"] = [
        item
        for item in no_status["colours"]
        if item["name"] not in {"success", "warning", "danger"}
    ]
    _, fallback_receipt = map_inspection_to_brand(no_status, name="Plain")
    assert any("no semantic status colours" in item for item in fallback_receipt["warnings"])


def test_brand_contrast_pass_fail_small_text_and_accent_foreground() -> None:
    brand, _ = _brand()
    passing = validate_brand_document(brand)
    assert passing.valid
    assert all(check["passes"] for check in passing.contrast)
    assert passing.resolvedBrand["variants"]["light"]["foregrounds"]["emphasisPrimary"]

    failing = yaml.safe_load(yaml.safe_dump(brand))
    failing["variants"]["light"]["roles"]["inkMuted"] = "#C8CAD0"
    failing["accessibility"]["allowDerivedColours"] = False
    result = validate_brand_document(failing)
    assert not result.valid
    assert any("inkMuted" in error and "not permitted" in error for error in result.errors)


def test_accessible_adjustment_requires_policy_and_preserves_original() -> None:
    brand, _ = _brand()
    brand["variants"]["light"]["roles"]["inkMuted"] = "#A0A4AC"
    proposal = validate_brand_document(brand, adjust=False)
    assert proposal.valid
    adjustment = next(item for item in proposal.adjustments if item["role"] == "inkMuted")
    assert adjustment["sourceValue"] == "#A0A4AC"
    assert adjustment["approved"] is False
    approved = validate_brand_document(brand, adjust=True)
    assert approved.resolvedBrand["variants"]["light"]["roles"]["inkMuted"] != "#A0A4AC"


def test_precedence_provenance_and_non_overridable_safety() -> None:
    result = resolve_configuration_with_provenance(
        safety={"accessibility": {"neverUseColourAlone": True}, "safety": {"scripts": False}},
        diagram_type={"connector": {"kind": "orthogonal"}},
        art_direction={"density": "generous"},
        brand={"roles": {"emphasisPrimary": "#111111"}},
        project={"density": "balanced"},
        diagram={"roles": {"emphasisPrimary": "#222222"}, "safety": {"scripts": True}},
        output_preset={"density": "compact"},
    )
    assert result["tokens"]["density"] == "compact"
    assert result["tokens"]["roles"]["emphasisPrimary"] == "#222222"
    assert result["tokens"]["safety"]["scripts"] is False
    assert result["provenance"]["roles.emphasisPrimary"] == "diagram"
    assert result["provenance"]["safety.scripts"] == "non-overridable-safety"
    assert result["tokens"]["connector"]["kind"] == "orthogonal"


def test_one_off_override_validation_does_not_mutate_brand() -> None:
    brand, _ = _brand()
    original = yaml.safe_dump(brand)
    assert validate_diagram_overrides(
        brand, "light", {"emphasisPrimary": "#704FD1", "connectorWidth": 2}
    ) == []
    assert yaml.safe_dump(brand) == original
    assert validate_diagram_overrides(brand, "light", {"emphasisPrimary": "violet"})
    assert validate_diagram_overrides(brand, "light", {"neverUseColourAlone": False})
    resolved = resolve_diagram_brand(
        brand, "light", {"emphasisPrimary": "#704FD1", "connectorWidth": 2}
    )
    assert resolved["appliedOverrides"] == {
        "emphasisPrimary": "#704FD1",
        "connectorWidth": 2,
    }
    assert resolved["provenance"]["emphasisPrimary"] == "diagram-override"


def test_safe_logo_accepted_and_unsafe_assets_rejected(tmp_path: Path) -> None:
    safe = tmp_path / "logo.svg"
    safe.write_text('<svg viewBox="0 0 20 20"><path d="M0 0H20V20Z"/></svg>', encoding="utf-8")
    assert validate_svg_asset(safe) == []
    scripted = tmp_path / "scripted.svg"
    scripted.write_text('<svg viewBox="0 0 20 20"><script>bad()</script></svg>', encoding="utf-8")
    assert any("script" in error for error in validate_svg_asset(scripted))
    event = tmp_path / "event.svg"
    event.write_text('<svg viewBox="0 0 20 20" onload="bad()"/>', encoding="utf-8")
    assert any("event" in error for error in validate_svg_asset(event))
    remote = tmp_path / "remote.svg"
    remote.write_text(
        '<svg viewBox="0 0 20 20"><use href="https://x/logo.svg"/></svg>',
        encoding="utf-8",
    )
    assert any("external" in error for error in validate_svg_asset(remote))


def test_approved_safe_logo_is_copied_but_unapproved_logo_is_not(tmp_path: Path) -> None:
    logo = tmp_path / "source-logo.svg"
    logo.write_text(
        '<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="8"/></svg>',
        encoding="utf-8",
    )
    brand, receipt = _brand()
    brand["logo"]["source"] = "./logo.svg"
    brand["logo"]["placements"] = ["footer-right"]
    proposal = prepare_brand(
        tmp_path / "proposal", brand, receipt, approved=False, logo_source=logo
    )
    assert not (tmp_path / "proposal/.diagrammatical").exists()
    assert "logo.svg" in proposal["files"]
    approved = prepare_brand(
        tmp_path / "approved", brand, receipt, approved=True, logo_source=logo
    )
    copied = Path(approved["directory"]) / "logo.svg"
    assert copied.read_text(encoding="utf-8") == logo.read_text(encoding="utf-8")


def test_project_owned_icon_directory_uses_svg_asset_safety(tmp_path: Path) -> None:
    brand, _ = _brand()
    brand["icons"]["customDirectory"] = "./icons"
    icons = tmp_path / "icons"
    icons.mkdir()
    (icons / "safe.svg").write_text(
        '<svg viewBox="0 0 8 8"><path d="M0 0H8"/></svg>', encoding="utf-8"
    )
    assert validate_brand_document(brand, brand_directory=tmp_path).valid
    (icons / "unsafe.svg").write_text(
        '<svg viewBox="0 0 8 8"><script>bad()</script></svg>', encoding="utf-8"
    )
    result = validate_brand_document(brand, brand_directory=tmp_path)
    assert any("icon unsafe.svg" in error and "script" in error for error in result.errors)


def test_font_fallback_disclosure_is_reported() -> None:
    brand, _ = _brand()
    result = validate_brand_document(brand, available_fonts={"Arial"})
    assert any(
        "Sora" in disclosure and "fallback" in disclosure
        for disclosure in result.fontDisclosures
    )


def test_proposal_does_not_write_project_and_approval_persists_only_under_dot_directory(
    tmp_path: Path,
) -> None:
    brand, receipt = _brand()
    before = plugin_tree_digest()
    proposal = prepare_brand(tmp_path, brand, receipt, approved=False)
    assert proposal["valid"] and not proposal["saved"]
    assert not (tmp_path / ".diagrammatical").exists()
    approved = prepare_brand(tmp_path, brand, receipt, approved=True, set_default=True)
    target = tmp_path / ".diagrammatical/brands/care"
    assert approved["valid"] and target.is_dir()
    assert set(approved["files"]) == {
        "brand.yaml",
        "calibration.html",
        "calibration.svg",
        "fidelity.json",
    }
    config = load_structured_file(tmp_path / ".diagrammatical/config.yaml")
    assert config["defaults"]["brand"] == "care"
    assert plugin_tree_digest() == before
    assert not list(tmp_path.rglob("*.png"))


def test_default_requires_approval_and_unrelated_brand_and_config_survive(tmp_path: Path) -> None:
    user_root = tmp_path / ".diagrammatical"
    (user_root / "brands/existing").mkdir(parents=True)
    (user_root / "brands/existing/note.txt").write_text("keep", encoding="utf-8")
    (user_root / "config.yaml").write_text(
        "schemaVersion: 1\ndefaults:\n  brand: existing\noutput:\n  directory: pictures\n",
        encoding="utf-8",
    )
    brand, receipt = _brand("Second")
    prepare_brand(tmp_path, brand, receipt, approved=True, set_default=False)
    config = load_structured_file(user_root / "config.yaml")
    assert config["defaults"]["brand"] == "existing"
    assert config["output"]["directory"] == "pictures"
    assert (user_root / "brands/existing/note.txt").read_text(encoding="utf-8") == "keep"


def test_existing_brand_requires_replacement_approval_and_reports_differences(
    tmp_path: Path,
) -> None:
    brand, receipt = _brand()
    assert prepare_brand(tmp_path, brand, receipt, approved=True)["valid"]
    changed = yaml.safe_load(yaml.safe_dump(brand))
    changed["variants"]["light"]["roles"]["emphasisPrimary"] = "#704FD1"
    refused = prepare_brand(tmp_path, changed, receipt, approved=True)
    assert not refused["valid"]
    assert any(
        item["path"] == "$.variants.light.roles.emphasisPrimary"
        for item in refused["differences"]
    )


@pytest.mark.parametrize("dark", [False, True])
def test_calibration_represents_required_roles_validates_and_contains_no_png(
    tmp_path: Path, dark: bool
) -> None:
    brand, receipt = _brand("Night CARE" if dark else "Day CARE", dark=dark)
    outcome = prepare_brand(tmp_path, brand, receipt, approved=True)
    directory = Path(outcome["directory"])
    parser = _RoleParser()
    parser.feed((directory / "calibration.html").read_text(encoding="utf-8"))
    assert REQUIRED_CALIBRATION_ROLES <= parser.roles
    assert ("dark-preview" in parser.roles) is dark
    check = run_calibration_self_check(directory)
    assert check.valid, check.errors
    assert not list(directory.glob("*.png"))


def test_two_brands_keep_calibration_structure_but_render_different_tokens(tmp_path: Path) -> None:
    care, care_receipt = _brand("CARE")
    other_inspection = _manual_inspection()
    for colour in other_inspection["colours"]:
        if colour["name"] == "primary":
            colour["value"] = "#A3315D"
    other, other_receipt = map_inspection_to_brand(other_inspection, name="Orchard")
    care_outcome = prepare_brand(tmp_path / "one", care, care_receipt, approved=True)
    care_path = Path(care_outcome["directory"])
    other_path = Path(
        prepare_brand(tmp_path / "two", other, other_receipt, approved=True)["directory"]
    )
    care_html = (care_path / "calibration.html").read_text(encoding="utf-8")
    other_html = (other_path / "calibration.html").read_text(encoding="utf-8")
    assert "#6758E8" in care_html and "#A3315D" in other_html
    for role in REQUIRED_CALIBRATION_ROLES:
        assert f'data-calibration-role="{role}"' in care_html
        assert f'data-calibration-role="{role}"' in other_html


@pytest.mark.parametrize(
    "art_direction", ["editorial", "technical", "executive", "clinical", "neutral"]
)
def test_custom_brand_remains_independent_of_every_art_direction(art_direction: str) -> None:
    brand, _ = _brand()
    roles = brand["variants"]["light"]["roles"]
    result = resolve_configuration_with_provenance(
        safety={"accessibility": {"statusRequiresNonColourCue": True}},
        diagram_type={"structure": {"grammar": "architecture"}},
        art_direction={"style": art_direction, "density": "generous"},
        brand={"roles": roles, "typography": brand["typography"]},
    )
    assert result["tokens"]["style"] == art_direction
    assert result["tokens"]["roles"]["emphasisPrimary"] == "#6758E8"
    assert result["tokens"]["structure"]["grammar"] == "architecture"


@pytest.mark.parametrize(
    ("diagram_type", "slug", "grammar_marker"),
    (
        ("architecture", "event-ingestion-pipeline", "data-calibration"),
        ("flowchart", "partner-onboarding", "data-path"),
        ("sequence", "catalogue-request", "Messages read from top to bottom"),
    ),
)
def test_custom_brand_selection_preserves_existing_diagram_grammar(
    diagram_type: str, slug: str, grammar_marker: str
) -> None:
    directory = ROOT / "skills/diagrammatical/assets/examples" / diagram_type / slug
    source = load_structured_file(directory / "diagram.yaml")
    source["presentation"]["brand"] = "care"
    assert validate_document(source, "diagram").valid
    html = (directory / f"{slug}.html").read_text(encoding="utf-8")
    assert "--emphasis-primary:" in html
    if diagram_type != "architecture":
        assert grammar_marker in html


def test_brand_schema_accepts_dark_generated_metadata_and_rejects_bad_override() -> None:
    brand, _ = _brand(dark=True)
    assert validate_document(brand, "brand").valid
    diagram = load_structured_file(ROOT / "tests/fixtures/valid-diagram.yaml")
    diagram["presentation"]["overrides"] = {"scripts": True}
    result = validate_document(diagram, "diagram")
    assert not result.valid
    assert any("Additional properties" in error and "scripts" in error for error in result.errors)
