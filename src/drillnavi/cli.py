"""drillnavi の CLI エントリポイント。"""

from __future__ import annotations

import random
from datetime import date, datetime
from enum import Enum

import typer

from drillnavi import storage
from drillnavi.core.combo import title_for_combo, update_combo
from drillnavi.core.difficulty import adjust_difficulty
from drillnavi.core.planning import calculate_daily_quota
from drillnavi.core.problems import generate_problem
from drillnavi.models import ChildData, DrillRecord, Plan
from drillnavi.report import DEFAULT_REPORT_DIR, generate_report_pdf

app = typer.Typer(help="drillnavi: 算数の反復学習を管理するCLI")
plan_app = typer.Typer(help="学習計画(ページ配分)の管理")
app.add_typer(plan_app, name="plan")

FUN_MODE_LEVEL = 2  # fun モードは易しめの問題を中心に出題する


class DrillMode(str, Enum):
    grow = "grow"
    fun = "fun"


@plan_app.command("add")
def plan_add(
    name: str = typer.Option(..., "--name", help="児童名"),
    subject: str = typer.Option(..., "--subject", help="教科"),
    pages: int = typer.Option(..., "--pages", help="総ページ数"),
    due: str = typer.Option(..., "--due", help="締切日 (YYYY-MM-DD)"),
) -> None:
    """学習計画を登録し、日割りノルマを表示する。"""
    try:
        due_date = date.fromisoformat(due)
    except ValueError:
        typer.echo(f"締切日の形式が不正です(YYYY-MM-DDで指定してください): {due}", err=True)
        raise typer.Exit(code=1) from None

    today = date.today()
    data = storage.load_data()
    child = storage.get_or_create_child(data, name)
    child.plans.append(
        Plan(subject=subject, total_pages=pages, due=due_date, created_at=today)
    )
    storage.save_data(data)

    quota = calculate_daily_quota(
        total_pages=pages, completed_pages=0, due=due_date, today=today
    )
    typer.echo(f"{name} さんの「{subject}」計画を登録しました。")
    typer.echo(f"締切: {due_date.isoformat()} / 残り{quota.remaining_days}日")
    typer.echo(f"1日あたりのノルマ: {quota.pages_per_day}ページ")
    if quota.is_overdue:
        typer.echo("締切日を過ぎています。今日中にまとめて進めましょう。")


@plan_app.command("today")
def plan_today(
    name: str = typer.Option(..., "--name", help="児童名"),
) -> None:
    """今日やる分(日割りノルマ)を教科ごとに表示する。"""
    data = storage.load_data()
    child = data.children.get(name)
    if child is None or not child.plans:
        typer.echo(f"{name} さんの学習計画が登録されていません。")
        raise typer.Exit(code=1)

    today = date.today()
    typer.echo(f"{name} さんの今日のノルマ:")
    for plan in child.plans:
        quota = calculate_daily_quota(
            total_pages=plan.total_pages,
            completed_pages=0,
            due=plan.due,
            today=today,
        )
        note = " (締切超過)" if quota.is_overdue else ""
        typer.echo(f"  [{plan.subject}] {quota.pages_per_day}ページ{note}")


@app.command()
def drill(
    name: str = typer.Option(..., "--name", help="児童名"),
    mode: DrillMode = typer.Option(..., "--mode", help="grow または fun"),
    count: int = typer.Option(10, "--count", help="出題数"),
) -> None:
    """算数の四則演算問題を対話形式で出題する。"""
    data = storage.load_data()
    child = storage.get_or_create_child(data, name)

    if mode is DrillMode.grow:
        _run_grow_session(child, count)
    else:
        _run_fun_session(child, count)

    storage.save_data(data)


def _prompt_answer(problem_prompt: str) -> int | None:
    answer_text = typer.prompt(f"{problem_prompt} = ")
    try:
        return int(answer_text)
    except ValueError:
        return None


def _run_grow_session(child: ChildData, count: int) -> None:
    typer.echo(f"{child.name} さんの growモード ドリルを始めます(全{count}問、目標正答率70%)。")
    for i in range(count):
        level = child.grow_level
        problem = generate_problem(level, seed=random.randint(0, 2**31 - 1))
        typer.echo(f"[{i + 1}/{count}] Lv.{level}")
        answer = _prompt_answer(problem.prompt)
        correct = answer == problem.answer

        if correct:
            typer.echo("正解!")
        else:
            typer.echo(f"不正解… 正解は {problem.answer} でした。")

        child.drill_history.append(
            DrillRecord(
                timestamp=datetime.now(),
                mode="grow",
                level=level,
                operator=problem.operator,
                correct=correct,
            )
        )

        recent_results = [
            record.correct for record in child.drill_history if record.mode == "grow"
        ][-10:]
        adjustment = adjust_difficulty(current_level=level, recent_results=recent_results)
        if adjustment.new_level != level:
            child.grow_level = adjustment.new_level
            arrow = "アップ" if adjustment.direction == "up" else "ダウン"
            typer.echo(f"難易度{arrow}! Lv.{adjustment.new_level}")

    typer.echo("お疲れさまでした!")


def _run_fun_session(child: ChildData, count: int) -> None:
    typer.echo(f"{child.name} さんの funモード ドリルを始めます(全{count}問)。")
    combo = 0
    title = title_for_combo(combo)
    for i in range(count):
        problem = generate_problem(FUN_MODE_LEVEL, seed=random.randint(0, 2**31 - 1))
        typer.echo(f"[{i + 1}/{count}]")
        answer = _prompt_answer(problem.prompt)
        correct = answer == problem.answer
        combo = update_combo(combo, correct)
        title = title_for_combo(combo)

        if correct:
            typer.echo(f"正解! コンボ {combo} 「{title}」")
        else:
            typer.echo(f"不正解… 正解は {problem.answer} でした。コンボが途切れました。")

        child.drill_history.append(
            DrillRecord(
                timestamp=datetime.now(),
                mode="fun",
                level=FUN_MODE_LEVEL,
                operator=problem.operator,
                correct=correct,
            )
        )

    typer.echo(f"お疲れさまでした! 最終コンボ {combo} 「{title}」")


@app.command()
def report(
    name: str = typer.Option(..., "--name", help="児童名"),
) -> None:
    """学習履歴を集計し、進捗グラフ付きレポートをPDFで出力する。"""
    data = storage.load_data()
    child = data.children.get(name)
    if child is None or not child.drill_history:
        typer.echo(f"{name} さんのドリル履歴がありません。")
        raise typer.Exit(code=1)

    output_path = DEFAULT_REPORT_DIR / f"report_{name}.pdf"
    generate_report_pdf(child, output_path)
    typer.echo(f"レポートを出力しました: {output_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
