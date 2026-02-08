"""Source and Claim — ingested articles and their extracted assertions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Claim:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    text: str = ""
    theme: str = ""
    relevance: str = ""
    node_id: Optional[str] = None
    confidence: str = ""
    significance: int = 1  # 1-5
    actionable: bool = False
    action_suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "theme": self.theme,
            "relevance": self.relevance,
            "node_id": self.node_id,
            "confidence": self.confidence,
            "significance": self.significance,
            "actionable": self.actionable,
            "action_suggestion": self.action_suggestion,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Claim:
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            text=d.get("text", ""),
            theme=d.get("theme", ""),
            relevance=d.get("relevance", ""),
            node_id=d.get("node_id"),
            confidence=d.get("confidence", ""),
            significance=d.get("significance", 1),
            actionable=d.get("actionable", False),
            action_suggestion=d.get("action_suggestion", ""),
        )


@dataclass
class Source:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    url: str = ""
    title: str = ""
    author: str = ""
    date_published: str = ""
    date_ingested: str = field(default_factory=lambda: date.today().isoformat())
    summary: str = ""
    claims: list[Claim] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    significance: int = 1  # max significance across claims
    credibility_notes: str = ""

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.date_ingested}_{self.id}.yaml"
        path.write_text(yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False))
        return path

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "date_published": self.date_published,
            "date_ingested": self.date_ingested,
            "summary": self.summary,
            "themes": self.themes,
            "significance": self.significance,
            "credibility_notes": self.credibility_notes,
            "claims": [c.to_dict() for c in self.claims],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Source:
        claims = [Claim.from_dict(c) for c in d.get("claims", [])]
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            url=d.get("url", ""),
            title=d.get("title", ""),
            author=d.get("author", ""),
            date_published=d.get("date_published", ""),
            date_ingested=d.get("date_ingested", ""),
            summary=d.get("summary", ""),
            claims=claims,
            themes=d.get("themes", []),
            significance=d.get("significance", 1),
            credibility_notes=d.get("credibility_notes", ""),
        )

    @classmethod
    def load(cls, path: Path) -> Source:
        data = yaml.safe_load(path.read_text())
        return cls.from_dict(data)
