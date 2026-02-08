"""Scenario engine — tree CRUD, probability rebalancing, validation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from outlook.models.belief import BeliefDelta, BeliefLog
from outlook.models.scenario import ScenarioNode, ScenarioTree


class ScenarioEngine:
    def __init__(self, scenarios_dir: Path, belief_log: BeliefLog):
        self.scenarios_dir = scenarios_dir
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.belief_log = belief_log

    def list_trees(self) -> list[str]:
        return [p.stem for p in sorted(self.scenarios_dir.glob("*.yaml"))]

    def load_tree(self, name: str) -> ScenarioTree:
        path = self.scenarios_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"No scenario tree named '{name}'")
        return ScenarioTree.load(path)

    def load_all_trees(self) -> dict[str, ScenarioTree]:
        return {name: self.load_tree(name) for name in self.list_trees()}

    def save_tree(self, tree: ScenarioTree) -> Path:
        tree.updated = date.today().isoformat()
        path = self.scenarios_dir / f"{tree.name}.yaml"
        tree.save(path)
        return path

    def create_tree(self, name: str, root_label: str, root_description: str = "") -> ScenarioTree:
        tree = ScenarioTree(
            name=name,
            root=ScenarioNode(label=root_label, description=root_description, probability=1.0),
        )
        self.save_tree(tree)
        return tree

    def add_branch(
        self,
        tree: ScenarioTree,
        parent_id: str,
        label: str,
        probability: float,
        description: str = "",
        theme: str = "",
        horizon: str = "",
        signposts: Optional[list[str]] = None,
        actions: Optional[list[str]] = None,
    ) -> ScenarioNode:
        parent = tree.root.find(parent_id)
        if parent is None:
            raise ValueError(f"Node '{parent_id}' not found in tree '{tree.name}'")
        node = ScenarioNode(
            label=label,
            description=description,
            probability=probability,
            theme=theme,
            horizon=horizon,
            signposts=signposts or [],
            actions=actions or [],
        )
        parent.children.append(node)
        self.save_tree(tree)
        return node

    def override_probability(
        self,
        tree: ScenarioTree,
        node_id: str,
        new_probability: float,
        reason: str,
    ) -> BeliefDelta:
        """Manual override — used via CLI when you disagree with the analyst."""
        node = tree.root.find(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found")
        if not reason:
            raise ValueError("Reason is required for probability overrides")

        old_prob = node.probability
        node.probability = new_probability

        sibling_adjustments = self._rebalance_siblings(tree, node_id, new_probability)

        delta = BeliefDelta(
            node_id=node_id,
            node_label=node.label,
            tree_name=tree.name,
            old_probability=old_prob,
            new_probability=new_probability,
            reason=f"[MANUAL OVERRIDE] {reason}",
            sibling_adjustments=sibling_adjustments,
        )
        self.belief_log.append(delta)
        self.save_tree(tree)
        return delta

    def _rebalance_siblings(
        self, tree: ScenarioTree, node_id: str, new_probability: float
    ) -> list[dict]:
        parent = self._find_parent(tree.root, node_id)
        if not parent or len(parent.children) <= 1:
            return []

        siblings = [c for c in parent.children if c.id != node_id]
        old_sibling_total = sum(s.probability for s in siblings)
        new_sibling_total = 1.0 - new_probability

        adjustments = []
        if old_sibling_total > 0:
            for sib in siblings:
                old_sib_prob = sib.probability
                sib.probability = round(sib.probability / old_sibling_total * new_sibling_total, 4)
                adjustments.append({
                    "node_id": sib.id,
                    "label": sib.label,
                    "old": round(old_sib_prob, 4),
                    "new": round(sib.probability, 4),
                })
        return adjustments

    def _find_parent(self, node: ScenarioNode, child_id: str) -> Optional[ScenarioNode]:
        for child in node.children:
            if child.id == child_id:
                return node
            result = self._find_parent(child, child_id)
            if result:
                return result
        return None

    def action_summary(self, tree: ScenarioTree) -> list[dict]:
        actions: dict[str, float] = {}
        for scenario in tree.terminal_scenarios():
            for action in scenario.get("actions", []):
                actions[action] = actions.get(action, 0) + scenario["probability"]
        return sorted(
            [{"action": a, "weight": w} for a, w in actions.items()],
            key=lambda x: x["weight"],
            reverse=True,
        )

    def combined_action_summary(self) -> list[dict]:
        """Weighted actions across ALL trees."""
        actions: dict[str, float] = {}
        for name in self.list_trees():
            tree = self.load_tree(name)
            for scenario in tree.terminal_scenarios():
                for action in scenario.get("actions", []):
                    actions[action] = actions.get(action, 0) + scenario["probability"]
        return sorted(
            [{"action": a, "weight": w} for a, w in actions.items()],
            key=lambda x: x["weight"],
            reverse=True,
        )
