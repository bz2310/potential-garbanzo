"""Belief delta log — append-only record of every probability change.

Every entry has a mandatory reason.  This is the intellectual audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class BeliefDelta:
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )
    node_id: str = ""
    node_label: str = ""
    tree_name: str = ""
    old_probability: float = 0.0
    new_probability: float = 0.0
    reason: str = ""
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    sibling_adjustments: list[dict] = field(default_factory=list)

    @property
    def delta(self) -> float:
        return self.new_probability - self.old_probability

    @property
    def direction(self) -> str:
        if self.delta > 0:
            return "UP"
        elif self.delta < 0:
            return "DOWN"
        return "UNCHANGED"

    @property
    def arrow(self) -> str:
        if self.delta > 0:
            return "\u25b2"
        elif self.delta < 0:
            return "\u25bc"
        return "="

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "node_label": self.node_label,
            "tree_name": self.tree_name,
            "old_probability": self.old_probability,
            "new_probability": self.new_probability,
            "delta": round(self.delta, 4),
            "direction": self.direction,
            "reason": self.reason,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "sibling_adjustments": self.sibling_adjustments,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BeliefDelta:
        return cls(
            timestamp=d.get("timestamp", ""),
            node_id=d.get("node_id", ""),
            node_label=d.get("node_label", ""),
            tree_name=d.get("tree_name", ""),
            old_probability=d.get("old_probability", 0.0),
            new_probability=d.get("new_probability", 0.0),
            reason=d.get("reason", ""),
            source_url=d.get("source_url"),
            source_title=d.get("source_title"),
            sibling_adjustments=d.get("sibling_adjustments", []),
        )

    def summary_line(self) -> str:
        return (
            f"[{self.timestamp}] {self.tree_name}/{self.node_label} "
            f"{self.old_probability:.0%} {self.arrow} {self.new_probability:.0%} "
            f"({self.delta:+.0%}) \u2014 {self.reason}"
        )


@dataclass
class BeliefLog:
    path: Path = field(default_factory=lambda: Path("beliefs/log.yaml"))
    entries: list[BeliefDelta] = field(default_factory=list)

    def load(self) -> None:
        if self.path.exists():
            data = yaml.safe_load(self.path.read_text()) or []
            self.entries = [BeliefDelta.from_dict(d) for d in data]

    def append(self, delta: BeliefDelta) -> None:
        if not delta.reason:
            raise ValueError("BeliefDelta.reason is required.")
        self.entries.append(delta)
        self._persist()

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self.entries]
        self.path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def recent(self, days: int = 7) -> list[BeliefDelta]:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat(timespec="seconds")
        return [e for e in self.entries if e.timestamp >= cutoff]

    def by_node(self, node_id: str) -> list[BeliefDelta]:
        return [e for e in self.entries if e.node_id == node_id]

    def by_tree(self, tree_name: str) -> list[BeliefDelta]:
        return [e for e in self.entries if e.tree_name == tree_name]

    def biggest_moves(self, n: int = 10) -> list[BeliefDelta]:
        return sorted(self.entries, key=lambda e: abs(e.delta), reverse=True)[:n]
