from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from defusedxml import ElementTree

from skills.diagrammatical.scripts.gantt_dates import (
    date_to_x,
    inclusive_duration,
    parse_iso_date,
    resolve_end,
    select_scale,
    task_span,
)
from skills.diagrammatical.scripts.self_check import run_self_check
from skills.diagrammatical.scripts.validate import load_structured_file, validate_document

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/diagrammatical/assets/examples"


def load_example(kind: str, slug: str) -> dict:
    return load_structured_file(EXAMPLES / kind / slug / "diagram.yaml")


def validate(source: dict):
    return validate_document(source, "diagram")


def test_valid_standard_and_async_sequences() -> None:
    standard = load_example("sequence", "catalogue-request")
    standard["presentation"]["composition"] = "standard"
    assert validate(standard).valid
    assert validate(load_example("sequence", "order-event")).valid


def test_valid_sequence_exception_fragment() -> None:
    assert validate(load_example("sequence", "token-refresh")).valid


def test_sequence_unknown_participant() -> None:
    source = load_example("sequence", "catalogue-request")
    source["sequence"]["messages"][0]["to"] = "missing"
    result = validate(source)
    assert not result.valid
    assert any("unknown to participant 'missing'" in error for error in result.errors)


def test_sequence_invalid_or_duplicate_message_order() -> None:
    source = load_example("sequence", "catalogue-request")
    source["sequence"]["messages"][1]["order"] = 1
    result = validate(source)
    assert not result.valid
    assert any("order values must be unique" in error for error in result.errors)


def test_sequence_invalid_fragment_range() -> None:
    source = load_example("sequence", "token-refresh")
    source["sequence"]["fragments"][0]["startOrder"] = 9
    result = validate(source)
    assert not result.valid
    assert any(
        "starts after it ends" in error or "invalid message range" in error
        for error in result.errors
    )


def test_sequence_loop_requires_guard() -> None:
    source = load_example("sequence", "token-refresh")
    fragment = source["sequence"]["fragments"][0]
    fragment["kind"] = "loop"
    del fragment["guard"]
    result = validate(source)
    assert not result.valid
    assert any("loop fragment" in error and "guard" in error for error in result.errors)


def test_sequence_complexity_warnings() -> None:
    source = load_example("sequence", "catalogue-request")
    source["nodes"].extend(
        [
            {"id": "extra-one", "label": "Extra one", "kind": "service"},
            {"id": "extra-two", "label": "Extra two", "kind": "service"},
        ]
    )
    for order in range(8, 14):
        source["sequence"]["messages"].append(
            {
                "id": f"extra-message-{order}",
                "from": "api",
                "to": "extra-one",
                "label": "Extra call",
                "order": order,
                "kind": "sync",
            }
        )
    result = validate(source)
    assert result.valid, result.errors
    assert any("lifeline count" in warning for warning in result.warnings)
    assert any("message count" in warning for warning in result.warnings)


def test_valid_rooted_sitemap() -> None:
    assert validate(load_example("sitemap", "marketing-site")).valid


def test_sitemap_missing_root_and_multiple_roots() -> None:
    source = load_example("sitemap", "support-hub")
    source["sitemap"]["root"] = "missing"
    result = validate(source)
    assert not result.valid
    assert any("root 'missing'" in error for error in result.errors)
    source = load_example("sitemap", "support-hub")
    source["nodes"].append({"id": "orphan", "label": "Orphan", "kind": "page", "route": "/orphan"})
    result = validate(source)
    assert not result.valid
    assert any("multiple undeclared roots" in error for error in result.errors)


def test_sitemap_unknown_parent_and_cycle() -> None:
    source = load_example("sitemap", "support-hub")
    source["sitemap"]["hierarchy"][0]["parent"] = "missing"
    assert any("unknown parent" in error for error in validate(source).errors)
    source = load_example("sitemap", "support-hub")
    source["sitemap"]["hierarchy"].append(
        {"parent": "documentation", "child": "support", "order": 1}
    )
    assert any("cycle" in error for error in validate(source).errors)


