"""CLI — override and deep-dive interface. Daily operation is automated via scheduler."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "data" / "scenarios"
SOURCES_DIR = PROJECT_ROOT / "data" / "sources"
BELIEFS_DIR = PROJECT_ROOT / "data" / "beliefs"
BRIEFINGS_DIR = PROJECT_ROOT / "data" / "briefings"
MAPS_DIR = PROJECT_ROOT / "data" / "maps"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
THEMES_PATH = MAPS_DIR / "themes.yaml"
BELIEF_LOG_PATH = BELIEFS_DIR / "log.yaml"


def get_belief_log():
    from outlook.models.belief import BeliefLog
    log = BeliefLog(path=BELIEF_LOG_PATH)
    if BELIEF_LOG_PATH.exists():
        log.load()
    return log


def get_scenario_engine():
    from outlook.engines.scenario_engine import ScenarioEngine
    return ScenarioEngine(SCENARIOS_DIR, get_belief_log())


def get_theme_engine():
    from outlook.engines.theme_engine import ThemeEngine
    return ThemeEngine(THEMES_PATH)


# ── Commands ─────────────────────────────────────────────────────


def cmd_init(args):
    """Initialize project with seed scenario trees, themes, and config."""
    from outlook.seed import seed_all
    seed_all(PROJECT_ROOT)
    print("Initialized. Edit data/config.yaml with your API key and email settings.")
    print("Then run: python -m outlook scan")


def cmd_scan(args):
    """Run one scan cycle manually."""
    from outlook.pipeline import run_scan_pipeline
    run_scan_pipeline(PROJECT_ROOT, scan_time=args.time)


def cmd_run(args):
    """Start the 7AM/5PM scheduler daemon."""
    from outlook.scheduler import start_scheduler
    start_scheduler(PROJECT_ROOT)


def cmd_email_test(args):
    """Send a test email."""
    from outlook.pipeline import load_config
    from outlook.engines.emailer import Emailer
    config = load_config(PROJECT_ROOT)
    ec = config["email"]
    emailer = Emailer(
        smtp_host=ec["smtp_host"],
        smtp_port=ec.get("smtp_port", 587),
        smtp_user=ec["smtp_user"],
        smtp_password=ec["smtp_password"],
        from_address=ec["from_address"],
        to_addresses=ec["to_addresses"],
    )
    ok = emailer.send(
        "Future Outlook Agent — Test Email",
        "<h1>Test</h1><p>If you see this, email is configured correctly.</p>",
    )
    print("Sent!" if ok else "Failed. Check logs.")


def cmd_blurbs(args):
    """Fetch URLs, extract blurbs, and email them."""
    from outlook.pipeline import run_blurbs_pipeline
    urls = args.urls.split()
    if not urls:
        print("Error: provide at least one URL.")
        return
    run_blurbs_pipeline(PROJECT_ROOT, urls)


def cmd_override(args):
    """Override a probability (disagree with the analyst)."""
    se = get_scenario_engine()
    tree = se.load_tree(args.tree)
    delta = se.override_probability(tree, args.node_id, args.probability, args.reason)
    print(delta.summary_line())
    if delta.sibling_adjustments:
        for adj in delta.sibling_adjustments:
            print(f"  Rebalanced: {adj['label']} {adj['old']:.0%} -> {adj['new']:.0%}")


def cmd_tree_show(args):
    """Display a scenario tree."""
    se = get_scenario_engine()
    if args.all:
        for name in se.list_trees():
            tree = se.load_tree(name)
            print(f"\n{'='*60}")
            print(f"  {name.upper()}")
            print(f"{'='*60}")
            _print_node(tree.root)
    else:
        tree = se.load_tree(args.name)
        _print_node(tree.root)


def _print_node(node, indent=0):
    prefix = "  " * indent
    prob = f"{node.probability:.0%}" if node.probability else ""
    label = node.label
    print(f"{prefix}{'├── ' if indent else ''}{label} {prob}")
    if node.signposts:
        print(f"{prefix}    Signposts: {', '.join(node.signposts)}")
    if node.actions:
        print(f"{prefix}    Actions: {', '.join(node.actions)}")
    for child in node.children:
        _print_node(child, indent + 1)


def cmd_beliefs(args):
    """Show reasoning history."""
    log = get_belief_log()
    deltas = log.recent(days=args.days)
    if not deltas:
        print(f"No belief changes in the last {args.days} day(s).")
        return
    for delta in deltas:
        print(delta.summary_line())


def cmd_themes(args):
    """Show thematic map."""
    te = get_theme_engine()
    tmap = te.load_or_create()
    if not tmap.themes:
        print("No themes. Run 'outlook init' first.")
        return
    for theme in tmap.themes:
        stale = tmap.stale_themes(max_age_days=14)
        stale_marker = " [STALE]" if theme in stale else ""
        print(f"\n{'='*60}")
        print(f"  {theme.display_name}{stale_marker}")
        print(f"  Last updated: {theme.last_updated}")
        if theme.current_assessment:
            print(f"  Assessment: {theme.current_assessment}")
        for q in theme.key_questions:
            print(f"    ? {q}")
        for f in theme.family_implications:
            print(f"    > {f}")


def cmd_verify_feeds(args):
    """Test all configured feeds and report which work."""
    import xml.etree.ElementTree as ET
    from outlook.pipeline import load_config

    config = load_config(PROJECT_ROOT)
    feeds = config.get("feeds", [])
    if not feeds:
        print("No feeds configured. Run 'outlook init' first.")
        return

    ok_count = 0
    fail_count = 0
    timeout = 15

    print(f"\nVerifying {len(feeds)} feeds...\n")
    print(f"{'Status':<8} {'Type':<7} {'Name':<35} {'Details'}")
    print("-" * 90)

    for f in feeds:
        name = f.get("name", "?")
        url = f.get("url", "")
        ftype = f.get("feed_type", "rss")

        try:
            if ftype == "reddit":
                test_url = url.rstrip("/") + "/hot.json?limit=1"
            else:
                test_url = url

            resp = requests.get(
                test_url,
                timeout=timeout,
                headers={"User-Agent": "FutureOutlookAgent/1.0"},
            )
            resp.raise_for_status()
            status = resp.status_code
            ctype = resp.headers.get("content-type", "")[:40]

            detail = ""
            if ftype == "rss":
                try:
                    root = ET.fromstring(resp.content)
                    items = list(root.iter("item"))
                    entries = list(root.iter("{http://www.w3.org/2005/Atom}entry"))
                    count = len(items) + len(entries)
                    detail = f"{status} | {count} entries | {ctype}"
                except ET.ParseError:
                    detail = f"{status} | XML parse error | {ctype}"
                    fail_count += 1
                    print(f"{'FAIL':<8} {ftype:<7} {name:<35} {detail}")
                    continue
            elif ftype == "reddit":
                data = resp.json()
                count = len(data.get("data", {}).get("children", []))
                detail = f"{status} | {count} posts | reddit JSON"
            else:
                from bs4 import BeautifulSoup as BS
                soup = BS(resp.text, "html.parser")
                title = soup.find("title")
                title_text = title.get_text(strip=True)[:50] if title else "(no title)"
                links = len(soup.find_all("a", href=True))
                detail = f"{status} | {links} links | {title_text}"

            ok_count += 1
            print(f"{'OK':<8} {ftype:<7} {name:<35} {detail}")

        except Exception as e:
            fail_count += 1
            err = str(e)[:60]
            print(f"{'FAIL':<8} {ftype:<7} {name:<35} {err}")

    print("-" * 90)
    print(f"\n  {ok_count} OK, {fail_count} FAILED out of {len(feeds)} feeds\n")


def cmd_sources(args):
    """List ingested sources."""
    from outlook.models.source import Source
    sources_dir = SOURCES_DIR
    if not sources_dir.exists():
        print("No sources yet.")
        return
    for path in sorted(sources_dir.glob("*.yaml"), reverse=True):
        source = Source.load(path)
        if args.theme and args.theme not in source.themes:
            continue
        print(f"\n  [{source.significance}/5] {source.title} — {source.author}")
        print(f"  {source.url}")
        print(f"  Themes: {', '.join(source.themes)}")


# ── Parser ───────────────────────────────────────────────────────


def build_parser():
    parser = argparse.ArgumentParser(
        prog="outlook",
        description="Future Outlook Agent — autonomous intelligence scanner",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize with seed data and config")

    p = sub.add_parser("scan", help="Run one scan cycle manually")
    p.add_argument("--time", default="AM", choices=["AM", "PM"])

    sub.add_parser("run", help="Start the 7AM/5PM scheduler daemon")

    sub.add_parser("email-test", help="Send a test email")

    p = sub.add_parser("override", help="Override a probability")
    p.add_argument("tree", help="Tree name")
    p.add_argument("node_id", help="Node ID to change")
    p.add_argument("probability", type=float, help="New probability (0-1)")
    p.add_argument("--reason", required=True, help="Why you disagree")

    p = sub.add_parser("tree", help="Show scenario tree(s)")
    p.add_argument("name", nargs="?", default=None)
    p.add_argument("--all", action="store_true", help="Show all trees")

    p = sub.add_parser("beliefs", help="Show reasoning history")
    p.add_argument("--days", type=int, default=30)

    sub.add_parser("themes", help="Show thematic map")

    sub.add_parser("verify-feeds", help="Test all configured feeds and report status")

    p = sub.add_parser("blurbs", help="Extract and email blurbs for specific URLs")
    p.add_argument("urls", help="Space-separated URLs to extract blurbs from")

    p = sub.add_parser("sources", help="List ingested sources")
    p.add_argument("--theme", default=None)

    return parser


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    cmds = {
        "init": cmd_init,
        "scan": cmd_scan,
        "run": cmd_run,
        "email-test": cmd_email_test,
        "override": cmd_override,
        "tree": cmd_tree_show,
        "beliefs": cmd_beliefs,
        "themes": cmd_themes,
        "verify-feeds": cmd_verify_feeds,
        "blurbs": cmd_blurbs,
        "sources": cmd_sources,
    }
    cmds[args.command](args)
