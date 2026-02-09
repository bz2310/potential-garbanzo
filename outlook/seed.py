"""Seed data — creates all 9 scenario trees, thematic map, config, and feed list."""

from __future__ import annotations

from pathlib import Path

import yaml

from outlook.engines.scanner import DEFAULT_LOOKBACK_HOURS
from outlook.engines.theme_engine import ThemeEngine
from outlook.models.scenario import ScenarioNode, ScenarioTree


def seed_all(project_root: Path) -> None:
    scenarios_dir = project_root / "data" / "scenarios"
    maps_dir = project_root / "data" / "maps"
    config_path = project_root / "data" / "config.yaml"

    scenarios_dir.mkdir(parents=True, exist_ok=True)
    maps_dir.mkdir(parents=True, exist_ok=True)
    (project_root / "data" / "sources").mkdir(parents=True, exist_ok=True)
    (project_root / "data" / "beliefs").mkdir(parents=True, exist_ok=True)
    (project_root / "data" / "briefings").mkdir(parents=True, exist_ok=True)

    # Themes
    te = ThemeEngine(maps_dir / "themes.yaml")
    te.initialize_defaults()
    print("  Created thematic map (9 themes)")

    # Scenario trees
    trees = _build_all_trees()
    for tree in trees:
        tree.save(scenarios_dir / f"{tree.name}.yaml")
        errors = tree.validate()
        if errors:
            print(f"  WARNING: {tree.name} has validation errors:")
            for e in errors:
                print(f"    {e}")
        else:
            print(f"  Created scenario tree: {tree.name}")

    # Config
    if not config_path.exists():
        _write_default_config(config_path)
        print(f"  Created config template at {config_path}")
    else:
        print(f"  Config already exists at {config_path}")


def _n(label, prob, children=None, desc="", signposts=None, actions=None,
       theme="", horizon=""):
    """Shorthand for building a ScenarioNode."""
    return ScenarioNode(
        label=label,
        probability=prob,
        description=desc,
        children=children or [],
        signposts=signposts or [],
        actions=actions or [],
        theme=theme,
        horizon=horizon,
    )


def _build_all_trees() -> list[ScenarioTree]:
    return [
        _tree_ai_foundation_models(),
        _tree_ai_applications(),
        _tree_ai_supply_chain(),
        _tree_robotics(),
        _tree_geopolitics(),
        _tree_energy(),
        _tree_demographics(),
        _tree_capital_markets(),
        _tree_health_longevity(),
    ]


def _tree_ai_foundation_models() -> ScenarioTree:
    root = _n("AI Foundation Models", 1.0, theme="ai_foundation_models", children=[
        _n("Rapid takeoff — superhuman by 2028", 0.25, horizon="2028", children=[
            _n("Controlled by 2-3 labs", 0.50,
               signposts=["Lab consolidation", "Government partnerships", "Export controls hold"],
               actions=["Position close to winning labs", "Invest concentrated in AI leaders"]),
            _n("Open-source catches up within 12 months", 0.30,
               signposts=["Llama/Mistral match frontier", "Weights leak", "China closes gap"],
               actions=["AI literacy over platform bets", "Skills in deployment not access"]),
            _n("State seizure — governments control labs", 0.20,
               signposts=["Executive orders", "IAEA-style AI body formed", "Lab CEOs pushed out"],
               actions=["Government adjacency critical", "DC/policy career paths"]),
        ]),
        _n("Steady climb — superhuman by 2030-2034", 0.45, horizon="2030-2034", children=[
            _n("Scaling continues working", 0.60,
               signposts=["Each generation clearly better", "Compute investment keeps growing"],
               actions=["Traditional education still has runway", "Gradual repositioning"]),
            _n("New paradigm needed but found", 0.30,
               signposts=["Plateau then breakthrough", "New architecture announcements"],
               actions=["Watch for paradigm shift signals", "Stay flexible"]),
            _n("Progress real but overhyped", 0.10,
               signposts=["Enterprise adoption disappoints", "Revenue growth slows"],
               actions=["Don't over-rotate", "Maintain traditional career optionality"]),
        ]),
        _n("Plateau — diminishing returns", 0.20, horizon="2026-2030", children=[
            _n("Temporary plateau then new breakthrough", 0.60,
               signposts=["AI winter discourse", "Then sudden capability jump"],
               actions=["Buy the dip", "Maintain conviction through winter"]),
            _n("Sustained ceiling for this generation", 0.40,
               signposts=["5+ years flat benchmarks", "Talent exodus from labs"],
               actions=["Traditional career paths viable", "Reduce AI portfolio weight"]),
        ]),
        _n("Catastrophic AI incident", 0.10, children=[
            _n("Recoverable — regulation, 3-5 year slowdown", 0.70,
               signposts=["Major autonomous system failure", "Public backlash", "Moratorium"],
               actions=["Short-term defensive", "Long-term still AI-forward"]),
            _n("Civilizational-scale damage", 0.30,
               signposts=["Cascading infrastructure failure", "Loss of life"],
               actions=["Self-sufficiency", "Geographic diversification", "Community resilience"]),
        ]),
    ])
    return ScenarioTree(name="ai_foundation_models", root=root)


