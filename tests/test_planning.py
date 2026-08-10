from datetime import date

import pytest

from drillnavi.core.planning import calculate_daily_quota


def test_evenly_divisible() -> None:
    quota = calculate_daily_quota(
        total_pages=30,
        completed_pages=0,
        due=date(2026, 8, 15),
        today=date(2026, 8, 10),
    )
    assert quota.remaining_days == 6
    assert quota.remaining_pages == 30
    assert quota.pages_per_day == 5
    assert quota.is_overdue is False


def test_ceiling_division_when_not_evenly_divisible() -> None:
    quota = calculate_daily_quota(
        total_pages=10,
        completed_pages=0,
        due=date(2026, 8, 13),
        today=date(2026, 8, 10),
    )
    # 残り4日で10ページ -> 1日あたり3ページ(切り上げ)
    assert quota.remaining_days == 4
    assert quota.pages_per_day == 3


def test_due_today_counts_as_one_study_day() -> None:
    quota = calculate_daily_quota(
        total_pages=5,
        completed_pages=0,
        due=date(2026, 8, 10),
        today=date(2026, 8, 10),
    )
    assert quota.remaining_days == 1
    assert quota.pages_per_day == 5
    assert quota.is_overdue is False


def test_overdue_due_date_in_the_past() -> None:
    quota = calculate_daily_quota(
        total_pages=12,
        completed_pages=0,
        due=date(2026, 8, 1),
        today=date(2026, 8, 10),
    )
    assert quota.is_overdue is True
    assert quota.remaining_days == 1
    assert quota.pages_per_day == 12


def test_no_remaining_pages_gives_zero_quota() -> None:
    quota = calculate_daily_quota(
        total_pages=20,
        completed_pages=20,
        due=date(2026, 8, 20),
        today=date(2026, 8, 10),
    )
    assert quota.remaining_pages == 0
    assert quota.pages_per_day == 0


def test_completed_pages_exceeding_total_clamped_to_zero_remaining() -> None:
    quota = calculate_daily_quota(
        total_pages=10,
        completed_pages=15,
        due=date(2026, 8, 20),
        today=date(2026, 8, 10),
    )
    assert quota.remaining_pages == 0
    assert quota.pages_per_day == 0


def test_total_pages_zero() -> None:
    quota = calculate_daily_quota(
        total_pages=0,
        completed_pages=0,
        due=date(2026, 8, 20),
        today=date(2026, 8, 10),
    )
    assert quota.remaining_pages == 0
    assert quota.pages_per_day == 0


@pytest.mark.parametrize("total_pages,completed_pages", [(-1, 0), (10, -1)])
def test_negative_inputs_raise(total_pages: int, completed_pages: int) -> None:
    with pytest.raises(ValueError):
        calculate_daily_quota(
            total_pages=total_pages,
            completed_pages=completed_pages,
            due=date(2026, 8, 20),
            today=date(2026, 8, 10),
        )
