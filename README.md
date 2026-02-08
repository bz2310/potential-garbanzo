# Future Outlook Agent

Autonomous intelligence agent that scans ~45 sources twice daily, extracts significant claims across 9 thematic domains, autonomously updates a probabilistic scenario tree, and emails a comprehensive intelligence report.

Built for a family of 6 optimizing for survivability, durable control/power, and health/longevity.

## Setup

```bash
pip install -e .
python -m outlook init
```

Edit `data/config.yaml`:
- Add your Anthropic API key
- Configure Gmail SMTP (use an [App Password](https://support.google.com/accounts/answer/185833))

## Usage

**Start the scheduler (runs at 7 AM and 5 PM EST):**
```bash
python -m outlook run
```

**Run a manual scan:**
```bash
python -m outlook scan
```

**Send a test email:**
```bash
python -m outlook email-test
```

**Override a probability (when you disagree with the agent):**
```bash
python -m outlook override ai_foundation_models abc12345 0.35 \
  --reason "I think rapid takeoff is more likely given recent benchmarks"
```

**View current scenario trees:**
```bash
python -m outlook tree --all
python -m outlook tree ai_foundation_models
```

**View reasoning history:**
```bash
python -m outlook beliefs --days 30
```

**View thematic map:**
```bash
python -m outlook themes
```

**Browse ingested sources:**
```bash
python -m outlook sources
python -m outlook sources --theme energy
```

## 9 Themes Tracked

1. **AI Foundation Models** — capability trajectory, scaling, alignment
2. **AI Applications** — economic impact, labor displacement, new industries
3. **AI Supply Chain** — chips, compute, NVIDIA, TSMC, export controls
4. **Robotics** — humanoids, drones, physical automation
5. **Geopolitics** — US-China, alliances, conflict, governance
6. **Energy** — solar, nuclear, grid, AI energy demand
7. **Demographics** — fertility, aging, migration, workforce
8. **Capital Markets** — asset regimes, inflation, dollar, crypto
9. **Health & Longevity** — GLP-1s, gene therapy, longevity, biotech

## Email Format

Each briefing contains (in order):
1. **Belief Changes** — what the agent changed and why
2. **Significant Reads** — full summaries with clickable links (4/5+ significance only)
3. **30-Day Reasoning History** — rolling log of all probability changes
4. **Full Scenario Trees** — all 9 themes with current probabilities
5. **Probability-Weighted Family Actions** — ranked by expected value

If nothing significant happened, no email is sent.

## Architecture

```
outlook/
  models/          Data models (scenario trees, beliefs, sources, themes)
  engines/         Business logic (scanner, extractor, analyst, briefing, email)
  pipeline.py      Full scan-extract-analyze-brief-email pipeline
  scheduler.py     7 AM / 5 PM EST cron scheduler
  seed.py          Initial scenario trees and configuration
  cli.py           CLI for overrides and deep dives
data/
  scenarios/       YAML scenario trees
  sources/         Ingested articles
  beliefs/         Append-only belief delta log
  maps/            Thematic future maps
  briefings/       Archived HTML briefings
  config.yaml      All configuration
templates/
  briefing.html    Jinja2 email template
```