def _tree_ai_applications() -> ScenarioTree:
    root = _n("AI Applications", 1.0, theme="ai_applications", children=[
        _n("Rapid displacement — most knowledge work automated by 2030", 0.20, horizon="2030", children=[
            _n("New jobs emerge fast enough", 0.40,
               signposts=["New job categories appearing", "Wages rising in complementary roles"],
               actions=["Train children for human-AI collaboration", "Creativity and management"]),
            _n("Mass unemployment / UBI era", 0.35,
               signposts=["Unemployment >15%", "Political pressure for UBI", "Social unrest"],
               actions=["Capital ownership over labor income", "Own assets", "Political positioning"]),
            _n("Bifurcated — AI owners thrive, everyone else struggles", 0.25,
               signposts=["Gini coefficient spikes", "Tech wealth concentration accelerates"],
               actions=["Be on the owning side", "Equity and AI businesses over wage labor"]),
        ]),
        _n("Gradual transformation — sector by sector over 10-15 years", 0.55, horizon="2035-2040", children=[
            _n("White collar first", 0.50,
               signposts=["BigLaw layoffs", "Analyst roles eliminated", "Coding democratized"],
               actions=["Avoid pure knowledge-work careers for children", "Blend with physical/social"]),
            _n("Blue and white collar simultaneously", 0.30,
               signposts=["Robotics + AI converge", "Warehouse/logistics automated"],
               actions=["Ownership and management roles", "Trades with human-touch premium"]),
            _n("Patchwork — some sectors transformed, others stubborn", 0.20,
               signposts=["Healthcare/education resist", "Creative fields persist"],
               actions=["Identify and position in sticky sectors"]),
        ]),
        _n("Slower than expected — AI enhances but doesn't replace", 0.20, horizon="2035",
           signposts=["Productivity stats disappoint", "Human-in-the-loop remains standard"],
           actions=["Traditional career planning still works", "AI as skill multiplier"]),
        _n("Backlash / regulation slows adoption", 0.05,
           signposts=["EU-style regulation spreads", "Unions win AI restrictions"],
           actions=["Regulatory/policy careers gain value", "Compliance as growth industry"]),
    ])
    return ScenarioTree(name="ai_applications", root=root)


def _tree_ai_supply_chain() -> ScenarioTree:
    root = _n("AI Supply Chain", 1.0, theme="ai_supply_chain", children=[
        _n("US maintains chokehold", 0.35, children=[
            _n("Stable — chip diplomacy works", 0.60,
               signposts=["TSMC Arizona succeeds", "Allies comply", "China stays 2-3 gens behind"],
               actions=["US-based assets safe", "Invest in US semiconductor ecosystem"]),
            _n("Fragile — Taiwan single point of failure", 0.40,
               signposts=["China military exercises increase", "TSMC Arizona delays"],
               actions=["Diversify away from Taiwan-dependent supply chains"]),
        ]),
        _n("China breaks through", 0.20, children=[
            _n("Gradual — SMIC/Huawei close gap slowly", 0.70,
               signposts=["Huawei phones with competitive chips", "SMIC yield improvements"],
               actions=["Reduce bet on US chokehold thesis", "Dual-stack world"]),
            _n("Rapid — stolen IP or breakthrough", 0.30,
               signposts=["Sudden Chinese model capability jump", "Intelligence reports of IP theft"],
               actions=["Geopolitical risk reprices", "Accelerate diversification"]),
        ]),
        _n("Diversified supply chain emerges", 0.25,
           signposts=["Intel foundry wins customers", "Samsung GAA yields improve"],
           actions=["Less concentrated risk", "Broader semiconductor investment"]),
        _n("Compute becomes abundant / commoditized", 0.20, children=[
            _n("Hardware innovation (optical, neuromorphic)", 0.40,
               signposts=["Startup demos at scale", "Major lab adopts non-GPU"],
               actions=["Watch for platform shifts", "Don't over-index on NVIDIA"]),
            _n("Efficiency gains reduce compute needs", 0.60,
               signposts=["Models 100x cheaper to train/run", "Distillation breakthroughs"],
               actions=["Compute scarcity thesis weakens", "Moats shift to data and distribution"]),
        ]),
    ])
    return ScenarioTree(name="ai_supply_chain", root=root)


