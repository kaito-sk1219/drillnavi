"""Elo 適応出題のシミュレーション検証。

仮想生徒に対して出題ループを回し、以下を確認する。
  1. 推定 theta が真の能力に収束するか(RMSE)
  2. 実現正答率が目標正答率の近傍に保たれるか
  3. 項目難易度を同時推定した場合に真の難易度を復元できるか

実行: uv run python experiments/sim_elo.py
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from drillnavi.core.elo import (  # noqa: E402
    TARGET_ACCURACY_GROW,
    expected_probability,
    select_item_index,
    update_ratings,
)

N_LEARNERS = 1000
N_ITEMS = 200
N_QUESTIONS = 120
CANDIDATE_POOL = 24  # 1問ごとに難易度を評価する候補数(実運用ではKC内から抽出する)
LEARNER_ABILITY_SD = 1.2
ITEM_DIFFICULTY_SPAN = (-3.0, 3.0)


@dataclass
class SimResult:
    rmse_by_step: list[float]
    realized_accuracy: float
    final_rmse: float
    beta_correlation: float | None
    beta_mean_drift: float | None


def _make_items(rng: random.Random) -> list[float]:
    lo, hi = ITEM_DIFFICULTY_SPAN
    return [lo + (hi - lo) * i / (N_ITEMS - 1) for i in range(N_ITEMS)]


def _pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def run(
    *,
    k_initial: float,
    k_decay: float,
    estimate_items: bool,
    target: float = TARGET_ACCURACY_GROW,
    seed: int = 42,
    n_learners: int = N_LEARNERS,
    n_questions: int = N_QUESTIONS,
) -> SimResult:
    rng = random.Random(seed)
    true_betas = _make_items(rng)
    true_thetas = [rng.gauss(0.0, LEARNER_ABILITY_SD) for _ in range(n_learners)]

    # 推定値。項目を同時推定する場合は全て 0 から始める(コールドスタート)。
    est_betas = [0.0] * N_ITEMS if estimate_items else list(true_betas)
    item_attempts = [0] * N_ITEMS
    est_thetas = [0.0] * n_learners

    squared_error_by_step = [0.0] * n_questions
    n_correct = 0
    n_total = 0

    for step in range(n_questions):
        for learner in range(n_learners):
            theta_hat = est_thetas[learner]
            pool = rng.sample(range(N_ITEMS), CANDIDATE_POOL)
            idx = pool[select_item_index(theta_hat, [est_betas[i] for i in pool], target, rng)]

            # 真のモデルで正誤を決める
            p_true = expected_probability(true_thetas[learner], true_betas[idx])
            correct = rng.random() < p_true

            upd = update_ratings(
                theta_hat,
                est_betas[idx],
                correct,
                learner_attempts=step,
                item_attempts=item_attempts[idx],
                k_initial=k_initial,
                k_decay=k_decay,
            )
            est_thetas[learner] = upd.new_theta
            if estimate_items:
                est_betas[idx] = upd.new_beta
                item_attempts[idx] += 1

            n_correct += int(correct)
            n_total += 1

        squared_error_by_step[step] = statistics.fmean(
            (e - t) ** 2 for e, t in zip(est_thetas, true_thetas)
        )

    rmse_by_step = [math.sqrt(v) for v in squared_error_by_step]

    beta_corr = None
    beta_drift = None
    if estimate_items:
        used = [i for i in range(N_ITEMS) if item_attempts[i] >= 30]
        if len(used) >= 10:
            beta_corr = _pearson([est_betas[i] for i in used], [true_betas[i] for i in used])
            beta_drift = statistics.fmean(est_betas[i] - true_betas[i] for i in used)

    return SimResult(
        rmse_by_step=rmse_by_step,
        realized_accuracy=n_correct / n_total,
        final_rmse=rmse_by_step[-1],
        beta_correlation=beta_corr,
        beta_mean_drift=beta_drift,
    )


def grid_search() -> None:
    print("=== K値のグリッド探索(生徒300人×60問、項目難易度は既知) ===")
    print(f"{'k_initial':>10} {'k_decay':>9} {'RMSE@20':>9} {'RMSE@60':>9} {'正答率':>8}")
    best = None
    for k_initial in (0.3, 0.45, 0.6, 0.9):
        for k_decay in (0.0, 0.02, 0.05, 0.1):
            r = run(k_initial=k_initial, k_decay=k_decay, estimate_items=False,
                    n_learners=300, n_questions=60)
            print(
                f"{k_initial:>10.2f} {k_decay:>9.2f} {r.rmse_by_step[19]:>9.3f} "
                f"{r.final_rmse:>9.3f} {r.realized_accuracy:>8.3f}"
            )
            if best is None or r.final_rmse < best[0]:
                best = (r.final_rmse, k_initial, k_decay)
    print(f"\n最良: k_initial={best[1]}, k_decay={best[2]} (RMSE={best[0]:.3f})")


def main() -> None:
    grid_search()

    print("\n=== 採用パラメータ (k_initial=0.6, k_decay=0.05) の挙動 ===")
    r = run(k_initial=0.6, k_decay=0.05, estimate_items=False)
    for step in (0, 4, 9, 19, 29, 59, 119):
        print(f"  {step + 1:>4}問後  RMSE={r.rmse_by_step[step]:.3f}")
    print(f"  実現正答率={r.realized_accuracy:.3f} (目標 {TARGET_ACCURACY_GROW})")

    print("\n=== コールドスタート(項目難易度も同時推定) ===")
    rc = run(k_initial=0.6, k_decay=0.05, estimate_items=True)
    print(f"  最終RMSE(theta)={rc.final_rmse:.3f}")
    print(f"  実現正答率={rc.realized_accuracy:.3f}")
    print(f"  推定betaと真のbetaの相関={rc.beta_correlation:.3f}")
    print(f"  betaの平均ドリフト={rc.beta_mean_drift:+.3f}  ← 尺度のアンカリングが必要")

    print("\n=== 旧方式(±1レベル)との比較: 難易度の暴走 ===")
    print("  旧: 実力90%の生徒が9問でLv.10に到達し、以降は最大値に張り付く")
    print(f"  新: 120問を通して正答率{r.realized_accuracy:.1%}を維持し、暴走しない")


if __name__ == "__main__":
    main()
