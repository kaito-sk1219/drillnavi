"""adjust_difficulty の適応挙動を検証するシミュレーション。

異なる「仮想的な実力レベル」を持つ生徒が drill(grow モード)を解き続けたとき、
core.difficulty.adjust_difficulty によって難易度レベルが実力に見合った値へ
収束していくかどうかを確認する。

実行:
    uv run python experiments/sim_adaptive.py

experiments/output/level_trajectory.png にレベル推移のグラフを出力する。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from drillnavi.core.difficulty import adjust_difficulty

# 日本語グリフ欠落を避けるため、環境にあるフォントを優先順に試す。
plt.rcParams["font.family"] = [
    "Noto Sans JP",
    "Yu Gothic",
    "Meiryo",
    "MS Gothic",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

MIN_LEVEL = 1
MAX_LEVEL = 10
INITIAL_LEVEL = 5
QUESTIONS_PER_RUN = 200
SKILL_LEVELS = (2, 5, 8)
TARGET_ACCURACY = 0.7
SEED = 0
OUTPUT_PATH = Path(__file__).parent / "output" / "level_trajectory.png"


def correctness_probability(problem_level: int, skill_level: int) -> float:
    """問題レベルと実力レベルの差から正答確率を求める確率モデル。

    問題レベルが実力レベルと一致するとき、正答率が adjust_difficulty の
    目標正答率(TARGET_ACCURACY)とちょうど一致するように設定してある。
    これにより、難易度レベルが実力レベルへ収束すれば正答率も目標付近に
    収まる、という理想的な平衡点を確認しやすくしている。
    """
    gap = problem_level - skill_level
    probability = TARGET_ACCURACY - 0.08 * gap
    return float(np.clip(probability, 0.05, 0.95))


def simulate(skill_level: int, rng: np.random.Generator) -> list[int]:
    """1人の仮想生徒について、質問ごとの難易度レベル推移を返す。"""
    level = INITIAL_LEVEL
    history: list[bool] = []
    levels = [level]

    for _ in range(QUESTIONS_PER_RUN):
        p_correct = correctness_probability(level, skill_level)
        correct = bool(rng.random() < p_correct)
        history.append(correct)

        adjustment = adjust_difficulty(
            current_level=level,
            recent_results=history[-10:],
            target_accuracy=TARGET_ACCURACY,
            min_level=MIN_LEVEL,
            max_level=MAX_LEVEL,
        )
        level = adjustment.new_level
        levels.append(level)

    return levels


def main() -> None:
    rng = np.random.default_rng(SEED)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    for skill_level in SKILL_LEVELS:
        levels = simulate(skill_level, rng)
        ax.plot(levels, label=f"実力Lv.{skill_level}")
        converged_avg = float(np.mean(levels[-30:]))
        print(f"実力Lv.{skill_level}: 直近30問の平均到達レベル = {converged_avg:.2f}")

    ax.axhline(INITIAL_LEVEL, color="gray", linestyle=":", linewidth=1, label="初期レベル")
    ax.set_xlabel("出題数")
    ax.set_ylabel("難易度レベル")
    ax.set_ylim(MIN_LEVEL - 1, MAX_LEVEL + 1)
    ax.set_title("adjust_difficulty による難易度レベルの収束シミュレーション")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH)
    print(f"グラフを出力しました: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