def _tree_robotics() -> ScenarioTree:
    root = _n("Robotics", 1.0, theme="robotics", children=[
        _n("Humanoid robots at scale by 2028-2030", 0.25, horizon="2028-2030", children=[
            _n("Factory/warehouse first, then household", 0.60,
               signposts=["Tesla Optimus in Gigafactory", "Amazon deploys humanoids"],
               actions=["Invest in robotics leaders", "Manual labor careers lose value"]),
            _n("Military/security first", 0.25,
               signposts=["DoD contracts for autonomous systems", "Drone swarm deployments"],
               actions=["Defense-adjacent positioning", "Geographic safety planning"]),
            _n("Household/elder care first", 0.15,
               signposts=["Figure/1X consumer products", "Japan elder care robots"],
               actions=["Early adoption advantage", "Domestic labor restructured"]),
        ]),
        _n("Functional but limited — narrow tasks only through 2035", 0.45, horizon="2035", children=[
            _n("Industrial robots expand, humanoids struggle", 0.55,
               signposts=["More automation in existing form factors", "Humanoids deploy poorly"],
               actions=["Skilled trades retain value", "Human dexterity premium"]),
            _n("Drones succeed where humanoids fail", 0.45,
               signposts=["Drone delivery mainstream", "Aerial inspection standard"],
               actions=["Drone-adjacent skills/businesses", "Airspace rights matter"]),
        ]),
        _n("Robotics winter — hardware too hard", 0.20,
           signposts=["Major humanoid companies fold", "Hardware costs don't come down"],
           actions=["Physical-world skills retain premium", "Blue collar trades strong"]),
        _n("Unexpected AI + robotics convergence", 0.10,
           signposts=["Autonomous vehicles everywhere", "Robot-to-robot economies"],
           actions=["Maintain optionality", "Own capital"]),
    ])
    return ScenarioTree(name="robotics", root=root)


def _tree_geopolitics() -> ScenarioTree:
    root = _n("Geopolitics", 1.0, theme="geopolitics", children=[
        _n("US-led unipolarity holds", 0.30, children=[
            _n("Cold peace with China", 0.65,
               signposts=["Trade continues despite tensions", "No Taiwan action", "Diplomatic channels open"],
               actions=["US assets safe", "Moderate geographic diversification"]),
            _n("US decisively wins AI/tech race", 0.20,
               signposts=["Chinese economy slows sharply", "Tech gap widens", "Internal instability"],
               actions=["Concentrate in US", "Bullish on dollar assets"]),
            _n("Managed decline — US weakens but no challenger", 0.15,
               signposts=["Fiscal crisis", "Political dysfunction", "No viable alternative"],
               actions=["Diversify currencies and jurisdictions slowly"]),
        ]),
        _n("Bipolar — US and China both AI superpowers", 0.25, children=[
            _n("Stable cold war — two blocs", 0.55,
               signposts=["Tech decoupling completes", "Separate internet/standards"],
               actions=["Pick your bloc", "Optimize within it"]),
            _n("Unstable — proxy wars, escalation risk", 0.45,
               signposts=["Military incidents", "AI arms race rhetoric", "Space weaponization"],
               actions=["Physical safety paramount", "Avoid frontline geographies", "Self-sufficiency"]),
        ]),
        _n("Multipolar fragmentation", 0.20,
           signposts=["BRICS gains real teeth", "EU asserts independence", "Regional powers rise"],
           actions=["Maximum diversification", "Multiple passports and jurisdictions"]),
        _n("Hot conflict (Taiwan or broader)", 0.15, children=[
            _n("Limited and contained", 0.60,
               signposts=["Blockade/strike on Taiwan", "No nuclear escalation"],
               actions=["Immediate supply chain disruption prep", "Asset safety"]),
            _n("Escalation to great power war", 0.40,
               signposts=["Nuclear threats", "NATO involvement", "Mobilization"],
               actions=["Geographic safety is existential", "Rural self-sufficiency"]),
        ]),
        _n("Black swan — unexpected realignment", 0.10,
           signposts=["Internal collapse (US or China)", "AI-driven regime change", "Pandemic 2.0"],
           actions=["Resilience over optimization", "Anti-fragile positioning"]),
    ])
    return ScenarioTree(name="geopolitics", root=root)


