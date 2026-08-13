#!/usr/bin/env python3
"""Compare fixed-viewport browser screenshots with explicitly reviewed PNG baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tests/visual/baselines"
VIEWPORT = {"width": 1440, "height": 1000}


def sources() -> list[Path]:
    examples = sorted((ROOT / "skills/diagrammatical/assets/examples").glob("*/*/*.html"))
    calibrations = sorted((ROOT / "tests/visual/fixtures").glob("*/calibration.html"))
    return examples + calibrations


def baseline_name(source: Path) -> str:
    return "--".join(source.relative_to(ROOT).with_suffix("").parts) + ".png"


def run(*, update: bool = False) -> dict[str, object]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"valid": False, "errors": ["Playwright is required for visual regression"]}
    errors: list[str] = []
    checked: list[dict[str, str]] = []
    BASELINES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="diagrammatical-visual-") as temporary:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except PlaywrightError as exc:
                return {"valid": False, "errors": [f"Chromium could not start: {exc}"]}
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
            page.emulate_media(reduced_motion="reduce")
            for index, source in enumerate(sources()):
                page.goto(source.resolve().as_uri(), wait_until="load")
                page.evaluate("document.fonts.ready")
                actual = Path(temporary) / f"{index}.png"
                page.locator("svg").first.screenshot(path=str(actual), animations="disabled")
                baseline = BASELINES / baseline_name(source)
                if update:
                    baseline.write_bytes(actual.read_bytes())
                elif not baseline.is_file():
                    errors.append(f"missing baseline: {baseline.relative_to(ROOT)}")
                    continue
                expected_hash = hashlib.sha256(baseline.read_bytes()).hexdigest()
                actual_hash = hashlib.sha256(actual.read_bytes()).hexdigest()
                if expected_hash != actual_hash:
                    errors.append(f"screenshot changed: {source.relative_to(ROOT)}")
                checked.append({"source": str(source.relative_to(ROOT)), "baseline": baseline.name})
            browser.close()
    return {
        "valid": not errors,
        "viewport": VIEWPORT,
        "threshold": "exact pixel output (zero unreviewed difference)",
        "updated": update,
        "checked": checked,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="replace baselines after explicit maintainer visual review; never use in CI",
    )
    args = parser.parse_args()
    result = run(update=args.update)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
