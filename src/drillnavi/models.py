"""永続化するデータのモデル定義。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

Mode = Literal["grow", "fun"]


@dataclass
class Plan:
    """1件の学習計画(教科ごとのページ配分)。"""

    subject: str
    total_pages: int
    due: date
    created_at: date

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "total_pages": self.total_pages,
            "due": self.due.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Plan":
        return Plan(
            subject=str(data["subject"]),
            total_pages=int(data["total_pages"]),
            due=date.fromisoformat(str(data["due"])),
            created_at=date.fromisoformat(str(data["created_at"])),
        )


@dataclass
class DrillRecord:
    """ドリル1問分の解答履歴。"""

    timestamp: datetime
    mode: Mode
    level: int
    operator: str
    correct: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "mode": self.mode,
            "level": self.level,
            "operator": self.operator,
            "correct": self.correct,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DrillRecord":
        mode = str(data["mode"])
        if mode not in ("grow", "fun"):
            raise ValueError(f"invalid mode: {mode}")
        return DrillRecord(
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
            mode=mode,  # type: ignore[arg-type]
            level=int(data["level"]),
            operator=str(data["operator"]),
            correct=bool(data["correct"]),
        )


@dataclass
class ChildData:
    """児童1人分のデータ(学習計画とドリル履歴)。"""

    name: str
    plans: list[Plan] = field(default_factory=list)
    drill_history: list[DrillRecord] = field(default_factory=list)
    grow_level: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "plans": [plan.to_dict() for plan in self.plans],
            "drill_history": [record.to_dict() for record in self.drill_history],
            "grow_level": self.grow_level,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ChildData":
        return ChildData(
            name=str(data["name"]),
            plans=[Plan.from_dict(p) for p in data.get("plans", [])],
            drill_history=[
                DrillRecord.from_dict(r) for r in data.get("drill_history", [])
            ],
            grow_level=int(data.get("grow_level", 1)),
        )


@dataclass
class AppData:
    """data.json のルート構造。児童名をキーに管理する。"""

    children: dict[str, ChildData] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"children": {name: child.to_dict() for name, child in self.children.items()}}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppData":
        children_raw: dict[str, Any] = data.get("children", {})
        return AppData(
            children={name: ChildData.from_dict(c) for name, c in children_raw.items()}
        )
