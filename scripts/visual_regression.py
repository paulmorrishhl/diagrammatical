#!/usr/bin/env python3
"""Compare fixed-viewport browser screenshots with explicitly reviewed PNG baselines."""

from __future__ import annotations

import argparse
import base64
import json
import tempfile
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tests/visual/baselines"
VIEWPORT = {"width": 1440, "height": 1000}
PIXEL_DELTA_THRESHOLD = 8
MAX_CHANGED_PIXEL_RATIO = 0.02
MAX_MEAN_CHANNEL_DELTA = 0.005


class PixelComparison(NamedTuple):
    width: int
    height: int
    changed_pixel_ratio: float
    mean_channel_delta: float


def compare_pixel_buffers(
    expected_pixels: bytes, actual_pixels: bytes, width: int, height: int
) -> PixelComparison:
    """Measure RGBA buffer differences independently of PNG compression."""

    if len(expected_pixels) != len(actual_pixels) or len(expected_pixels) != width * height * 4:
        raise ValueError("pixel buffers do not match the supplied dimensions")
    pixel_count = width * height
    changed = 0
    total_delta = 0
    expected_words = memoryview(expected_pixels).cast("I")
    actual_words = memoryview(actual_pixels).cast("I")
    for expected_pixel, actual_pixel in zip(expected_words, actual_words, strict=True):
        delta_0 = abs((expected_pixel & 0xFF) - (actual_pixel & 0xFF))
        delta_1 = abs(((expected_pixel >> 8) & 0xFF) - ((actual_pixel >> 8) & 0xFF))
        delta_2 = abs(((expected_pixel >> 16) & 0xFF) - ((actual_pixel >> 16) & 0xFF))
        delta_3 = abs(((expected_pixel >> 24) & 0xFF) - ((actual_pixel >> 24) & 0xFF))
        if (
            delta_0 > PIXEL_DELTA_THRESHOLD
            or delta_1 > PIXEL_DELTA_THRESHOLD
            or delta_2 > PIXEL_DELTA_THRESHOLD
            or delta_3 > PIXEL_DELTA_THRESHOLD
        ):
            changed += 1
        total_delta += delta_0 + delta_1 + delta_2 + delta_3
    return PixelComparison(
        width=width,
        height=height,
        changed_pixel_ratio=changed / pixel_count,
        mean_channel_delta=total_delta / (pixel_count * 4 * 255),
    )


def compare_png_in_browser(page: object, expected: Path, actual: Path) -> PixelComparison:
    """Use Chromium's native image decoder for fast comparison during the Playwright suite."""

    urls = [
        "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        for path in (expected, actual)
    ]
    result = page.evaluate(  # type: ignore[attr-defined]
        """async ([expectedUrl, actualUrl, deltaThreshold]) => {
          const load = async (url) => {
            const image = new Image();
            image.src = url;
            await image.decode();
            return image;
          };
          const [expected, actual] = await Promise.all([load(expectedUrl), load(actualUrl)]);
          if (expected.width !== actual.width || expected.height !== actual.height) {
            throw new Error(
              `screenshot dimensions changed: ${expected.width}x${expected.height} != ` +
              `${actual.width}x${actual.height}`
            );
          }
          const canvas = document.createElement('canvas');
          canvas.width = expected.width;
          canvas.height = expected.height;
          const context = canvas.getContext('2d', {willReadFrequently: true});
          context.drawImage(expected, 0, 0);
          const expectedPixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
          context.clearRect(0, 0, canvas.width, canvas.height);
          context.drawImage(actual, 0, 0);
          const actualPixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
          let changed = 0;
          let totalDelta = 0;
          for (let index = 0; index < expectedPixels.length; index += 4) {
            let pixelChanged = false;
            for (let channel = 0; channel < 4; channel += 1) {
              const delta = Math.abs(
                expectedPixels[index + channel] - actualPixels[index + channel]
              );
              totalDelta += delta;
              pixelChanged ||= delta > deltaThreshold;
            }
            changed += Number(pixelChanged);
          }
          const pixels = expected.width * expected.height;
          return {
            width: expected.width,
            height: expected.height,
            changedPixelRatio: changed / pixels,
            meanChannelDelta: totalDelta / (pixels * 4 * 255),
          };
        }""",
        [*urls, PIXEL_DELTA_THRESHOLD],
    )
    return PixelComparison(
        width=result["width"],
        height=result["height"],
        changed_pixel_ratio=result["changedPixelRatio"],
        mean_channel_delta=result["meanChannelDelta"],
    )


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
                try:
                    comparison = compare_png_in_browser(page, baseline, actual)
                except (ValueError, PlaywrightError) as exc:
                    errors.append(f"screenshot changed: {source.relative_to(ROOT)} ({exc})")
                    continue
                within_tolerance = (
                    comparison.changed_pixel_ratio <= MAX_CHANGED_PIXEL_RATIO
                    and comparison.mean_channel_delta <= MAX_MEAN_CHANNEL_DELTA
                )
                if not within_tolerance:
                    errors.append(
                        f"screenshot changed: {source.relative_to(ROOT)} "
                        f"(changed pixels {comparison.changed_pixel_ratio:.3%}, "
                        f"mean channel delta {comparison.mean_channel_delta:.3%})"
                    )
                checked.append(
                    {
                        "source": str(source.relative_to(ROOT)),
                        "baseline": baseline.name,
                        "changedPixelRatio": f"{comparison.changed_pixel_ratio:.6f}",
                        "meanChannelDelta": f"{comparison.mean_channel_delta:.6f}",
                    }
                )
            browser.close()
    return {
        "valid": not errors,
        "viewport": VIEWPORT,
        "threshold": {
            "perChannelDelta": PIXEL_DELTA_THRESHOLD,
            "maximumChangedPixelRatio": MAX_CHANGED_PIXEL_RATIO,
            "maximumMeanChannelDelta": MAX_MEAN_CHANNEL_DELTA,
        },
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
