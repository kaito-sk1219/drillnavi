"""core/elo.py のユニットテスト。"""

from __future__ import annotations

import math
import random

import pytest

from drillnavi.core.elo import (
    BETA_MAX,
    BETA_MIN,
    THETA_MAX,
    THETA_MIN,
    EloUpdate,
    effective_result,
    expected_probability,
    initial_theta_for_grade,
    select_item_index,
    selection_weight,
    target_beta,
    uncertainty_k,
    update_ratings,
)


class TestExpectedProbability:
    def test_equal_ratings_give_half(self) -> None:
        assert expected_probability(0.0, 0.0) == pytest.approx(0.5)
        assert expected_probability(2.5, 2.5) == pytest.approx(0.5)

    def test_stronger_learner_is_more_likely_to_be_correct(self) -> None:
        assert expected_probability(1.0, 0.0) > 0.5
        assert expected_probability(-1.0, 0.0) < 0.5

    def test_monotonic_in_theta(self) -> None:
        values = [expected_probability(t / 10, 0.0) for t in range(-30, 31)]
        assert all(a < b for a, b in zip(values, values[1:]))

    def test_bounded(self) -> None:
        """極端な入力でも開区間 (0, 1) に収まり、例外を出さない。"""
        assert 0.0 < expected_probability(-20.0, 20.0) < 1.0
        assert 0.0 < expected_probability(20.0, -20.0) < 1.0

    def test_extreme_inputs_do_not_overflow(self) -> None:
        """math.exp のオーバーフローで落ちないこと(回帰テスト)。"""
        assert 0.0 < expected_probability(-1e5, 1e5) < 1.0
        assert 0.0 < expected_probability(1e5, -1e5) < 1.0


class TestTargetBeta:
    @pytest.mark.parametrize("target", [0.5, 0.6, 0.75, 0.9])
    def test_roundtrip(self, target: float) -> None:
        """target_beta が返す難易度では、予測正答率がちょうど目標になる。"""
        beta = target_beta(1.3, target)
        assert expected_probability(1.3, beta) == pytest.approx(target)

    def test_harder_target_means_harder_item(self) -> None:
        """目標正答率が低いほど、選ぶべき項目は難しい(betaが大きい)。"""
        assert target_beta(0.0, 0.5) > target_beta(0.0, 0.75)

    @pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
    def test_rejects_out_of_range(self, bad: float) -> None:
        with pytest.raises(ValueError):
            target_beta(0.0, bad)


class TestUncertaintyK:
    def test_decreases_with_attempts(self) -> None:
        ks = [uncertainty_k(n) for n in (0, 10, 50, 200, 1000)]
        assert all(a > b for a, b in zip(ks, ks[1:]))

    def test_initial_value(self) -> None:
        assert uncertainty_k(0, k_initial=0.75) == pytest.approx(0.75)

    def test_no_decay_keeps_k_constant(self) -> None:
        assert uncertainty_k(500, k_initial=0.5, k_decay=0.0) == pytest.approx(0.5)

    def test_stays_positive(self) -> None:
        assert uncertainty_k(10**6) > 0.0

    def test_rejects_negative_attempts(self) -> None:
        with pytest.raises(ValueError):
            uncertainty_k(-1)


class TestEffectiveResult:
    def test_incorrect_is_zero_regardless_of_time(self) -> None:
        assert effective_result(False) == 0.0
        assert effective_result(False, 100, 10_000) == 0.0

    def test_correct_without_timing_is_full(self) -> None:
        assert effective_result(True) == 1.0

    def test_fast_correct_is_full(self) -> None:
        assert effective_result(True, 5_000, 10_000) == 1.0

    def test_slow_correct_is_discounted(self) -> None:
        """標準時間の1.5倍なら割引は上限の半分。"""
        assert effective_result(True, 15_000, 10_000) == pytest.approx(0.875)

    def test_discount_is_capped(self) -> None:
        """どれだけ遅くても割引は上限で頭打ちになる。"""
        assert effective_result(True, 20_000, 10_000) == pytest.approx(0.75)
        assert effective_result(True, 10**7, 10_000) == pytest.approx(0.75)

    def test_monotonic_in_elapsed(self) -> None:
        values = [effective_result(True, ms, 10_000) for ms in range(1_000, 30_000, 1_000)]
        assert all(a >= b for a, b in zip(values, values[1:]))

    def test_rejects_invalid_expected_ms(self) -> None:
        with pytest.raises(ValueError):
            effective_result(True, 1_000, 0)


