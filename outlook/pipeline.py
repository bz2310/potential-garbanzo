"""Pipeline — the full scan-extract-analyze-brief-email pipeline.

This is what runs on each scheduled scan and can also be invoked manually.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from outlook.engines.analyst import Analyst
from outlook.engines.briefing_engine import BriefingEngine
from outlook.engines.emailer import Emailer
from outlook.engines.extractor import Extractor
from outlook.engines.llm_client import create_llm_client
from outlook.engines.scanner import FeedConfig, Scanner
from outlook.engines.scenario_engine import ScenarioEngine
from outlook.models.belief import BeliefLog

logger = logging.getLogger(__name__)


def load_config(project_root: Path) -> dict:
    config_path = project_root / "data" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found at {config_path}. Run 'outlook init' first.")
    return yaml.safe_load(config_path.read_text())


def run_scan_pipeline(project_root: Path, scan_time: str = "AM") -> None:
    """Full pipeline: scan → extract → analyze → brief → email."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    config = load_config(project_root)
    scenarios_dir = project_root / "data" / "scenarios"
    sources_dir = project_root / "data" / "sources"
    beliefs_dir = project_root / "data" / "beliefs"
    briefings_dir = project_root / "data" / "briefings"
    templates_dir = project_root / "templates"
    seen_path = project_root / "data" / ".seen.yaml"

    llm = create_llm_client(config)
    significance_threshold = config.get("scanning", {}).get("significance_threshold", 4)
    lookback_hours = config.get("scanning", {}).get("lookback_hours", 12)

    # 1. Initialize components
    belief_log = BeliefLog(path=beliefs_dir / "log.yaml")
    belief_log.load()

    scanner = Scanner(seen_path=seen_path)
    extractor = Extractor(llm=llm)
    analyst = Analyst(llm=llm)
    scenario_engine = ScenarioEngine(scenarios_dir, belief_log)
    briefing_engine = BriefingEngine(scenario_engine, belief_log, templates_dir, briefings_dir)

    feeds = [FeedConfig.from_dict(f) for f in config.get("feeds", [])]

    # 2. Scan feeds
    logger.info(f"Scanning {len(feeds)} feeds (lookback: {lookback_hours}h)...")
    items = scanner.scan_all(feeds, lookback_hours=lookback_hours)
    logger.info(f"Found {len(items)} new items")

    if not items:
        logger.info("No new items. Skipping email.")
        return

    # 3. Extract claims
    logger.info("Extracting claims...")
    sources = extractor.extract_batch(items, significance_threshold=significance_threshold)
    logger.info(f"{len(sources)} sources above significance threshold")

    # Save sources
    for source in sources:
        source.save(sources_dir)

    # 4. Analyze — autonomous probability updates
    logger.info("Running analyst...")
    trees = scenario_engine.load_all_trees()
    deltas = analyst.analyze(trees, sources, belief_log)
    logger.info(f"Analyst made {len(deltas)} probability updates")

    # Save updated trees
    for name, tree in trees.items():
        scenario_engine.save_tree(tree)

    # 5. Build briefing
    if not sources and not deltas:
        logger.info("Nothing significant. No email sent.")
        return

    data = briefing_engine.build_briefing(deltas, sources, scan_time=scan_time)
    html = briefing_engine.render_html(data)
    subject = briefing_engine.render_subject(data)

    # Save briefing archive
    briefing_engine.save_briefing(html, data)

    # 6. Email
    email_config = config.get("email", {})
    if not email_config.get("smtp_host"):
        logger.warning("Email not configured. Printing briefing to stdout.")
        print(html)
        return

    emailer = Emailer(
        smtp_host=email_config["smtp_host"],
        smtp_port=email_config.get("smtp_port", 587),
        smtp_user=email_config["smtp_user"],
        smtp_password=email_config["smtp_password"],
        from_address=email_config["from_address"],
        to_addresses=email_config["to_addresses"],
    )
    emailer.send(subject, html)
    logger.info("Pipeline complete.")