def _tree_energy() -> ScenarioTree:
    root = _n("Energy", 1.0, theme="energy", children=[
        _n("Solar + battery abundance by 2035", 0.30, horizon="2035", children=[
            _n("Broadly distributed (developing world too)", 0.45,
               signposts=["Solar <$10/MWh", "Battery <$50/kWh", "Africa/India leapfrog"],
               actions=["Energy independence easy and cheap", "Property anywhere viable"]),
            _n("Concentrated in wealthy nations", 0.40,
               signposts=["Supply chain bottlenecks for minerals", "Rich nations hoard capacity"],
               actions=["Be in wealthy nation", "Grid independence as insurance"]),
            _n("Grid infrastructure can't keep up", 0.15,
               signposts=["Generation cheap but transmission bottlenecked"],
               actions=["Local/distributed energy critical", "Off-grid capability valuable"]),
        ]),
        _n("Nuclear renaissance supplements renewables", 0.20, children=[
            _n("SMRs actually work and deploy", 0.50,
               signposts=["NuScale/similar operational", "Utilities ordering"],
               actions=["Invest in nuclear supply chain", "Proximity to nuclear safe"]),
            _n("Fusion breakthrough commercialized by 2035", 0.15,
               signposts=["Ignition replicated", "Private companies hit milestones"],
               actions=["Game-changing for civilization"]),
            _n("Large nuclear builds (AP1000, EPR)", 0.35,
               signposts=["China/Korea mass deployment", "US/EU restart programs"],
               actions=["Nuclear-friendly jurisdictions become energy-secure"]),
        ]),
        _n("AI energy demand creates crisis", 0.25, children=[
            _n("Datacenter strain but adaptation works", 0.60,
               signposts=["Brownouts near datacenters", "Massive grid investment", "Natural gas bridge"],
               actions=["Avoid grid-stressed geographies", "Energy self-sufficiency matters"]),
            _n("Energy scarcity constrains AI progress", 0.40,
               signposts=["Datacenter moratoriums", "Energy costs spike"],
               actions=["Energy assets extremely valuable", "Own generation capacity"]),
        ]),
        _n("Fossil fuel persistence — transition slower", 0.20,
           signposts=["Oil demand doesn't peak", "EV adoption slows", "Political reversals"],
           actions=["Don't abandon fossil fuel exposure entirely"]),
        _n("Energy weaponization escalates", 0.05,
           signposts=["Pipeline attacks", "Grid cyberattacks", "Energy embargoes"],
           actions=["Energy self-sufficiency not optional", "Local generation + storage"]),
    ])
    return ScenarioTree(name="energy", root=root)


def _tree_demographics() -> ScenarioTree:
    root = _n("Demographics", 1.0, theme="demographics", children=[
        _n("Demographic collapse accelerates", 0.45, children=[
            _n("AI/robots substitute for missing workers", 0.40,
               signposts=["Japan/Korea deploy robots in care", "GDP grows despite population decline"],
               actions=["Large family = social capital advantage", "Labor scarcity less relevant"]),
            _n("Mass immigration fills gaps", 0.25,
               signposts=["US/Europe liberalize immigration", "Brain drain from developing world"],
               actions=["Position in destination countries", "Multilingual children advantaged"]),
            _n("Economic stagnation / pension crisis", 0.35,
               signposts=["Pension funds insolvent", "Healthcare costs explode", "Tax burden on young"],
               actions=["Don't depend on government systems", "Private wealth critical"]),
        ]),
        _n("Fertility stabilizes or rebounds", 0.20, children=[
            _n("Pro-natalist policies work", 0.50,
               signposts=["Fertility rises to 1.8+ in policy-active countries"],
               actions=["Position in pro-natalist jurisdictions", "Capture subsidies"]),
            _n("Cultural shift — voluntary return to larger families", 0.50,
               signposts=["Religious/intentional communities grow", "Elite pro-natalism trend"],
               actions=["Community building with aligned families", "5-child plan becomes normal"]),
        ]),
        _n("Developing world population boom", 0.15,
           signposts=["Africa 2B+", "Nigeria/Ethiopia/DRC become major economies"],
           actions=["Emerging market exposure", "Children learn relevant languages"]),
        _n("Aging crisis dominates 2030s politics", 0.15,
           signposts=["Elder care #1 political issue", "Intergenerational conflict"],
           actions=["Young family = political power", "Avoid elder-heavy tax jurisdictions"]),
        _n("Pandemic or crisis causes demographic shock", 0.05,
           signposts=["New pandemic", "Fertility-affecting environmental exposure"],
           actions=["Health resilience", "Geographic flexibility"]),
    ])
    return ScenarioTree(name="demographics", root=root)


