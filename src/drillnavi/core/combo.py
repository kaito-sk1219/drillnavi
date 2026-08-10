"""fun モードのコンボ数・称号判定のための純関数群。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ComboTitle:
    """コンボ数がこの値以上になったときに付与される称号。"""

    threshold: int
    name: str


DEFAULT_TITLES: tuple[ComboTitle, ...] = (
    ComboTitle(0, "はじめの一歩"),
    ComboTitle(3, "がんばり屋"),
    ComboTitle(5, "れんしょう王"),
    ComboTitle(10, "スーパースター"),
    ComboTitle(20, "でんせつ"),
)


def update_combo(current_combo: int, correct: bool) -> int:
    """正解ならコンボを1増やし、不正解なら0にリセットする。"""
    if current_combo < 0:
        raise ValueError("current_combo must be non-negative")
    return current_combo + 1 if correct else 0


def title_for_combo(
    combo: int,
    titles: Sequence[ComboTitle] = DEFAULT_TITLES,
) -> str:
    """コンボ数に応じた称号名を返す。

    しきい値(threshold)以下で最も高いものの称号が採用される。
    titles には threshold=0 の要素が含まれている必要がある。
    """
    if combo < 0:
        raise ValueError("combo must be non-negative")
    if not titles:
        raise ValueError("titles must not be empty")

    sorted_titles = sorted(titles, key=lambda t: t.threshold)
    if sorted_titles[0].threshold != 0:
        raise ValueError("titles must include an entry with threshold=0")

    current_name = sorted_titles[0].name
    for title in sorted_titles:
        if combo >= title.threshold:
            current_name = title.name
        else:
            break
    return current_name
