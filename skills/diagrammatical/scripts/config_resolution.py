"""Canonical configuration precedence resolution with leaf-value provenance."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

LAYER_ORDER = (
    "diagram-type",
    "art-direction",
    "brand",
    "project",
    "diagram",
    "output-preset",
)


def _merge(
    target: dict[str, Any],
    overlay: Mapping[str, Any],
    provenance: dict[str, str],
    layer: str,
    prefix: tuple[str, ...] = (),
) -> None:
    for key, value in overlay.items():
        path = (*prefix, str(key))
        if isinstance(value, Mapping):
            if not isinstance(target.get(key), dict):
                target[key] = {}
            _merge(target[key], value, provenance, layer, path)
        else:
            target[key] = deepcopy(value)
            provenance[".".join(path)] = layer


def resolve_configuration_with_provenance(
    *,
    safety: Mapping[str, Any],
    diagram_type: Mapping[str, Any] | None = None,
    art_direction: Mapping[str, Any] | None = None,
    brand: Mapping[str, Any] | None = None,
    project: Mapping[str, Any] | None = None,
    diagram: Mapping[str, Any] | None = None,
    output_preset: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply later-layer overrides, then reapply non-overridable safety."""

    layers = (
        ("diagram-type", diagram_type),
        ("art-direction", art_direction),
        ("brand", brand),
        ("project", project),
        ("diagram", diagram),
        ("output-preset", output_preset),
    )
    resolved: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for layer, values in layers:
        if values:
            _merge(resolved, values, provenance, layer)
    _merge(resolved, safety, provenance, "non-overridable-safety")
    return {"tokens": resolved, "provenance": provenance, "layers": list(LAYER_ORDER)}
