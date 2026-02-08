"""Thematic future maps — the 9 domains being tracked."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

CANONICAL_THEMES = [
    "ai_foundation_models",
    "ai_applications",
    "ai_supply_chain",
    "robotics",
    "geopolitics",
    "energy",
    "demographics",
    "capital_markets",
    "health_longevity",
]

THEME_DISPLAY_NAMES = {
    "ai_foundation_models": "AI Foundation Models",
    "ai_applications": "AI Applications",
    "ai_supply_chain": "AI Supply Chain",
    "robotics": "Robotics",
    "geopolitics": "Geopolitics",
    "energy": "Energy",
    "demographics": "Demographics",
    "capital_markets": "Capital Markets",
    "health_longevity": "Health & Longevity",
}


@dataclass
class Theme:
    name: str = ""
    display_name: str = ""
    key_questions: list[str] = field(default_factory=list)
    current_assessment: str = ""
    scenario_node_ids: list[str] = field(default_factory=list)
    watch_sources: list[str] = field(default_factory=list)
    family_implications: list[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "key_questions": self.key_questions,
            "current_assessment": self.current_assessment,
            "scenario_node_ids": self.scenario_node_ids,
            "watch_sources": self.watch_sources,
            "family_implications": self.family_implications,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Theme:
        return cls(
            name=d.get("name", ""),
            display_name=d.get("display_name", ""),
            key_questions=d.get("key_questions", []),
            current_assessment=d.get("current_assessment", ""),
            scenario_node_ids=d.get("scenario_node_ids", []),
            watch_sources=d.get("watch_sources", []),
            family_implications=d.get("family_implications", []),
            last_updated=d.get("last_updated", ""),
        )


@dataclass
class ThematicMap:
    themes: list[Theme] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"themes": [t.to_dict() for t in self.themes]}
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    @classmethod
    def load(cls, path: Path) -> ThematicMap:
        data = yaml.safe_load(path.read_text())
        themes = [Theme.from_dict(t) for t in data.get("themes", [])]
        return cls(themes=themes)

    def get_theme(self, name: str) -> Theme | None:
        for t in self.themes:
            if t.name == name:
                return t
        return None

    def stale_themes(self, max_age_days: int = 14) -> list[Theme]:
        cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).date().isoformat()
        return [t for t in self.themes if t.last_updated < cutoff]