def test_sitemap_depth_and_sibling_warnings() -> None:
    source = load_example("sitemap", "marketing-site")
    for index in range(6):
        node_id = f"extra-page-{index}"
        source["nodes"].append(
            {"id": node_id, "label": f"Extra {index}", "kind": "page", "route": f"/extra/{index}"}
        )
        source["sitemap"]["hierarchy"].append(
            {"parent": "home", "child": node_id, "order": 10 + index}
        )
    previous = "platform"
    for index in range(3):
        node_id = f"deep-page-{index}"
        source["nodes"].append(
            {"id": node_id, "label": f"Deep {index}", "kind": "page", "route": f"/deep/{index}"}
        )
        source["sitemap"]["hierarchy"].append({"parent": previous, "child": node_id, "order": 1})
        previous = node_id
    result = validate(source)
    assert result.valid, result.errors
    assert any("depth" in warning for warning in result.warnings)
    assert any("siblings" in warning for warning in result.warnings)


def test_sitemap_cross_link_requires_distinct_treatment() -> None:
    source = load_example("sitemap", "support-hub")
    source["sitemap"]["crossLinks"][0]["treatment"] = "solid"
    result = validate(source)
    assert not result.valid
    assert any("not one of" in error and "solid" in error for error in result.errors)


def test_gantt_date_parsing_duration_and_derived_end() -> None:
    assert parse_iso_date("2026-09-01").isoformat() == "2026-09-01"
    assert inclusive_duration("2026-09-01", "2026-09-12") == 12
    assert resolve_end("2026-09-08", 4).isoformat() == "2026-09-11"
    assert select_scale("2026-09-01", "2026-10-30") == "week"
    with pytest.raises(ValueError, match="invalid ISO date"):
        parse_iso_date("03/04/2027")


def test_exact_gantt_date_to_coordinate_calculations() -> None:
    assert date_to_x("2026-09-01", "2026-09-01", "2026-10-30", 360, 1120) == 360
    assert date_to_x("2026-09-30", "2026-09-01", "2026-10-30", 360, 1120) == pytest.approx(
        727.333333
    )
    assert task_span(
        "2026-09-14", "2026-10-02", "2026-09-01", "2026-10-30", 360, 1120
    ) == pytest.approx((524.666667, 240.666667))


@pytest.mark.parametrize("slug", ("mobile-launch", "platform-workstreams", "release-gates"))
def test_every_gantt_bar_matches_source_dates(slug: str) -> None:
    directory = EXAMPLES / "gantt" / slug
    document = load_structured_file(directory / "diagram.yaml")
    gantt = document["gantt"]
    root = ElementTree.fromstring((directory / f"{slug}.svg").read_text(encoding="utf-8"))
    bars = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "rect"
        and element.attrib.get("class") in {"bar", "done", "critical"}
    ]
    tasks = [task for task in gantt["tasks"] if not task.get("milestone")]
    assert len(bars) == len(tasks)
    for bar, task in zip(bars, tasks, strict=True):
        end = task.get("end") or resolve_end(task["start"], task["durationDays"])
        expected_x, expected_width = task_span(
            task["start"], end, gantt["planStart"], gantt["planEnd"], 360, 1120
        )
        assert float(bar.attrib["x"]) == pytest.approx(expected_x, abs=0.02)
        assert float(bar.attrib["width"]) == pytest.approx(expected_width, abs=0.02)


def test_valid_phased_gantt_and_range_failures() -> None:
    source = load_example("gantt", "mobile-launch")
    assert validate(source).valid
    source["gantt"]["tasks"][0]["end"] = "2026-08-31"
    result = validate(source)
    assert not result.valid
    assert any("end date must be" in error for error in result.errors)


