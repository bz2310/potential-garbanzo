"""Briefing engine — generates the full intelligence report.

This assembles all 5 sections of the email:
1. Belief changes this scan
2. Significant reads (full summaries + clickable links)
3. 30-day reasoning history
4. Full scenario tree (all 9 themes)
5. Probability-weighted family actions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from outlook.models.belief import BeliefDelta, BeliefLog
from outlook.models.scenario import ScenarioNode, ScenarioTree
from outlook.models.source import Source
from outlook.engines.scenario_engine import ScenarioEngine


@dataclass
class BriefingData:
    scan_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%b %d, %Y %H:%M UTC"))
    scan_time: str = ""  # "AM" or "PM"
    has_content: bool = False

    # Section 1: belief changes from this scan
    belief_changes: list[BeliefDelta] = field(default_factory=list)

    # Section 2: significant articles
    significant_sources: list[Source] = field(default_factory=list)

    # Section 3: 30-day reasoning history
    reasoning_history: list[BeliefDelta] = field(default_factory=list)

    # Section 4: full scenario trees
    trees: dict[str, ScenarioTree] = field(default_factory=dict)

    # Section 5: weighted family actions
    weighted_actions: list[dict] = field(default_factory=list)

    @property
    def n_articles(self) -> int:
        return len(self.significant_sources)

    @property
    def n_changes(self) -> int:
        return len(self.belief_changes)


class BriefingEngine:
    def __init__(
        self,
        scenario_engine: ScenarioEngine,
        belief_log: BeliefLog,
        templates_dir: Path,
        briefings_dir: Path,
    ):
        self.scenario_engine = scenario_engine
        self.belief_log = belief_log
        self.templates_dir = templates_dir
        self.briefings_dir = briefings_dir
        self.briefings_dir.mkdir(parents=True, exist_ok=True)

    def build_briefing(
        self,
        new_deltas: list[BeliefDelta],
        significant_sources: list[Source],
        scan_time: str = "AM",
    ) -> BriefingData:
        data = BriefingData(scan_time=scan_time)

        # Section 1: belief changes
        data.belief_changes = new_deltas

        # Section 2: significant articles
        data.significant_sources = significant_sources

        # Section 3: 30-day reasoning history
        data.reasoning_history = self.belief_log.recent(days=30)

        # Section 4: all scenario trees
        data.trees = self.scenario_engine.load_all_trees()

        # Section 5: weighted actions
        data.weighted_actions = self.scenario_engine.combined_action_summary()

        data.has_content = bool(new_deltas) or bool(significant_sources)
        return data

    def render_html(self, data: BriefingData) -> str:
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )
        env.filters["pct"] = lambda v: f"{v:.0%}"
        env.filters["pct1"] = lambda v: f"{v:.1%}"
        env.filters["delta_arrow"] = lambda d: "\u25b2" if d > 0 else "\u25bc" if d < 0 else "="
        template = env.get_template("briefing.html")
        return template.render(data=data, render_tree=self._render_tree_html)

    def _render_tree_html(self, node: ScenarioNode, indent: int = 0, changed_ids: set | None = None) -> str:
        changed_ids = changed_ids or set()
        lines = []
        pad = "&nbsp;" * (indent * 4)
        prob_str = f"{node.probability:.0%}" if node.probability else ""

        # Check if this node changed
        marker = ""
        if node.id in changed_ids:
            marker = ' class="changed"'

        if node.children:
            connector = "\u251c\u2500\u2500" if indent > 0 else ""
            lines.append(f'<div{marker}>{pad}{connector} <strong>{node.label}</strong> '
                         f'<span class="prob">{prob_str}</span></div>')
            for i, child in enumerate(node.children):
                lines.append(self._render_tree_html(child, indent + 1, changed_ids))
        else:
            connector = "\u251c\u2500\u2500" if indent > 0 else ""
            lines.append(f'<div{marker}>{pad}{connector} {node.label} '
                         f'<span class="prob">{prob_str}</span></div>')

        return "\n".join(lines)

    def render_subject(self, data: BriefingData) -> str:
        parts = [f"Outlook Briefing \u2014 {data.scan_date} {data.scan_time}"]
        if data.n_changes > 0:
            parts.append(f"{data.n_changes} belief change{'s' if data.n_changes != 1 else ''}")
        if data.n_articles > 0:
            parts.append(f"{data.n_articles} article{'s' if data.n_articles != 1 else ''}")
        if not data.has_content:
            parts.append("no significant updates")
        return " | ".join(parts)

    def save_briefing(self, html: str, data: BriefingData) -> Path:
        ts = datetime.utcnow().strftime("%Y-%m-%d_%H%M")
        path = self.briefings_dir / f"{ts}.html"
        path.write_text(html)
        return path
