from __future__ import annotations

import builtins
import os
from pathlib import Path

import pytest

from skills.diagrammatical.scripts.export_png import INSTALL_MESSAGE, export_png
from skills.diagrammatical.scripts.extract_svg import extract_svg_file, extract_svg_text
from skills.diagrammatical.scripts.validate_svg import validate_svg

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = ROOT / "skills/diagrammatical/assets/examples"
SAMPLE_HTML = EXAMPLE_ROOT / "architecture/event-ingestion-pipeline/event-ingestion-pipeline.html"
SAMPLE_SVG = EXAMPLE_ROOT / "architecture/event-ingestion-pipeline/event-ingestion-pipeline.svg"
PLAYWRIGHT_ENABLED = os.environ.get("DIAGRAMMATICAL_PLAYWRIGHT") == "1"


def test_single_svg_extraction_is_deterministic_and_preserves_required_content() -> None:
    source = SAMPLE_HTML.read_text(encoding="utf-8")
    first = extract_svg_text(source)
    second = extract_svg_text(source)
    assert first == second
    assert "viewBox=" in first
    assert "<defs>" in first and "<marker" in first
    assert "<style>" in first
    assert "<title" in first and "<desc" in first


def test_ambiguous_svg_requires_simple_id_selector() -> None:
    svg = SAMPLE_SVG.read_text(encoding="utf-8")
    root = svg.split("<svg", 1)[1].split(">", 1)[0]
    diagram_id = (
        next(part.split('"', 1)[0] for part in root.split('id="')[1:] if part)
        if 'id="' in root
        else None
    )
    if diagram_id is None:
        svg = svg.replace("<svg ", '<svg id="selected-diagram" ', 1)
        diagram_id = "selected-diagram"
    other_svg = svg.replace(diagram_id, "other-diagram", 1)
    html = f"<!doctype html><html><body>{svg}{other_svg}</body></html>"
    with pytest.raises(ValueError, match="found 2"):
        extract_svg_text(html)
    selected = extract_svg_text(html, selector=f"#{diagram_id}")
    assert f'id="{diagram_id}"' in selected


