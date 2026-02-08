"""Analyst — the autonomous brain that reasons about probability updates.

Takes extracted claims + current scenario trees and decides whether
probabilities should change.  Records all reasoning in the belief log.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import yaml

from outlook.engines.llm_client import LLMClient
from outlook.models.belief import BeliefDelta, BeliefLog
from outlook.models.scenario import ScenarioTree
from outlook.models.source import Source

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an intelligence analyst maintaining a probabilistic scenario tree
for a family of 6 (2 adults, 4+ children) focused on survivability, durable control/power,
and health/longevity.

Below is the CURRENT scenario tree with probabilities, followed by NEW claims extracted
from recent articles. Your job:

1. For each claim, determine if it should change any probability in the tree.
2. Only recommend changes when the evidence is genuinely significant — resist the urge
   to update on noise. Most claims should NOT trigger changes.
3. When you do recommend a change, explain WHY in 1-2 sentences.
4. Probability changes should be small (1-5 percentage points) unless the evidence is
   truly paradigm-shifting.
5. Siblings at each branch level MUST sum to 1.0 — when you increase one, you must
   specify which siblings decrease and by how much.

Present claims NEUTRALLY. Do not editorialize or add opinion beyond the probability assessment.

CURRENT SCENARIO TREE:
{tree_yaml}

NEW CLAIMS FROM RECENT SOURCES:
{claims_text}

Return ONLY valid JSON with this structure:
{{
  "updates": [
    {{
      "node_id": "abc12345",
      "node_label": "Name of the node",
      "tree_name": "tree_name",
      "old_probability": 0.25,
      "new_probability": 0.30,
      "reason": "Brief explanation citing specific evidence",
      "source_url": "https://...",
      "source_title": "Article title",
      "sibling_adjustments": [
        {{
          "node_id": "def67890",
          "label": "Sibling name",
          "old": 0.45,
          "new": 0.42
        }}
      ]
    }}
  ],
  "no_change_notes": "Brief note on why other claims didn't warrant changes (optional)"
}}

If NO changes are warranted, return: {{"updates": [], "no_change_notes": "explanation"}}"""


class Analyst:
    """Autonomous probability reasoning engine."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(
        self,
        trees: dict[str, ScenarioTree],
        sources: list[Source],
        belief_log: BeliefLog,
    ) -> list[BeliefDelta]:
        """Analyze new sources against all scenario trees and return belief deltas."""
        if not sources:
            return []

        # Build claims text
        claims_lines = []
        for source in sources:
            claims_lines.append(f"\n--- From: {source.title} by {source.author} ---")
            claims_lines.append(f"URL: {source.url}")
            claims_lines.append(f"Summary: {source.summary}")
            for claim in source.claims:
                claims_lines.append(
                    f"  [{claim.theme}] (significance {claim.significance}/5, "
                    f"confidence: {claim.confidence}): {claim.text}"
                )
        claims_text = "\n".join(claims_lines)

        # Build combined tree YAML
        tree_data = {}
        for name, tree in trees.items():
            tree_data[name] = tree.root.to_dict()
        tree_yaml = yaml.dump(tree_data, default_flow_style=False, sort_keys=False)

        prompt = ANALYSIS_PROMPT.format(
            tree_yaml=tree_yaml,
            claims_text=claims_text,
        )

        try:
            text = self.llm.complete(prompt, max_tokens=4096)

            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]

            data = json.loads(text)
        except json.JSONDecodeError:
            logger.exception("Failed to parse analyst JSON response")
            return []
        except Exception:
            logger.exception("Analyst API call failed")
            return []

        deltas: list[BeliefDelta] = []
        for update in data.get("updates", []):
            delta = BeliefDelta(
                node_id=update.get("node_id", ""),
                node_label=update.get("node_label", ""),
                tree_name=update.get("tree_name", ""),
                old_probability=update.get("old_probability", 0.0),
                new_probability=update.get("new_probability", 0.0),
                reason=update.get("reason", ""),
                source_url=update.get("source_url"),
                source_title=update.get("source_title"),
                sibling_adjustments=update.get("sibling_adjustments", []),
            )

            if not delta.reason:
                delta.reason = "Analyst update (no reason provided)"

            # Apply the change to the tree
            tree_name = delta.tree_name
            if tree_name in trees:
                tree = trees[tree_name]
                node = tree.root.find(delta.node_id)
                if node:
                    node.probability = delta.new_probability
                    # Apply sibling adjustments
                    for adj in delta.sibling_adjustments:
                        sib = tree.root.find(adj.get("node_id", ""))
                        if sib:
                            sib.probability = adj.get("new", sib.probability)

            # Record in belief log
            belief_log.append(delta)
            deltas.append(delta)

        if data.get("no_change_notes"):
            logger.info(f"Analyst notes: {data['no_change_notes']}")

        return deltas
