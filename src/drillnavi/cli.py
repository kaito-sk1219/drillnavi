"""drillnavi の CLI エントリポイント。"""

from __future__ import annotations

from datetime import date

import typer

from drillnavi import storage
from drillnavi.core.planning import calculate_daily_quota
from drillnavi.models import Plan

app = typer.Typer(help="drillnavi: 算数の反復学習を管理するCLI")
plan_app = typer.Typer(help="学習計画(ページ配分)の管理")
app.add_typer(plan_app, name="plan")


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