def _tree_capital_markets() -> ScenarioTree:
    root = _n("Capital Markets", 1.0, theme="capital_markets", children=[
        _n("AI drives new tech boom", 0.30, children=[
            _n("Winners-take-all — top 5 = 40%+ of S&P", 0.45,
               signposts=["AI revenue concentration", "Top companies dominate"],
               actions=["Concentrated positions in AI winners", "Not broad index"]),
            _n("Broad-based productivity boom", 0.35,
               signposts=["GDP >4%", "Productivity reflects AI", "Broad earnings growth"],
               actions=["Equities broadly", "Leverage for assets"]),
            _n("Bubble that pops then real growth", 0.20,
               signposts=["AI valuations 100x revenue", "IPO mania then correction"],
               actions=["Stay invested but hedge timing", "Cash reserves for buying crash"]),
        ]),
        _n("Inflation regime persists (3-5%)", 0.25, children=[
            _n("Financial repression — rates below inflation", 0.50,
               signposts=["Real rates negative", "Government debt eroded via inflation"],
               actions=["Own real assets (property, equity, commodities)", "Avoid bonds/cash"]),
            _n("Stagflation", 0.30,
               signposts=["GDP <2% + CPI >4%", "Political instability"],
               actions=["Hard assets", "Gold", "Energy", "Reduce debt exposure"]),
            _n("Hyperinflation risk in some currencies", 0.20,
               signposts=["Fiscal crisis in major economy", "Currency collapse"],
               actions=["Multi-currency holdings", "Hard assets", "Crypto as hedge"]),
        ]),
        _n("AI-driven deflation — abundance economy", 0.15,
           signposts=["Cost of goods drops rapidly", "CPI negative", "Central banks struggle"],
           actions=["Cash/bonds become valuable", "Debt is dangerous"]),
        _n("Dollar regime change", 0.15, children=[
            _n("Gradual — dollar weakens, no replacement", 0.60,
               signposts=["De-dollarization incremental", "BRICS local currency trade"],
               actions=["Diversify currency exposure", "Some non-USD assets"]),
            _n("Rapid — alternative reserve system", 0.40,
               signposts=["Major oil trade in non-USD", "Digital yuan", "Gold remonetization"],
               actions=["Significant non-USD allocation", "Physical gold", "Multi-jurisdiction banking"]),
        ]),
        _n("Crypto / digital assets mature", 0.15, children=[
            _n("Bitcoin as digital gold ($500K+)", 0.40,
               signposts=["Sovereign wealth funds hold BTC", "ETF inflows sustained"],
               actions=["5-15% BTC allocation as insurance"]),
            _n("CBDCs dominate, private crypto marginalized", 0.35,
               signposts=["Digital dollar/euro launched", "Crypto regulation tightens"],
               actions=["CBDC-compatible financial planning"]),
            _n("Crypto remains niche/volatile", 0.25,
               signposts=["No mainstream adoption breakthrough"],
               actions=["Minimal allocation"]),
        ]),
    ])
    return ScenarioTree(name="capital_markets", root=root)


