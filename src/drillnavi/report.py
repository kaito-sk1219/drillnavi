"""ドリル履歴の集計と進捗グラフPDFの出力。"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from drillnavi.models import ChildData  # noqa: E402

DEFAULT_REPORT_DIR = Path.home() / ".drillnavi"

# 日本語グリフ欠落を避けるため、環境にあるフォントを優先順に試す。
# いずれも無い環境では DejaVu Sans にフォールバックする。
plt.rcParams["font.family"] = [
    "Noto Sans JP",
    "Yu Gothic",
    "Meiryo",
    "MS Gothic",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def drill_history_to_dataframe(child: ChildData) -> pd.DataFrame:
    """ドリル履歴を集計しやすい pandas.DataFrame に変換する。"""
    columns = ["timestamp", "date", "mode", "level", "operator", "correct"]
    records = [
        {
            "timestamp": record.timestamp,
            "date": record.timestamp.date(),
            "mode": record.mode,
            "level": record.level,
            "operator": record.operator,
            "correct": record.correct,
        }
        for record in child.drill_history
    ]
    return pd.DataFrame.from_records(records, columns=columns)


def summarize_daily(df: pd.DataFrame) -> pd.DataFrame:
    """日付ごとの出題数・正答率・平均難易度を集計する。"""
    if df.empty:
        return pd.DataFrame(columns=["date", "attempts", "accuracy", "avg_level"])
    grouped = df.groupby("date").agg(
        attempts=("correct", "count"),
        accuracy=("correct", "mean"),
        avg_level=("level", "mean"),
    )
    return grouped.reset_index()


def generate_report_pdf(child: ChildData, output_path: Path) -> Path:
    """児童1人分の進捗グラフをPDFに出力し、出力先パスを返す。"""
    df = drill_history_to_dataframe(child)
    daily = summarize_daily(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_path) as pdf:
        fig, axes = plt.subplots(2, 1, figsize=(8, 10))
        fig.suptitle(f"{child.name} さんの学習レポート")

        if daily.empty:
            for ax in axes:
                ax.axis("off")
            axes[0].text(0.5, 0.5, "ドリル履歴がありません", ha="center", va="center")
        else:
            axes[0].plot(daily["date"], daily["accuracy"] * 100, marker="o")
            axes[0].set_title("日別正答率")
            axes[0].set_ylabel("正答率 (%)")
            axes[0].set_ylim(0, 100)
            axes[0].tick_params(axis="x", rotation=45)

            axes[1].bar(daily["date"].astype(str), daily["attempts"])
            axes[1].set_title("日別出題数")
            axes[1].set_ylabel("問題数")
            axes[1].tick_params(axis="x", rotation=45)

        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
        pdf.savefig(fig)
        plt.close(fig)

    return output_path
