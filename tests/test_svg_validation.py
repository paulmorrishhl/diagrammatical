from __future__ import annotations

from pathlib import Path

import pytest

from skills.diagrammatical.scripts.extract_svg import extract_svg_text
from skills.diagrammatical.scripts.validate_svg import (
    validate_html_text,
    validate_svg_text,
)

ACCESSIBLE_SVG = """<svg id="sample-diagram" xmlns="http://www.w3.org/2000/svg"
viewBox="0 0 400 240" role="img" aria-labelledby="sample-title sample-desc">
<title id="sample-title">Sample architecture</title>
<desc id="sample-desc">A client sends a request to one application service.</desc>
<defs><style>.label { font-size: 14px; }</style></defs>
<rect x="20" y="20" width="100" height="60"/><text x="30" y="50" class="label">Client</text>
</svg>"""


def test_accessible_svg_metadata_passes() -> None:
    result = validate_svg_text(ACCESSIBLE_SVG, slug="sample")
    assert result.valid, result.errors
    assert result.warnings == []


@pytest.mark.parametrize(
    ("svg", "message"),
    (
        (ACCESSIBLE_SVG.replace(' role="img"', ""), 'role="img"'),
        (ACCESSIBLE_SVG.replace("<title", "<metadata/><title", 1), "first child"),
        (ACCESSIBLE_SVG.replace("sample-desc", "missing-desc", 1), "missing SVG IDs"),
        (ACCESSIBLE_SVG.replace("viewBox=\"0 0 400 240\"", "viewBox=\"0 0 0 240\""), "positive"),
        (
            ACCESSIBLE_SVG.replace("</svg>", '<script id="sample-script">bad()</script></svg>'),
            "unsafe SVG element",
        ),
        (
            ACCESSIBLE_SVG.replace("<rect", '<image href="https://example.test/a.png"/><rect'),
            "unsafe external SVG reference",
        ),
        (
            ACCESSIBLE_SVG.replace("<rect", '<rect onload="bad()"/><rect'),
            "event attribute",
        ),
        (
            ACCESSIBLE_SVG.replace('x="30" y="50"', 'x="430" y="50"'),
            "outside the SVG viewBox",
        ),
    ),
)
def test_invalid_or_unsafe_svg_is_rejected(svg: str, message: str) -> None:
    result = validate_svg_text(svg, slug="sample")
    assert not result.valid
    assert any(message in error for error in result.errors)


def test_duplicate_svg_ids_fail() -> None:
    svg = ACCESSIBLE_SVG.replace(
        "</svg>", '<g id="sample-title"><text>Duplicate</text></g></svg>'
    )
    result = validate_svg_text(svg, slug="sample")
    assert not result.valid
    assert "duplicate SVG ID 'sample-title'" in result.errors


def test_status_requires_non_colour_cue() -> None:
    svg = ACCESSIBLE_SVG.replace(
        "</svg>", '<g id="sample-status" data-status="danger"><circle r="8"/></g></svg>'
    )
    result = validate_svg_text(svg, slug="sample")
    assert not result.valid
    assert any("colour is not the only carrier" in error for error in result.errors)


@pytest.mark.parametrize(
    "unsafe",
    (
        "<script>bad()</script>",
        '<iframe src="x"></iframe>',
        '<div onclick="bad()"></div>',
        '<img src="data:image/png;base64,AAAA">',
        "<style>@import 'bad.css';</style>",
        '<div style="background:url(https://example.test/x)"></div>',
    ),
)
def test_unsafe_html_is_rejected(unsafe: str) -> None:
    html = f"<!doctype html><html><body>{unsafe}{ACCESSIBLE_SVG}</body></html>"
    result = validate_html_text(html)
    assert not result.valid


def test_standalone_svg_extraction_preserves_inline_svg() -> None:
    html = f"<!doctype html><html><body>{ACCESSIBLE_SVG}</body></html>"
    assert extract_svg_text(html).strip() == ACCESSIBLE_SVG.strip()


def test_extraction_rejects_unsafe_or_ambiguous_html() -> None:
    with pytest.raises(ValueError, match="unsafe HTML"):
        extract_svg_text(f"<script>bad()</script>{ACCESSIBLE_SVG}")
    with pytest.raises(ValueError, match="exactly one canonical"):
        extract_svg_text(ACCESSIBLE_SVG + ACCESSIBLE_SVG)


def test_extraction_selector_resolves_multiple_svgs() -> None:
    second = ACCESSIBLE_SVG.replace("sample-", "other-").replace(
        'id="sample-diagram"', 'id="other-diagram"'
    )
    extracted = extract_svg_text(ACCESSIBLE_SVG + second, selector="#other-diagram")
    assert 'id="other-diagram"' in extracted


def test_defused_xml_rejects_entity_expansion() -> None:
    unsafe = """<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <svg viewBox="0 0 10 10" role="img" aria-labelledby="t d">
    <title id="t">Title</title>
    <desc id="d">This description is long enough.</desc>
    <text>&xxe;</text></svg>"""
    result = validate_svg_text(unsafe)
    assert not result.valid
    assert any("safely parse" in error for error in result.errors)


def test_example_svg_uses_embedded_semantic_theme_tokens() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in sorted(
        (root / "skills/diagrammatical/assets/examples/architecture").glob("*/*.svg")
    ):
        content = path.read_text(encoding="utf-8")
        for role in (
            "--canvas",
            "--surface",
            "--ink",
            "--ink-muted",
            "--rule",
            "--connector",
            "--emphasis-primary",
            "--external",
        ):
            assert role in content, f"{path} does not use {role}"