def _tree_health_longevity() -> ScenarioTree:
    root = _n("Health & Longevity", 1.0, theme="health_longevity", children=[
        _n("Longevity escape velocity for wealthy by 2035", 0.15, horizon="2035", children=[
            _n("Epigenetic reprogramming works at scale", 0.40,
               signposts=["Yamanaka factors in clinical trials", "Age reversal in humans"],
               actions=["Be in top wealth percentile for access", "Position near biotech hubs"]),
            _n("Combination therapy stack extends healthspan 20+ years", 0.40,
               signposts=["GLP-1 + rapamycin + metformin + NAD+ show synergy"],
               actions=["Early adoption of proven protocols", "Children benefit from day one"]),
            _n("AI accelerates drug discovery dramatically", 0.20,
               signposts=["AI-designed drugs in Phase III", "10x faster pipeline"],
               actions=["Biotech investment", "Access to cutting-edge trials"]),
        ]),
        _n("Incremental progress — 5-10 year healthspan extension", 0.45, children=[
            _n("GLP-1 revolution continues expanding", 0.40,
               signposts=["New GLP-1 indications approved", "Widespread insurance coverage"],
               actions=["Adopt GLP-1s when appropriate", "Invest in Lilly/Novo"]),
            _n("AI-personalized preventive medicine", 0.35,
               signposts=["Continuous monitoring standard", "AI catches diseases years earlier"],
               actions=["Early adoption of monitoring tech", "Annual comprehensive panels"]),
            _n("Gene therapy for single-gene diseases mainstreamed", 0.25,
               signposts=["CRISPR therapies <$100K", "Sickle cell cure expands"],
               actions=["Genetic screening for children", "Access to gene therapy if needed"]),
        ]),
        _n("Status quo — marginal improvements only", 0.25,
           signposts=["Clinical trials disappoint", "Longevity biotech funding dries up"],
           actions=["Standard health optimization (exercise, sleep, nutrition)"]),
        _n("Healthcare system crisis limits access", 0.10,
           signposts=["Costs explode", "Rationing", "Two-tier medicine hardens"],
           actions=["Wealth = health access", "Concierge medicine", "Medical tourism"]),
        _n("Engineered pandemic or bioweapon risk", 0.05,
           signposts=["Lab leak discourse intensifies", "Dual-use AI bio research concerns"],
           actions=["Geographic flexibility", "Stockpile basics", "Community health resilience"]),
    ])
    return ScenarioTree(name="health_longevity", root=root)


