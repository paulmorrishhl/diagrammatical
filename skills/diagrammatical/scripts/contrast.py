"""WCAG contrast calculations for semantic brand roles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContrastCheck:
    variant: str
    foreground_role: str
    background_role: str
    ratio: float
    minimum: float

    @property
    def passes(self) -> bool:
        return self.ratio >= self.minimum


def _linear_channel(value: int) -> float:
    channel = value / 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: str) -> float:
    if len(colour) != 7 or not colour.startswith("#"):
        raise ValueError(f"expected a six-digit hex colour, got {colour!r}")
    try:
        channels = [int(colour[index : index + 2], 16) for index in (1, 3, 5)]
    except ValueError as exc:
        raise ValueError(f"expected a six-digit hex colour, got {colour!r}") from exc
    red, green, blue = (_linear_channel(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def validate_brand_contrast(brand: Mapping[str, Any]) -> list[ContrastCheck]:
    """Check intended text and meaningful graphical role pairings for every variant."""

    policy = brand["accessibility"]
    normal_minimum = float(policy["normalTextContrast"])
    variants = brand["variants"]
    results: list[ContrastCheck] = []
    text_pairs = (
        ("ink", "canvas"),
        ("ink", "surface"),
        ("ink", "surfaceSecondary"),
        ("ink", "emphasisPrimaryTint"),
        ("inkMuted", "canvas"),
        ("inkMuted", "surface"),
    )
    graphical_pairs = tuple(
        (role, "canvas")
        for role in (
            "connector",
            "emphasisPrimary",
            "emphasisSecondary",
            "external",
            "success",
            "warning",
            "danger",
            "deprecated",
        )
    )
    for variant_name, variant in variants.items():
        roles = variant["roles"]
        for foreground, background in text_pairs:
            results.append(
                ContrastCheck(
                    variant_name,
                    foreground,
                    background,
                    contrast_ratio(roles[foreground], roles[background]),
                    normal_minimum,
                )
            )
        for foreground, background in graphical_pairs:
            results.append(
                ContrastCheck(
                    variant_name,
                    foreground,
                    background,
                    contrast_ratio(roles[foreground], roles[background]),
                    3.0,
                )
            )
    return results
