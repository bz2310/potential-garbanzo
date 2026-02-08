"""Theme engine — manage the thematic future map."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from outlook.models.theme import CANONICAL_THEMES, THEME_DISPLAY_NAMES, Theme, ThematicMap


class ThemeEngine:
    def __init__(self, map_path: Path):
        self.map_path = map_path

    def load_or_create(self) -> ThematicMap:
        if self.map_path.exists():
            return ThematicMap.load(self.map_path)
        return ThematicMap()

    def save(self, tmap: ThematicMap) -> None:
        tmap.save(self.map_path)

    def initialize_defaults(self) -> ThematicMap:
        defaults = {
            "ai_foundation_models": {
                "key_questions": [
                    "When does transformative AI arrive?",
                    "Which actors control frontier models?",
                    "Is scaling still working?",
                    "What is the alignment trajectory?",
                ],
                "family_implications": [
                    "Career positioning for AI-complementary skills",
                    "Education strategy for children in AI-native world",
                    "Geographic positioning near AI hubs vs. diversified",
                ],
            },
            "ai_applications": {
                "key_questions": [
                    "How fast does AI automate knowledge work?",
                    "Which sectors get disrupted first?",
                    "Do new job categories emerge fast enough?",
                    "Does AI create winner-take-all or broad-based gains?",
                ],
                "family_implications": [
                    "Career path planning for 5 children",
                    "Which skills retain value in AI economy",
                    "Income stream diversification",
                ],
            },
            "ai_supply_chain": {
                "key_questions": [
                    "Does the US chip chokehold hold?",
                    "When does China achieve self-sufficiency?",
                    "Does compute become commoditized?",
                    "What happens to NVIDIA's moat?",
                ],
                "family_implications": [
                    "Investment positioning in semiconductor ecosystem",
                    "Understanding compute bottleneck implications",
                    "Geographic risk from Taiwan dependency",
                ],
            },
            "robotics": {
                "key_questions": [
                    "When do humanoid robots deploy at scale?",
                    "Factory/military/household — which comes first?",
                    "Does physical automation lag AI by 5 years or 15?",
                    "Drone warfare trajectory?",
                ],
                "family_implications": [
                    "Manual labor career value trajectory",
                    "Home automation planning",
                    "Defense/military adjacency considerations",
                ],
            },
            "geopolitics": {
                "key_questions": [
                    "US-China: cold war, hot conflict, or detente?",
                    "Does the US maintain dollar hegemony?",
                    "Which jurisdictions become safe havens?",
                    "How does AI shift military balance?",
                ],
                "family_implications": [
                    "Passport and residency diversification",
                    "Asset jurisdiction diversification",
                    "Physical safety and relocation planning",
                ],
            },
            "energy": {
                "key_questions": [
                    "When does solar/battery reach true abundance?",
                    "Nuclear renaissance: real or vaporware?",
                    "How does AI energy demand reshape the grid?",
                    "Energy weaponization escalation path?",
                ],
                "family_implications": [
                    "Energy independence for property",
                    "Investment positioning in energy transition",
                    "Geographic selection for energy reliability",
                ],
            },
            "demographics": {
                "key_questions": [
                    "Which countries face demographic collapse first?",
                    "Does AI substitute for missing workers?",
                    "Immigration policy trajectory?",
                    "Does pro-natalist policy work?",
                ],
                "family_implications": [
                    "Large family as strategic advantage in low-fertility world",
                    "Community building with aligned families",
                    "Positioning children for demographic-scarce roles",
                ],
            },
            "capital_markets": {
                "key_questions": [
                    "Inflation vs. deflation in AI economy?",
                    "Which asset classes survive regime change?",
                    "Dollar reserve status trajectory?",
                    "Crypto: integration or marginalization?",
                ],
                "family_implications": [
                    "Multi-decade asset allocation",
                    "Income stream diversification",
                    "Generational wealth transfer strategy",
                ],
            },
            "health_longevity": {
                "key_questions": [
                    "When does longevity escape velocity arrive?",
                    "GLP-1 revolution: how far does it extend?",
                    "AI-accelerated drug discovery impact?",
                    "Healthcare access: democratization or bifurcation?",
                ],
                "family_implications": [
                    "Longevity protocol adoption for family",
                    "Biotech investment positioning",
                    "Children's health optimization from birth",
                    "Healthcare access strategy",
                ],
            },
        }

        themes = []
        for name in CANONICAL_THEMES:
            config = defaults.get(name, {})
            themes.append(Theme(
                name=name,
                display_name=THEME_DISPLAY_NAMES.get(name, name),
                key_questions=config.get("key_questions", []),
                family_implications=config.get("family_implications", []),
            ))

        tmap = ThematicMap(themes=themes)
        self.save(tmap)
        return tmap

    def update_assessment(self, tmap: ThematicMap, theme_name: str, assessment: str) -> None:
        theme = tmap.get_theme(theme_name)
        if theme is None:
            raise ValueError(f"Theme '{theme_name}' not found")
        theme.current_assessment = assessment
        theme.last_updated = date.today().isoformat()
        self.save(tmap)
