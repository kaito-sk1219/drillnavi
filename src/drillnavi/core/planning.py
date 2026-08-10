"""日割りノルマ計算のための純関数群。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DailyQuota:
    """ある基準日における日割りノルマの計算結果。"""

    remaining_days: int
    remaining_pages: int
    pages_per_day: int
    is_overdue: bool


def calculate_daily_quota(
    total_pages: int,
    completed_pages: int,
    due: date,
    today: date,
) -> DailyQuota:
    """総ページ数・完了済みページ数・締切日・基準日から日割りノルマを計算する。

    基準日(today)自体を学習日1日分として数える。締切日を過ぎている場合は
    is_overdue=True とし、残りページを基準日にまとめて割り当てる。
    """
    if total_pages < 0:
        raise ValueError("total_pages must be non-negative")
    if completed_pages < 0:
        raise ValueError("completed_pages must be non-negative")

    remaining_pages = max(total_pages - completed_pages, 0)
    days_until_due = (due - today).days
    is_overdue = days_until_due < 0
    remaining_days = max(days_until_due, 0) + 1

    pages_per_day = 0
    if remaining_pages > 0:
        pages_per_day = -(-remaining_pages // remaining_days)  # ceiling division

    return DailyQuota(
        remaining_days=remaining_days,
        remaining_pages=remaining_pages,
        pages_per_day=pages_per_day,
        is_overdue=is_overdue,
    )
