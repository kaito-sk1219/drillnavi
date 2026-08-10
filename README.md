# drillnavi

[![CI](https://github.com/kaito-sk1219/prog-assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/kaito-sk1219/prog-assignment/actions/workflows/ci.yml)

算数の反復学習を管理するCLIツールです。ページ数と締切から日割りノルマを計算し、四則演算のドリルを対話形式で出題、学習履歴をグラフ付きレポートにまとめます。

## インストール

```bash
uv tool install drillnavi
```

または開発用にクローンして実行:

```bash
git clone https://github.com/kaito-sk1219/prog-assignment.git drillnavi
cd drillnavi
uv sync
```

## 最短の使い方

```bash
# 学習計画を登録(残日数から日割りノルマを自動計算)
uv run drillnavi plan add --name たろう --subject 算数 --pages 60 --due 2026-08-31

# 今日やる分を確認
uv run drillnavi plan today --name たろう

# ドリルを出題(grow: 正答率70%を目標に難易度が自動調整 / fun: コンボと称号を表示)
uv run drillnavi drill --name たろう --mode grow

# 学習履歴のグラフ付きレポートをPDF出力
uv run drillnavi report --name たろう
```

データは `~/.drillnavi/data.json` に保存されます。

## 開発環境構築

[uv](https://docs.astral.sh/uv/) を使用します。

```bash
uv sync
```

## テスト実行

```bash
uv run pytest
```