def test_gantt_missing_dates_and_unknown_dependency() -> None:
    source = load_example("gantt", "mobile-launch")
    del source["gantt"]["tasks"][0]["start"]
    assert not validate(source).valid
    source = load_example("gantt", "mobile-launch")
    source["gantt"]["tasks"][0]["dependencies"] = ["missing"]
    assert any("unknown dependency 'missing'" in error for error in validate(source).errors)


def test_gantt_circular_dependencies_and_milestone_duration() -> None:
    source = load_example("gantt", "mobile-launch")
    source["gantt"]["tasks"][0]["dependencies"] = ["scope"]
    assert any("dependency cycle" in error for error in validate(source).errors)
    source = load_example("gantt", "mobile-launch")
    source["gantt"]["tasks"][-1]["start"] = "2026-10-29"
    assert any(
        "milestone" in error and "zero elapsed" in error for error in validate(source).errors
    )


def test_gantt_plan_range_progress_and_complexity() -> None:
    source = load_example("gantt", "release-gates")
    source["gantt"]["tasks"][0]["start"] = "2027-02-28"
    assert any("outside" in error for error in validate(source).errors)
    source = load_example("gantt", "release-gates")
    source["gantt"]["tasks"][0]["progress"] = 101
    assert not validate(source).valid
    source = load_example("gantt", "release-gates")
    for index in range(7):
        source["gantt"]["tasks"].append(
            {"id": f"extra-{index}", "label": "Extra", "start": "2027-03-01", "end": "2027-03-01"}
        )
    source["gantt"]["workstreams"].extend(["fifth", "sixth"])
    result = validate(source)
    assert result.valid, result.errors
    assert any("task count" in warning for warning in result.warnings)
    assert any("workstream count" in warning for warning in result.warnings)


@pytest.mark.parametrize("kind", ("sequence", "sitemap", "gantt"))
def test_all_new_examples_pass_self_check_and_are_distinct(kind: str) -> None:
    directories = sorted(path for path in (EXAMPLES / kind).iterdir() if path.is_dir())
    assert len(directories) == 3
    compositions = set()
    for directory in directories:
        result = run_self_check(directory)
        assert result.valid, result.errors
        assert result.warnings == []
        document = load_structured_file(directory / "diagram.yaml")
        compositions.add(document["presentation"]["composition"])
        svg = (directory / f"{directory.name}.svg").read_text(encoding="utf-8")
        assert "--canvas" in svg and "--emphasis-primary" in svg and "<desc" in svg
        report = json.loads((directory / "validation.json").read_text(encoding="utf-8"))
        assert report["valid"] is True
        assert report["visualReview"]["status"] == "completed"
        assert len(report["visualReview"]["findings"]) >= 3
    assert len(compositions) == 3


def test_milestone5_validation_does_not_mutate_sources() -> None:
    for kind, slug in (
        ("sequence", "catalogue-request"),
        ("sitemap", "marketing-site"),
        ("gantt", "mobile-launch"),
    ):
        source = load_example(kind, slug)
        original = deepcopy(source)
        validate(source)
        assert source == original


@pytest.mark.parametrize(
    ("reference", "recipes"),
    (
        (
            "sequence",
            (
                "standard",
                "request-response",
                "authentication-refresh",
                "async-event",
                "exception-path",
            ),
        ),
        ("sitemap", ("conventional-tree", "product-sections", "hub-navigation", "user-journey")),
        ("gantt", ("phased-plan", "workstreams", "milestone-led")),
    ),
)
def test_type_references_document_every_composition(
    reference: str, recipes: tuple[str, ...]
) -> None:
    content = (ROOT / f"skills/diagrammatical/references/types/{reference}.md").read_text(
        encoding="utf-8"
    )
    for recipe in recipes:
        assert f"### `{recipe}`" in content
    for phrase in ("When to use", "When not to use", "Audiences", "Complexity", "Failure modes"):
        assert phrase in content
