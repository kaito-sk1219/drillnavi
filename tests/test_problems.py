import pytest

from drillnavi.core.problems import generate_problem, generate_problems


def test_same_level_and_seed_is_deterministic() -> None:
    p1 = generate_problem(level=5, seed=42)
    p2 = generate_problem(level=5, seed=42)
    assert p1 == p2


def test_low_level_only_uses_addition_and_subtraction() -> None:
    for seed in range(50):
        problem = generate_problem(level=1, seed=seed)
        assert problem.operator in ("+", "-")


def test_mid_level_adds_multiplication() -> None:
    operators = {generate_problem(level=5, seed=seed).operator for seed in range(50)}
    assert operators <= {"+", "-", "*"}
    assert "*" in operators


def test_high_level_adds_division() -> None:
    operators = {generate_problem(level=9, seed=seed).operator for seed in range(50)}
    assert "/" in operators


def test_subtraction_never_negative() -> None:
    for seed in range(200):
        problem = generate_problem(level=2, seed=seed)
        if problem.operator == "-":
            assert problem.answer >= 0
            assert problem.left >= problem.right


def test_division_is_always_exact() -> None:
    for seed in range(200):
        problem = generate_problem(level=10, seed=seed)
        if problem.operator == "/":
            assert problem.right * problem.answer == problem.left


def test_answer_matches_operator() -> None:
    for seed in range(200):
        problem = generate_problem(level=7, seed=seed)
        if problem.operator == "+":
            assert problem.answer == problem.left + problem.right
        elif problem.operator == "-":
            assert problem.answer == problem.left - problem.right
        elif problem.operator == "*":
            assert problem.answer == problem.left * problem.right


@pytest.mark.parametrize("level", [0, 11])
def test_level_out_of_range_raises(level: int) -> None:
    with pytest.raises(ValueError):
        generate_problem(level=level, seed=1)


def test_generate_problems_count_zero_returns_empty_list() -> None:
    assert generate_problems(level=5, count=0, seed=1) == []


def test_generate_problems_returns_requested_count() -> None:
    problems = generate_problems(level=5, count=10, seed=1)
    assert len(problems) == 10


def test_generate_problems_negative_count_raises() -> None:
    with pytest.raises(ValueError):
        generate_problems(level=5, count=-1, seed=1)


def test_prompt_property_formats_expression() -> None:
    problem = generate_problem(level=1, seed=1)
    assert problem.prompt == f"{problem.left} {problem.operator} {problem.right}"
