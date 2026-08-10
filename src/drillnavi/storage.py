"""~/.drillnavi/data.json への永続化を担当する層。"""

from __future__ import annotations

import json
from pathlib import Path

from drillnavi.models import AppData, ChildData

DEFAULT_DATA_DIR = Path.home() / ".drillnavi"
DEFAULT_DATA_FILE = DEFAULT_DATA_DIR / "data.json"


def load_data(path: Path = DEFAULT_DATA_FILE) -> AppData:
    """data.json を読み込む。存在しない場合は空のデータを返す。"""
    if not path.exists():
        return AppData()
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return AppData.from_dict(raw)


def save_data(data: AppData, path: Path = DEFAULT_DATA_FILE) -> None:
    """data.json へ書き込む。親ディレクトリが無ければ作成する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)


def get_or_create_child(data: AppData, name: str) -> ChildData:
    """名前に対応する児童データを取得する。存在しなければ新規作成して登録する。"""
    if name not in data.children:
        data.children[name] = ChildData(name=name)
    return data.children[name]
