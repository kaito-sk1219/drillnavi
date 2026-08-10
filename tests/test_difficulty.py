import pytest

from drillnavi.core.difficulty import adjust_difficulty


def test_no_history_keeps_level_unchanged() -> None:
    result = adjust_difficulty(current_level=5, recent_results=[])
    assert result.new_level == 5
    assert result.accuracy is None
    assert result.direction == "same"


def test_accuracy_above_target_increases_level() -> None:
    # 8/10 = 80% > 70%
    results = [True] * 8 + [False] * 2
    result = adjust_difficulty(current_level=5, recent_results=results)
    assert result.accuracy == pytest.approx(0.8)
    assert result.new_level == 6
    assert result.direction == "up"


def test_accuracy_below_target_decreases_level() -> None:
    # 6/10 = 60% < 70%
    results = [True] * 6 + [False] * 4
    result = adjust_difficulty(current_level=5, recent_results=results)
    assert result.accuracy == pytest.approx(0.6)
    assert result.new_level == 4
    assert result.direction == "down"


def test_accuracy_exactly_at_target_keeps_level() -> None:
    # 7/10 = 70% == target
    results = [True] * 7 + [False] * 3
    result = adjust_difficulty(current_level=5, recent_results=results)
    assert result.accuracy == pytest.approx(0.7)
    assert result.new_level == 5
    assert result.direction == "same"


def test_level_clamped_at_max() -> None:
    results = [True] * 10
    result = adjust_difficulty(current_level=10, recent_results=results, max_level=10)
    assert result.new_level == 10
    assert result.direction == "up"


def test_level_clamped_at_min() -> None:
    results = [False] * 10
    result = adjust_difficulty(current_level=1, recent_results=results, min_level=1)
    assert result.new_level == 1
    assert result.direction == "down"


def test_only_last_window_results_are_considered() -> None:
    # 直近10問だけ見る: 先頭5問はFalseだが古いので無視され、
    # 直近10問は8/10正解で難化する
    results = [False] * 5 + [True] * 8 + [False] * 2
    result = adjust_difficulty(current_level=5, recent_results=results, window=10)
    assert result.accuracy == pytest.approx(0.8)
    assert result.direction == "up"


@pytest.mark.parametrize("current_level", [0, 11])
def test_current_level_out_of_range_raises(current_level: int) -> None:
    with pytest.raises(ValueError):
        adjust_difficulty(current_level=current_level, recent_results=[True])


def test_min_greater_than_max_raises() -> None:
    with pytest.raises(ValueError):
        adjust_difficulty(current_level=5, recent_results=[True], min_level=8, max_level=2)


def test_non_positive_window_raises() -> None:
    with pytest.raises(ValueError):
        adjust_difficulty(current_level=5, recent_results=[True], window=0)