class TestUpdateRatings:
    def _update(self, theta: float, beta: float, correct: bool, **kw) -> EloUpdate:
        params = {"learner_attempts": 0, "item_attempts": 0}
        params.update(kw)
        return update_ratings(theta, beta, correct, **params)  # type: ignore[arg-type]

    def test_correct_answer_raises_theta_and_lowers_beta(self) -> None:
        upd = self._update(0.0, 0.0, True)
        assert upd.theta_delta > 0
        assert upd.beta_delta < 0

    def test_incorrect_answer_lowers_theta_and_raises_beta(self) -> None:
        upd = self._update(0.0, 0.0, False)
        assert upd.theta_delta < 0
        assert upd.beta_delta > 0

    def test_surprising_result_moves_more_than_expected_one(self) -> None:
        """予測外の結果ほど大きく動く。Elo の中核的性質。"""
        expected_win = self._update(3.0, -3.0, True)  # ほぼ確実な正解
        surprise_win = self._update(-3.0, 3.0, True)  # 番狂わせの正解
        assert surprise_win.theta_delta > expected_win.theta_delta

    def test_experienced_learner_moves_less(self) -> None:
        """解答数が多い生徒ほど1問あたりの変動が小さい。"""
        novice = self._update(0.0, 0.0, True, learner_attempts=0)
        veteran = self._update(0.0, 0.0, True, learner_attempts=500)
        assert abs(veteran.theta_delta) < abs(novice.theta_delta)

    def test_item_moves_less_than_learner(self) -> None:
        """項目難易度は生徒能力より緩やかに動く。"""
        upd = self._update(0.0, 0.0, True)
        assert abs(upd.beta_delta) < abs(upd.theta_delta)

    def test_slow_correct_gains_less(self) -> None:
        fast = self._update(0.0, 0.0, True, elapsed_ms=5_000, expected_ms=10_000)
        slow = self._update(0.0, 0.0, True, elapsed_ms=30_000, expected_ms=10_000)
        assert slow.theta_delta < fast.theta_delta
        assert slow.theta_delta > 0  # 正解である以上は上がる

    def test_theta_is_clamped(self) -> None:
        assert self._update(THETA_MAX, -5.0, True).new_theta <= THETA_MAX
        assert self._update(THETA_MIN, 5.0, False).new_theta >= THETA_MIN

    def test_beta_is_clamped(self) -> None:
        assert self._update(5.0, BETA_MIN, False).new_beta >= BETA_MIN
        assert self._update(-5.0, BETA_MAX, True).new_beta <= BETA_MAX

    def test_expected_matches_standalone_function(self) -> None:
        upd = self._update(0.7, -0.3, True)
        assert upd.expected == pytest.approx(expected_probability(0.7, -0.3))

    def test_converges_toward_true_ability(self) -> None:
        """真の能力1.5の生徒を難易度0の項目で繰り返し評価すると1.5付近に収束する。"""
        true_theta = 1.5
        rng = random.Random(0)
        theta = 0.0
        for n in range(600):
            p = expected_probability(true_theta, 0.0)
            correct = rng.random() < p
            theta = update_ratings(
                theta, 0.0, correct, learner_attempts=n, item_attempts=10**6
            ).new_theta
        assert theta == pytest.approx(true_theta, abs=0.4)


class TestSelectionWeight:
    def test_peaks_at_target(self) -> None:
        theta = 0.5
        best = target_beta(theta, 0.75)
        assert selection_weight(theta, best, 0.75) == pytest.approx(1.0)

    def test_decreases_with_distance_from_target(self) -> None:
        theta = 0.0
        best = target_beta(theta, 0.75)
        assert selection_weight(theta, best + 1.0, 0.75) < selection_weight(theta, best, 0.75)
        assert selection_weight(theta, best - 1.0, 0.75) < selection_weight(theta, best, 0.75)

    def test_rejects_non_positive_tolerance(self) -> None:
        with pytest.raises(ValueError):
            selection_weight(0.0, 0.0, 0.75, tolerance=0.0)


class TestSelectItemIndex:
    def test_returns_valid_index(self) -> None:
        rng = random.Random(0)
        betas = [-2.0, -1.0, 0.0, 1.0, 2.0]
        for _ in range(50):
            assert 0 <= select_item_index(0.0, betas, 0.75, rng) < len(betas)

    def test_rejects_empty_candidates(self) -> None:
        with pytest.raises(ValueError):
            select_item_index(0.0, [], 0.75, random.Random(0))

    def test_favours_items_near_target(self) -> None:
        """目標正答率に近い項目が最も多く選ばれる。"""
        rng = random.Random(1)
        theta = 0.0
        betas = [-3.0, target_beta(theta, 0.75), 3.0]
        counts = [0, 0, 0]
        for _ in range(2_000):
            counts[select_item_index(theta, betas, 0.75, rng)] += 1
        assert counts[1] == max(counts)

    def test_is_not_deterministic(self) -> None:
        """飽き防止のため、常に同じ項目を返してはいけない。"""
        rng = random.Random(2)
        theta = 0.0
        betas = [target_beta(theta, p) for p in (0.70, 0.75, 0.80)]
        chosen = {select_item_index(theta, betas, 0.75, rng) for _ in range(200)}
        assert len(chosen) > 1

    def test_falls_back_when_all_weights_underflow(self) -> None:
        """全候補が目標から極端に外れても例外を出さず最も近いものを返す。"""
        rng = random.Random(3)
        betas = [50.0, 60.0]
        assert select_item_index(0.0, betas, 0.75, rng) == 0

    def test_reproducible_with_same_seed(self) -> None:
        betas = [-1.0, 0.0, 1.0, 2.0]
        a = [select_item_index(0.0, betas, 0.75, random.Random(7)) for _ in range(5)]
        b = [select_item_index(0.0, betas, 0.75, random.Random(7)) for _ in range(5)]
        assert a == b


class TestInitialThetaForGrade:
    def test_reference_grade_is_zero(self) -> None:
        assert initial_theta_for_grade(4) == pytest.approx(0.0)

    def test_increases_with_grade(self) -> None:
        values = [initial_theta_for_grade(g) for g in range(1, 10)]
        assert all(a < b for a, b in zip(values, values[1:]))

    def test_rejects_invalid_grade(self) -> None:
        with pytest.raises(ValueError):
            initial_theta_for_grade(0)
