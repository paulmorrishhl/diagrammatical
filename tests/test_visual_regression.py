from scripts.visual_regression import BASELINES, baseline_name, compare_pixel_buffers, sources


def test_every_visual_source_has_a_reviewable_baseline() -> None:
    assert sources()
    missing = [source for source in sources() if not (BASELINES / baseline_name(source)).is_file()]
    assert not missing


def test_visual_regression_never_updates_baselines_by_default() -> None:
    source = __import__("inspect").getsource(
        __import__("scripts.visual_regression", fromlist=["run"]).run
    )
    assert "update: bool = False" in source


def test_pixel_comparison_measures_visual_change() -> None:
    white = bytes([255, 255, 255, 255] * 100)
    one_black_pixel = bytes([0, 0, 0, 255] + [255, 255, 255, 255] * 99)

    identical = compare_pixel_buffers(white, white, 10, 10)
    difference = compare_pixel_buffers(white, one_black_pixel, 10, 10)

    assert identical.changed_pixel_ratio == 0
    assert identical.mean_channel_delta == 0
    assert difference.changed_pixel_ratio == 0.01
    assert difference.mean_channel_delta > 0