def _write_default_config(config_path: Path) -> None:
    config = {
        # LLM provider — choose ONE of "anthropic" or "openai"
        "llm": {
            "provider": "anthropic",  # or "openai"
            "api_key": "YOUR_API_KEY_HERE",
            "model": "claude-sonnet-4-5-20250929",
            # For OpenAI, use: provider: openai, model: gpt-4o
        },
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "YOUR_EMAIL@gmail.com",
            "smtp_password": "YOUR_APP_PASSWORD",
            "from_address": "YOUR_EMAIL@gmail.com",
            "to_addresses": [
                "barbara.zhan@gmail.com",
                "max.schindler11@gmail.com",
            ],
        },
        "schedule": {
            "timezone": "US/Eastern",
            "scan_times": ["07:00", "17:00"],
        },
        "scanning": {
            "significance_threshold": 4,
            "max_articles_per_source": 10,
            "lookback_hours": DEFAULT_LOOKBACK_HOURS,
        },
        "feeds": [
            # AI Foundation Models & Research
            {"name": "Kevin Lu", "url": "https://kevinlu.ai/blog", "feed_type": "web",
             "themes": ["ai_foundation_models"]},
            {"name": "Delphi Intelligence", "url": "https://www.delphiintelligence.io/",
             "feed_type": "web", "themes": ["ai_foundation_models", "ai_applications"]},
            {"name": "Situational Awareness (Leopold)", "url": "https://www.forourposterity.com",
             "feed_type": "web", "themes": ["ai_foundation_models"]},
            {"name": "Zvi Mowshowitz", "url": "https://thezvi.substack.com/feed", "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_applications"]},
            {"name": "Import AI (Jack Clark)", "url": "https://importai.substack.com/feed", "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_applications"]},
            {"name": "Dwarkesh Patel", "url": "https://www.dwarkesh.com/feed", "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_applications"]},
            {"name": "Epoch AI", "url": "https://epochai.substack.com/feed", "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_supply_chain"]},
            {"name": "r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning",
             "feed_type": "reddit", "themes": ["ai_foundation_models"]},

            # AI Applications & Robotics
            {"name": "a16z blog", "url": "https://a16z.news/feed", "feed_type": "rss",
             "themes": ["ai_applications", "capital_markets"]},
            {"name": "r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA",
             "feed_type": "reddit", "themes": ["ai_foundation_models", "ai_applications"]},
            {"name": "IEEE Spectrum Robotics", "url": "https://spectrum.ieee.org/feeds/topic/robotics.rss",
             "feed_type": "rss", "themes": ["robotics"]},

            # AI Supply Chain
            {"name": "SemiAnalysis", "url": "https://www.semianalysis.com/feed", "feed_type": "rss",
             "themes": ["ai_supply_chain"]},
            {"name": "Fabricated Knowledge", "url": "https://www.fabricatedknowledge.com/feed",
             "feed_type": "rss", "themes": ["ai_supply_chain"]},
            {"name": "Hacker News", "url": "https://hnrss.org/best?count=30", "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_supply_chain", "ai_applications"]},

            # Geopolitics
            {"name": "Palladium Magazine", "url": "https://www.palladiummag.com/feed/", "feed_type": "rss",
             "themes": ["geopolitics", "demographics"]},
            {"name": "Noahpinion", "url": "https://noahpinion.substack.com/feed", "feed_type": "rss",
             "themes": ["geopolitics", "demographics", "ai_applications"]},
            {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml", "feed_type": "rss",
             "themes": ["geopolitics"]},
            {"name": "Peter Zeihan", "url": "https://zeihan.com/feed/", "feed_type": "rss",
             "themes": ["geopolitics", "demographics", "energy"]},
            {"name": "r/geopolitics", "url": "https://www.reddit.com/r/geopolitics",
             "feed_type": "reddit", "themes": ["geopolitics"]},

            # Energy
            {"name": "Ramez Naam", "url": "https://rameznaam.com/feed/", "feed_type": "rss",
             "themes": ["energy"]},

            # Demographics
            {"name": "Our World in Data", "url": "https://ourworldindata.org/atom.xml", "feed_type": "rss",
             "themes": ["demographics", "health_longevity"]},

            # Capital Markets & Bloomberg
            {"name": "Matt Levine (Money Stuff)", "url": "https://www.bloomberg.com/opinion/authors/ARbTQlRLRjE/matthew-s-levine.rss",
             "feed_type": "rss", "themes": ["capital_markets"]},
            {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss",
             "feed_type": "rss", "themes": ["capital_markets"]},
            {"name": "Bloomberg Technology", "url": "https://feeds.bloomberg.com/technology/news.rss",
             "feed_type": "rss", "themes": ["ai_applications", "ai_supply_chain"]},
            {"name": "Bloomberg Politics", "url": "https://feeds.bloomberg.com/politics/news.rss",
             "feed_type": "rss", "themes": ["geopolitics"]},
            {"name": "Bloomberg Economics", "url": "https://feeds.bloomberg.com/economics/news.rss",
             "feed_type": "rss", "themes": ["capital_markets", "demographics"]},
            {"name": "Bloomberg Opinion", "url": "https://feeds.bloomberg.com/bview/news.rss",
             "feed_type": "rss", "themes": ["capital_markets", "geopolitics"]},

            # Health & Longevity
            {"name": "Peter Attia", "url": "https://peterattiamd.com/feed/", "feed_type": "rss",
             "themes": ["health_longevity"]},
            {"name": "STAT News", "url": "https://www.statnews.com/feed/", "feed_type": "rss",
             "themes": ["health_longevity"]},
            {"name": "Derek Lowe (In the Pipeline)", "url": "https://www.science.org/blogs/pipeline/feed",
             "feed_type": "rss", "themes": ["health_longevity"]},
            {"name": "r/longevity", "url": "https://www.reddit.com/r/longevity",
             "feed_type": "reddit", "themes": ["health_longevity"]},

            # Cross-Cutting Thinkers
            {"name": "Marginal Revolution", "url": "https://marginalrevolution.com/feed",
             "feed_type": "rss",
             "themes": ["ai_applications", "geopolitics", "demographics", "capital_markets"]},
            {"name": "Astral Codex Ten", "url": "https://www.astralcodexten.com/feed",
             "feed_type": "rss",
             "themes": ["ai_foundation_models", "ai_applications", "health_longevity"]},
            {"name": "Robin Hanson", "url": "https://overcomingbias.substack.com/feed",
             "feed_type": "rss",
             "themes": ["ai_foundation_models", "demographics"]},
            {"name": "Samo Burja (Bismarck Analysis)", "url": "https://brief.bismarckanalysis.com/feed",
             "feed_type": "rss", "themes": ["geopolitics"]},
        ],
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
