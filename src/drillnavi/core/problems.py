"""四則演算の問題生成のための純関数群。"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

Operator = Literal["+", "-", "*", "/"]

MIN_LEVEL = 1
MAX_LEVEL = 10


@dataclass(frozen=True)
class Problem:
    """1問分の四則演算問題。"""

    left: int
    right: int
    operator: Operator
    answer: int

    @property
    def prompt(self) -> str:
        return f"{self.left} {self.operator} {self.right}"


def _operators_for_level(level: int) -> tuple[Operator, ...]:
    if level <= 3:
        return ("+", "-")
    if level <= 6:
        return ("+", "-", "*")
    return ("+", "-", "*", "/")


def generate_problem(
    level: int,
    seed: int,
    *,
    min_level: int = MIN_LEVEL,
    max_level: int = MAX_LEVEL,
) -> Problem:
    """難易度レベルと乱数シードから1問生成する。

    同じ (level, seed) の組み合わせからは常に同じ問題が生成される。
    レベルが上がるほど扱う数値の範囲が広がり、加減算のみ -> 乗算追加 ->
    除算追加、の順に出題される演算が増える。減算は結果が負にならないよう
    左辺 >= 右辺になるように生成し、除算は割り切れる組み合わせのみ生成する。
    """
    if min_level > max_level:
        raise ValueError("min_level must be <= max_level")
    if not (min_level <= level <= max_level):
        raise ValueError("level must be within [min_level, max_level]")

    rng = random.Random(seed)
    operator = rng.choice(_operators_for_level(level))

    if operator == "+":
        bound = 5 + level * 5
        left = rng.randint(1, bound)
        right = rng.randint(1, bound)
        answer = left + right
    elif operator == "-":
        bound = 5 + level * 5
        left = rng.randint(1, bound)
        right = rng.randint(1, left)
        answer = left - right
    elif operator == "*":
        bound = 3 + level
        left = rng.randint(2, bound)
        right = rng.randint(2, bound)
        answer = left * right
    else:  # "/"
        bound = 3 + level
        right = rng.randint(2, bound)
        quotient = rng.randint(2, bound)
        left = right * quotient
        answer = quotient

    return Problem(left=left, right=right, operator=operator, answer=answer)


def generate_problems(
    level: int,
    count: int,
    seed: int,
    *,
    min_level: int = MIN_LEVEL,
    max_level: int = MAX_LEVEL,
) -> list[Problem]:
    """指定件数の問題をまとめて生成する。"""
    if count < 0:
        raise ValueError("count must be non-negative")
    return [
        generate_problem(level, seed + i, min_level=min_level, max_level=max_level)
        for i in range(count)
    ]
