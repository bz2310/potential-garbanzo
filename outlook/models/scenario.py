"""Scenario tree — branching futures with probabilities.

Each node is a possible world-state.  Siblings are mutually exclusive and
their probabilities must sum to 1.  Leaf nodes carry family-action implications.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ScenarioNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    label: str = ""
    description: str = ""
    probability: float = 0.0
    signposts: list[str] = field(default_factory=list)
    theme: str = ""
    horizon: str = ""
    children: list[ScenarioNode] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.children:
            total = sum(c.probability for c in self.children)
            if abs(total - 1.0) > 0.01:
                errors.append(
                    f"Node '{self.label}': children sum to {total:.3f}, not 1.0"
                )
            for child in self.children:
                errors.extend(child.validate())
        if not 0.0 <= self.probability <= 1.0:
            errors.append(f"Node '{self.label}': probability {self.probability} out of [0,1]")
        return errors

    def flatten(self, prefix: str = "") -> list[dict]:
        path_label = f"{prefix} > {self.label}" if prefix else self.label
        if not self.children:
            return [{"path": path_label, "probability": self.probability,
                      "actions": self.actions, "signposts": self.signposts}]
        results = []
        for child in self.children:
            for leaf in child.flatten(path_label):
                leaf["probability"] *= self.probability if self.probability else 1.0
                results.append(leaf)
        return results

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "probability": self.probability,
            "signposts": self.signposts,
            "theme": self.theme,
            "horizon": self.horizon,
            "actions": self.actions,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ScenarioNode:
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            label=d.get("label", ""),
            description=d.get("description", ""),
            probability=d.get("probability", 0.0),
            signposts=d.get("signposts", []),
            theme=d.get("theme", ""),
            horizon=d.get("horizon", ""),
            children=children,
            actions=d.get("actions", []),
        )

    def find(self, node_id: str) -> Optional[ScenarioNode]:
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find(node_id)
            if found:
                return found
        return None

    def all_nodes(self) -> list[ScenarioNode]:
        nodes = [self]
        for child in self.children:
            nodes.extend(child.all_nodes())
        return nodes


@dataclass
class ScenarioTree:
    name: str
    created: str = field(default_factory=lambda: date.today().isoformat())
    updated: str = field(default_factory=lambda: date.today().isoformat())
    root: ScenarioNode = field(default_factory=ScenarioNode)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "created": self.created,
            "updated": self.updated,
            "root": self.root.to_dict(),
        }
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    @classmethod
    def load(cls, path: Path) -> ScenarioTree:
        data = yaml.safe_load(path.read_text())
        return cls(
            name=data["name"],
            created=data.get("created", ""),
            updated=data.get("updated", ""),
            root=ScenarioNode.from_dict(data["root"]),
        )

    def validate(self) -> list[str]:
        return self.root.validate()

    def terminal_scenarios(self) -> list[dict]:
        return self.root.flatten()