@pytest.mark.parametrize(
    ("html", "message"),
    (
        ("<html><body>No diagram</body></html>", "found 0"),
        ("<html><body><svg><title>x</title></svg></body></html>", "viewBox"),
        ("<html><body><svg viewBox='0 0 10 10'><script>x</script></svg></body></html>", "unsafe"),
        ("<html><body><svg viewBox='0 0 10 10' onclick='x()'></svg></body></html>", "event"),
        (
            "<html><body><svg viewBox='0 0 10 10'><use href='https://x'/></svg></body></html>",
            "remote",
        ),
    ),
)
def test_invalid_or_unsafe_extraction_fails(html: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        extract_svg_text(html)


def test_extract_file_produces_svg_that_passes_self_check(tmp_path: Path) -> None:
    output = tmp_path / "diagram.svg"
    extract_svg_file(SAMPLE_HTML, output)
    assert validate_svg(output, slug="event-ingestion-pipeline").valid


def test_duplicate_ids_are_rejected_during_extraction() -> None:
    source = SAMPLE_HTML.read_text(encoding="utf-8")
    source = source.replace(
        'id="event-ingestion-pipeline-desc"',
        'id="event-ingestion-pipeline-title"',
        1,
    )
    with pytest.raises(ValueError, match="duplicate SVG ID"):
        extract_svg_text(source)


@pytest.mark.parametrize("scale", [1, 2, 4])
@pytest.mark.skipif(not PLAYWRIGHT_ENABLED, reason="set DIAGRAMMATICAL_PLAYWRIGHT=1")
def test_explicit_svg_png_export_has_viewbox_derived_dimensions(tmp_path: Path, scale: int) -> None:
    output = tmp_path / f"diagram-{scale}.png"
    result = export_png(SAMPLE_SVG, output, scale=scale)
    assert result.valid, result.errors
    assert output.is_file()
    assert (result.width, result.height) == (1200 * scale, 720 * scale)


@pytest.mark.skipif(not PLAYWRIGHT_ENABLED, reason="set DIAGRAMMATICAL_PLAYWRIGHT=1")
def test_explicit_html_diagram_and_full_frame_export(tmp_path: Path) -> None:
    diagram = export_png(SAMPLE_HTML, tmp_path / "diagram.png", scale=1)
    frame = export_png(SAMPLE_HTML, tmp_path / "frame.png", scale=1, full_frame=True)
    assert diagram.valid and frame.valid
    assert diagram.frame == "diagram-only"
    assert frame.frame == "full-editorial"
    assert frame.width and frame.height


@pytest.mark.skipif(not PLAYWRIGHT_ENABLED, reason="set DIAGRAMMATICAL_PLAYWRIGHT=1")
def test_invalid_scale_and_existing_file_protection_and_force(tmp_path: Path) -> None:
    assert not export_png(SAMPLE_SVG, tmp_path / "bad.png", scale=0).valid
    output = tmp_path / "existing.png"
    output.write_bytes(b"old")
    protected = export_png(SAMPLE_SVG, output)
    assert not protected.valid and output.read_bytes() == b"old"
    replaced = export_png(SAMPLE_SVG, output, scale=1, force=True)
    assert replaced.valid and output.read_bytes() != b"old"


def test_unsafe_input_rejected_before_browser_launch(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.svg"
    unsafe.write_text('<svg viewBox="0 0 10 10"><script>x()</script></svg>', encoding="utf-8")
    result = export_png(unsafe, tmp_path / "unsafe.png")
    assert not result.valid
    assert any("script" in error for error in result.errors)


def test_missing_playwright_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real_import = builtins.__import__

    def missing(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("playwright"):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    result = export_png(SAMPLE_SVG, tmp_path / "missing.png")
    assert not result.valid
    assert INSTALL_MESSAGE in result.errors[0]


def test_missing_chromium_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from playwright.sync_api import Error as PlaywrightError

    class MissingChromium:
        def launch(self, **kwargs: object) -> None:
            raise PlaywrightError("Executable doesn't exist")

    class Playwright:
        chromium = MissingChromium()

    class Manager:
        def __enter__(self) -> Playwright:
            return Playwright()

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: Manager())
    result = export_png(SAMPLE_SVG, tmp_path / "missing-chromium.png")
    assert not result.valid
    assert "playwright install chromium" in result.errors[0]


def test_font_timeout_falls_back_and_browser_network_is_blocked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    class Request:
        url = "https://unexpected.example/font.woff2"

    class Route:
        request = Request()

        def abort(self) -> None:
            return None

        def continue_(self) -> None:
            return None

    class Locator:
        first: Locator

        def __init__(self) -> None:
            self.first = self

        def screenshot(self, *, path: str) -> None:
            Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    class Page:
        def route(self, _pattern: str, callback: object) -> None:
            callback(Route())  # type: ignore[operator]

        def set_content(self, *_args: object, **_kwargs: object) -> None:
            return None

        def evaluate(self, *_args: object) -> None:
            raise PlaywrightTimeoutError("font timeout")

        def locator(self, _selector: str) -> Locator:
            return Locator()

    class Context:
        def new_page(self) -> Page:
            return Page()

    class Browser:
        def new_context(self, **_kwargs: object) -> Context:
            return Context()

        def close(self) -> None:
            return None

    class Chromium:
        def launch(self, **_kwargs: object) -> Browser:
            return Browser()

    class Playwright:
        chromium = Chromium()

    class Manager:
        def __enter__(self) -> Playwright:
            return Playwright()

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: Manager())
    result = export_png(SAMPLE_SVG, tmp_path / "fallback.png", font_timeout_ms=1)
    assert result.valid
    assert result.fontFallbackUsed
    assert result.networkRequestsBlocked == 1


def test_font_timeout_uses_fallback_and_network_is_blocked(tmp_path: Path) -> None:
    html_path = tmp_path / "network-font.html"
    html_path.write_text(
        SAMPLE_HTML.read_text(encoding="utf-8").replace(
            "</head>", '<link rel="stylesheet" href="https://fonts.example/font.css"></head>'
        ),
        encoding="utf-8",
    )
    # HTML safety rejects arbitrary remote styles before a browser can request them.
    blocked = export_png(html_path, tmp_path / "blocked.png", font_timeout_ms=1)
    assert not blocked.valid
    assert any("remote resource" in error for error in blocked.errors)


def test_every_checked_in_example_extracts_to_identical_standalone_svg() -> None:
    for diagram in sorted(EXAMPLE_ROOT.glob("*/*/diagram.yaml")):
        source = __import__("yaml").safe_load(diagram.read_text(encoding="utf-8"))
        slug = source["diagram"]["id"]
        extracted = extract_svg_text((diagram.parent / f"{slug}.html").read_text(encoding="utf-8"))
        canonical = (diagram.parent / f"{slug}.svg").read_text(encoding="utf-8")
        assert extracted.strip() == canonical.strip(), diagram.parent


def test_ordinary_workflows_contain_no_png() -> None:
    assert not list(EXAMPLE_ROOT.rglob("*.png"))
    assert not list((ROOT / "skills/diagrammatical/assets/templates").glob("*.png"))
