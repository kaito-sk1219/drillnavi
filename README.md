# drillnavi

[![CI](https://github.com/kaito-sk1219/drillnavi/actions/workflows/ci.yml/badge.svg)](https://github.com/kaito-sk1219/drillnavi/actions/workflows/ci.yml)

算数の反復学習を管理するCLIツールです。ページ数と締切から日割りノルマを計算し、四則演算のドリルを対話形式で出題、学習履歴をグラフ付きレポートにまとめます。

## インストール

```bash
uv tool install git+https://github.com/kaito-sk1219/drillnavi.git
```

または開発用にクローンして実行:

```bash
git clone https://github.com/kaito-sk1219/drillnavi.git
cd drillnavi
uv sync
```

## 最短の使い方

データは `~/.drillnavi/data.json` に保存されます。

### 学習計画を登録する(残日数から日割りノルマを自動計算)

```
$ uv run drillnavi plan add --name たろう --subject 算数 --pages 60 --due 2026-08-31
たろう さんの「算数」計画を登録しました。
締切: 2026-08-31 / 残り22日
1日あたりのノルマ: 3ページ
```

### 今日やる分を確認する

```
$ uv run drillnavi plan today --name たろう
たろう さんの今日のノルマ:
  [算数] 3ページ
```

### ドリルを出題する(grow: 直近の正答率70%を目標に難易度を自動調整)

```
$ uv run drillnavi drill --name たろう --mode grow --count 5
[1/5] Lv.3
18 + 12 = : 30
正解!
難易度アップ! Lv.4
```

正答率が70%を下回ると「難易度ダウン!」と表示され、逆に問題を間違えると
「不正解… 正解は◯◯でした。」のように正誤が都度フィードバックされます。

### ドリルを出題する(fun: 易しめの問題中心でコンボと称号を表示)

```
$ uv run drillnavi drill --name たろう --mode fun --count 4
[1/4]
11 - 8 = : 4
不正解… 正解は 3 でした。コンボが途切れました。
[2/4]
8 - 4 = : 4
正解! コンボ 1 「はじめの一歩」
```

コンボ数に応じて称号が変化していきます(例: 3コンボで「がんばり屋」)。

### 学習履歴のレポートをPDF出力する

```
$ uv run drillnavi report --name たろう
レポートを出力しました: /home/taro/.drillnavi/report_たろう.pdf
```

## 開発環境構築

[uv](https://docs.astral.sh/uv/) を使用します。

```bash
uv sync
```

## テスト実行

```bash
uv run pytest
```
