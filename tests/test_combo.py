import pytest

from drillnavi.core.combo import ComboTitle, title_for_combo, update_combo


def test_correct_answer_increments_combo() -> None:
    assert update_combo(current_combo=3, correct=True) == 4


def test_incorrect_answer_resets_combo() -> None:
    assert update_combo(current_combo=7, correct=False) == 0


def test_combo_starts_at_zero() -> None:
    assert update_combo(current_combo=0, correct=True) == 1


def test_negative_current_combo_raises() -> None:
    with pytest.raises(ValueError):
        update_combo(current_combo=-1, correct=True)


def test_title_at_zero_combo() -> None:
    assert title_for_combo(0) == "はじめの一歩"


def test_title_just_below_threshold_uses_lower_tier() -> None:
    assert title_for_combo(2) == "はじめの一歩"
    assert title_for_combo(4) == "がんばり屋"


def test_title_exactly_at_threshold_uses_that_tier() -> None:
    assert title_for_combo(3) == "がんばり屋"
    assert title_for_combo(5) == "れんしょう王"
    assert title_for_combo(10) == "スーパースター"
    assert title_for_combo(20) == "でんせつ"


def test_title_far_above_max_threshold_uses_highest_tier() -> None:
    assert title_for_combo(999) == "でんせつ"


def test_negative_combo_raises() -> None:
    with pytest.raises(ValueError):
        title_for_combo(-1)


def test_empty_titles_raises() -> None:
    with pytest.raises(ValueError):
        title_for_combo(5, titles=())


def test_titles_without_zero_threshold_raises() -> None:
    with pytest.raises(ValueError):
        title_for_combo(5, titles=(ComboTitle(1, "x"),))


def test_custom_titles_are_respected() -> None:
    custom = (ComboTitle(0, "A"), ComboTitle(2, "B"))
    assert title_for_combo(0, titles=custom) == "A"
    assert title_for_combo(1, titles=custom) == "A"
    assert title_for_combo(2, titles=custom) == "B"
