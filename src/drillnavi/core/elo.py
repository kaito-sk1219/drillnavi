"""Elo レーティングによる適応出題のための純関数群。

生徒の1回の解答を「生徒 vs 問題」の1試合とみなし、生徒の能力 theta と
項目の難易度 beta を同時に推定する。両者は同じロジット尺度で表現され、
theta == beta のとき正答確率が 0.5 になる。

このモジュールは I/O・DB・乱数状態を一切持たない純関数のみで構成する。
乱数が必要な関数は random.Random を引数で受け取り、再現性を保証する。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# --- 既定パラメータ -------------------------------------------------------
# いずれも experiments/sim_elo.py のグリッド探索で決定した値。
# 変更する場合は必ずシミュレーションで再検証すること。

DEFAULT_K_INITIAL = 0.75  # 解答数0のときのK値
DEFAULT_K_DECAY = 0.10  # 解答数に対する減衰係数
ITEM_K_SCALE = 0.25  # 項目側のK値は生徒側より小さくする(項目は多数の生徒を見るため)

TARGET_ACCURACY_GROW = 0.75  # growモードの目標正答率
TARGET_ACCURACY_FUN = 0.875  # funモードの目標正答率

MAX_SLOW_DISCOUNT = 0.25  # 「正解したが遅い」ときに正答スコアから引く上限
SLOW_RATIO_FULL_PENALTY = 2.0  # 標準時間の何倍で割引が上限に達するか

THETA_MIN = -6.0
THETA_MAX = 6.0
BETA_MIN = -6.0
BETA_MAX = 6.0

# 確率が厳密に 0.0 / 1.0 に飽和すると「絶対に正解する項目」が生まれ、
# 更新量が 0 になったり対数を取る後段処理が壊れる。境界から必ず離しておく。
PROBABILITY_EPS = 1e-12


@dataclass(frozen=True)
class EloUpdate:
    """1回の解答によるレーティング更新の結果。"""

    new_theta: float
    new_beta: float
    expected: float  # 更新前の予測正答確率
    effective_result: float  # 解答時間補正後のスコア (0.0〜1.0)
    theta_delta: float
    beta_delta: float


def expected_probability(theta: float, beta: float) -> float:
    """能力 theta の生徒が難易度 beta の問題に正答する確率。

    標準ロジスティック関数。theta - beta が大きいほど 1 に近づく。
    引数が極端な値でも math.exp のオーバーフローを起こさないよう、
    符号で場合分けした数値的に安定な形で計算する。戻り値は
    (0.0, 1.0) の開区間に収める。
    """
    diff = theta - beta
    if diff >= 0.0:
        probability = 1.0 / (1.0 + math.exp(-diff))
    else:
        exp_diff = math.exp(diff)
        probability = exp_diff / (1.0 + exp_diff)
    return min(max(probability, PROBABILITY_EPS), 1.0 - PROBABILITY_EPS)


def target_beta(theta: float, target_accuracy: float) -> float:
    """目標正答率をちょうど達成する項目難易度を返す。

    expected_probability(theta, 戻り値) == target_accuracy が成り立つ。
    """
    if not (0.0 < target_accuracy < 1.0):
        raise ValueError("target_accuracy must be in (0, 1)")
    return theta - math.log(target_accuracy / (1.0 - target_accuracy))


def uncertainty_k(
    n_attempts: int,
    *,
    k_initial: float = DEFAULT_K_INITIAL,
    k_decay: float = DEFAULT_K_DECAY,
) -> float:
    """解答数に応じて減衰するK値(学習率)を返す。

    推定値が不確かな初期は大きく動かして速く収束させ、解答数が増えたら
    小さくして安定させる。K = k_initial / (1 + k_decay * n)。
    """
    if n_attempts < 0:
        raise ValueError("n_attempts must be non-negative")
    if k_initial <= 0:
        raise ValueError("k_initial must be positive")
    if k_decay < 0:
        raise ValueError("k_decay must be non-negative")
    return k_initial / (1.0 + k_decay * n_attempts)


def effective_result(
    correct: bool,
    elapsed_ms: int | None = None,
    expected_ms: int | None = None,
    *,
    max_discount: float = MAX_SLOW_DISCOUNT,
    full_penalty_ratio: float = SLOW_RATIO_FULL_PENALTY,
) -> float:
    """正誤と解答時間から、レーティング更新に使うスコアを返す。

    「正解したが標準時間より大幅に遅い」場合は未定着とみなし、正答スコアを
    1.0 から割り引く。標準時間の full_penalty_ratio 倍以上かかると割引は
    max_discount で頭打ちになる。時間情報が無い場合は割引しない。
    不正解は常に 0.0 とする(速い誤答も遅い誤答も等しく不正解として扱う)。
    """
    if not correct:
        return 0.0
    if elapsed_ms is None or expected_ms is None:
        return 1.0
    if elapsed_ms < 0:
        raise ValueError("elapsed_ms must be non-negative")
    if expected_ms <= 0:
        raise ValueError("expected_ms must be positive")
    if full_penalty_ratio <= 1.0:
        raise ValueError("full_penalty_ratio must be > 1.0")

    ratio = elapsed_ms / expected_ms
    if ratio <= 1.0:
        return 1.0
    slowness = min((ratio - 1.0) / (full_penalty_ratio - 1.0), 1.0)
    return 1.0 - max_discount * slowness


def update_ratings(
    theta: float,
    beta: float,
    correct: bool,
    *,
    learner_attempts: int,
    item_attempts: int,
    elapsed_ms: int | None = None,
    expected_ms: int | None = None,
    k_initial: float = DEFAULT_K_INITIAL,
    k_decay: float = DEFAULT_K_DECAY,
    item_k_scale: float = ITEM_K_SCALE,
) -> EloUpdate:
    """1回の解答から生徒の能力と項目の難易度を同時に更新する。

    予測 expected と実績 effective_result の乖離に比例して両者を動かす。
    生徒が予測より良い成績なら theta は上がり beta は下がる(その問題は
    思ったより易しかった)。theta は [THETA_MIN, THETA_MAX] にクランプする。
    """
    expected = expected_probability(theta, beta)
    result = effective_result(correct, elapsed_ms, expected_ms)
    error = result - expected

    k_learner = uncertainty_k(learner_attempts, k_initial=k_initial, k_decay=k_decay)
    k_item = item_k_scale * uncertainty_k(
        item_attempts, k_initial=k_initial, k_decay=k_decay
    )

    new_theta = min(max(theta + k_learner * error, THETA_MIN), THETA_MAX)
    new_beta = min(max(beta - k_item * error, BETA_MIN), BETA_MAX)

    return EloUpdate(
        new_theta=new_theta,
        new_beta=new_beta,
        expected=expected,
        effective_result=result,
        theta_delta=new_theta - theta,
        beta_delta=new_beta - beta,
    )


def selection_weight(
    theta: float,
    beta: float,
    target_accuracy: float,
    *,
    tolerance: float = 0.1,
) -> float:
    """項目の出題されやすさを返す。目標正答率に近いほど大きい。

    予測正答率と目標正答率の差に対するガウスカーネル。tolerance は
    許容する差の目安で、小さいほど選択が目標に集中する。
    """
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    diff = expected_probability(theta, beta) - target_accuracy
    return math.exp(-((diff / tolerance) ** 2))


def select_item_index(
    theta: float,
    betas: Sequence[float],
    target_accuracy: float,
    rng: "RandomLike",
    *,
    tolerance: float = 0.1,
) -> int:
    """候補項目から1つを重み付きランダムで選び、そのインデックスを返す。

    最も目標に近い項目を決定論的に選ぶと同種の問題ばかりが続いて飽きるため、
    目標周辺から確率的に選ぶ。rng は random.Random 互換のオブジェクト。
    """
    if not betas:
        raise ValueError("betas must not be empty")

    weights = [
        selection_weight(theta, beta, target_accuracy, tolerance=tolerance)
        for beta in betas
    ]
    total = sum(weights)
    if total <= 0.0:
        # 全候補が目標から極端に外れている場合は最も近いものを返す
        return min(
            range(len(betas)),
            key=lambda i: abs(expected_probability(theta, betas[i]) - target_accuracy),
        )

    threshold = rng.random() * total
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if cumulative >= threshold:
            return index
    return len(betas) - 1


def initial_theta_for_grade(grade: int, *, reference_grade: int = 4) -> float:
    """学年から theta の初期値を推定する。

    項目難易度はその学年の標準的な生徒が 0 付近になるよう較正する前提で、
    学年が1つ上がるごとに 0.8 ロジット分の事前分布を置く。完全な当て推量を
    避け、初回セッションから妥当な難易度を出すための措置。
    """
    if grade <= 0:
        raise ValueError("grade must be positive")
    return 0.8 * (grade - reference_grade)


class RandomLike:
    """random.Random 互換の最小インタフェース(型注釈用)。"""

    def random(self) -> float:  # pragma: no cover - 型注釈専用
        raise NotImplementedError
