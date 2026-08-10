"""grow モードの難易度調整のための純関数群。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

Direction = Literal["up", "down", "same"]


@dataclass(frozen=True)
class DifficultyAdjustment:
    """難易度調整の計算結果。"""

    new_level: int
    accuracy: float | None
    direction: Direction


def adjust_difficulty(
    current_level: int,
    recent_results: Sequence[bool],
    *,
    window: int = 10,
    target_accuracy: float = 0.7,
    min_level: int = 1,
    max_level: int = 10,
) -> DifficultyAdjustment:
    """直近の正誤結果から難易度レベルを1段階上下させる。

    正答率が target_accuracy を上回れば難化、下回れば易化、
    ちょうど一致すれば据え置き。レベルは [min_level, max_level] の範囲に
    クランプされる。recent_results が空の場合は現在のレベルを維持する。
    """
    if min_level > max_level:
        raise ValueError("min_level must be <= max_level")
    if not (min_level <= current_level <= max_level):
        raise ValueError("current_level must be within [min_level, max_level]")
    if window <= 0:
        raise ValueError("window must be positive")

    window_results = recent_results[-window:]
    if not window_results:
        return DifficultyAdjustment(new_level=current_level, accuracy=None, direction="same")

    accuracy = sum(window_results) / len(window_results)

    if accuracy > target_accuracy:
        return DifficultyAdjustment(
            new_level=min(current_level + 1, max_level),
            accuracy=accuracy,
            direction="up",
        )
    if accuracy < target_accuracy:
        return DifficultyAdjustment(
            new_level=max(current_level - 1, min_level),
            accuracy=accuracy,
            direction="down",
        )
    return DifficultyAdjustment(new_level=current_level, accuracy=accuracy, direction="same")
