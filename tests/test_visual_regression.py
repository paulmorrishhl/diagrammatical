from scripts.visual_regression import BASELINES, baseline_name, sources


def test_every_visual_source_has_a_reviewable_baseline() -> None:
    assert sources()
    missing = [source for source in sources() if not (BASELINES / baseline_name(source)).is_file()]
    assert not missing


def test_visual_regression_never_updates_baselines_by_default() -> None:
    source = __import__("inspect").getsource(
        __import__("scripts.visual_regression", fromlist=["run"]).run
    )
    assert "update: bool = False" in source
