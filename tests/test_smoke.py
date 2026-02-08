"""Smoke tests — verify the system works without API keys or email."""

import json
import tempfile
from pathlib import Path

from outlook.models.scenario import ScenarioNode, ScenarioTree
from outlook.models.belief import BeliefDelta, BeliefLog
from outlook.models.source import Source, Claim
from outlook.models.theme import ThematicMap, CANONICAL_THEMES
from outlook.engines.scenario_engine import ScenarioEngine
from outlook.engines.theme_engine import ThemeEngine
from outlook.seed import _build_all_trees


def test_scenario_trees_validate():
    """All 9 seed trees should pass validation (probabilities sum to 1)."""
    trees = _build_all_trees()
    assert len(trees) == 9, f"Expected 9 trees, got {len(trees)}"
    for tree in trees:
        errors = tree.validate()
        assert not errors, f"Tree '{tree.name}' has errors: {errors}"
    print(f"  PASS: all {len(trees)} scenario trees validate")


def test_scenario_tree_save_load():
    """Trees should round-trip through YAML."""
    trees = _build_all_trees()
    with tempfile.TemporaryDirectory() as d:
        for tree in trees:
            path = Path(d) / f"{tree.name}.yaml"
            tree.save(path)
            loaded = ScenarioTree.load(path)
            assert loaded.name == tree.name
            assert loaded.root.label == tree.root.label
            errors = loaded.validate()
            assert not errors, f"Loaded tree '{tree.name}' has errors: {errors}"
    print("  PASS: all trees round-trip through YAML")


def test_belief_log():
    """Belief log should append, persist, and query."""
    with tempfile.TemporaryDirectory() as d:
        log = BeliefLog(path=Path(d) / "log.yaml")

        delta = BeliefDelta(
            node_id="abc123",
            node_label="Test node",
            tree_name="test_tree",
            old_probability=0.25,
            new_probability=0.30,
            reason="Test reason",
        )
        log.append(delta)
        assert len(log.entries) == 1
        assert abs(log.entries[0].delta - 0.05) < 0.001
        assert log.entries[0].direction == "UP"

        # Reload
        log2 = BeliefLog(path=Path(d) / "log.yaml")
        log2.load()
        assert len(log2.entries) == 1
        assert log2.entries[0].reason == "Test reason"
    print("  PASS: belief log append, persist, reload")


def test_source_save_load():
    """Sources should save and load."""
    with tempfile.TemporaryDirectory() as d:
        source = Source(
            url="https://example.com",
            title="Test Article",
            author="Test Author",
            summary="A test article.",
            themes=["ai_foundation_models"],
            significance=4,
            claims=[
                Claim(text="AI will be huge", theme="ai_foundation_models",
                      significance=4, confidence="high"),
            ],
        )
        path = source.save(Path(d))
        loaded = Source.load(path)
        assert loaded.title == "Test Article"
        assert len(loaded.claims) == 1
        assert loaded.claims[0].text == "AI will be huge"
    print("  PASS: source save/load")


def test_theme_engine():
    """Theme engine should initialize defaults."""
    with tempfile.TemporaryDirectory() as d:
        te = ThemeEngine(Path(d) / "themes.yaml")
        tmap = te.initialize_defaults()
        assert len(tmap.themes) == len(CANONICAL_THEMES)
        for theme in tmap.themes:
            assert theme.key_questions, f"Theme '{theme.name}' has no key questions"
            assert theme.family_implications, f"Theme '{theme.name}' has no family implications"
    print("  PASS: theme engine defaults")


def test_scenario_engine_override():
    """Overriding a probability should create a belief delta and rebalance siblings."""
    with tempfile.TemporaryDirectory() as d:
        log = BeliefLog(path=Path(d) / "log.yaml")
        se = ScenarioEngine(Path(d) / "scenarios", log)

        tree = se.create_tree("test", "Root")
        se.add_branch(tree, tree.root.id, "A", 0.60)
        tree = se.load_tree("test")
        se.add_branch(tree, tree.root.id, "B", 0.40)
        tree = se.load_tree("test")

        node_a = tree.root.children[0]
        delta = se.override_probability(tree, node_a.id, 0.70, "Testing override")

        assert delta.old_probability == 0.60
        assert delta.new_probability == 0.70
        assert "[MANUAL OVERRIDE]" in delta.reason
        assert len(log.entries) == 1

        # Reload and check B was rebalanced
        tree = se.load_tree("test")
        node_b = tree.root.children[1]
        assert abs(node_b.probability - 0.30) < 0.01
    print("  PASS: scenario engine override + rebalance")


def test_init_full():
    """Full init should create everything without errors."""
    with tempfile.TemporaryDirectory() as d:
        project_root = Path(d)
        (project_root / "templates").mkdir()
        # Copy briefing template (not needed for init, but for completeness)

        from outlook.seed import seed_all
        seed_all(project_root)

        scenarios_dir = project_root / "data" / "scenarios"
        assert len(list(scenarios_dir.glob("*.yaml"))) == 9

        config_path = project_root / "data" / "config.yaml"
        assert config_path.exists()

        themes_path = project_root / "data" / "maps" / "themes.yaml"
        assert themes_path.exists()
    print("  PASS: full init creates all files")


if __name__ == "__main__":
    print("Running smoke tests...\n")
    test_scenario_trees_validate()
    test_scenario_tree_save_load()
    test_belief_log()
    test_source_save_load()
    test_theme_engine()
    test_scenario_engine_override()
    test_init_full()
    print("\nAll tests passed.")
