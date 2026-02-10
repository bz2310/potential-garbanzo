"""Extractor — use LLM to extract claims and score significance."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from outlook.engines.llm_client import LLMClient
from outlook.engines.scanner import FeedItem
from outlook.models.source import Claim, Source
from outlook.models.theme import CANONICAL_THEMES

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an intelligence analyst extracting structured claims from articles.

The reader is a strategically-minded quant.
She tracks 9 thematic domains to orient her family for survivability, durable control/power,
and health/longevity, especially in the rapidly-changing world shaped by AI. 

The 9 themes are:
1. ai_foundation_models — capability trajectory, scaling, alignment, new developments (world models, etc.)
2. ai_applications — economic impact, labor displacement, new industries
3. ai_supply_chain — chips, compute, NVIDIA, TSMC, export controls, new processor component developments
4. robotics — humanoids, drones, physical automation
5. geopolitics — US vs China AI and robotics developments
6. energy — solar, nuclear, grid, AI energy demand
7. capital_markets — asset regimes, inflation, dollar, crypto
8. health_longevity — GLP-1s, gene therapy, longevity, biotech, actionable health findings

IMPORTANT for all articles: make sure the articles are either 1) some think-piece talking about a kind of novel long-range prediction about the world. 
Or 2) some news about a concrete development (new AI model, new chip, new geopolitical event, new drug approval, etc.) that have a significant impact on the future.
Ignore purely theoretical articles that don't have concrete implications for the future.

IMPORTANT for health_longevity: Focus on findings that are practically actionable for a
family — new treatments available or coming to market, dietary/supplement evidence with
human trial data, screening recommendations, drug approvals, clinical guidelines. Ignore
purely theoretical research (animal studies, mechanistic discoveries in model organisms)
unless they have near-term clinical implications. Score theoretical/animal studies as
significance 1-2 (noise/minor).

For the article below, extract:

1. A 2-3 paragraph summary of the key arguments
2. A list of discrete claims (assertions about the future or present state)
3. For each claim:
   - text: the core assertion (one sentence)
   - theme: which of the 9 themes it maps to
   - confidence: the author's apparent confidence (high/medium/low)
   - significance: 1-5 how important this is for someone tracking these themes
     (5 = paradigm-shifting, 4 = major signal, 3 = notable, 2 = minor, 1 = noise)
   - actionable: whether this suggests a concrete family-level action
   - action_suggestion: if actionable, what the action is

Return ONLY valid JSON with this structure:
{{
  "title": "...",
  "author": "...",
  "summary": "bullet-pointed summary of novel, important points",
  "date_published": "YYYY-MM-DD or empty string",
  "themes": ["theme1", "theme2"],
  "credibility_notes": "brief source credibility assessment",
  "overall_significance": 1-5,
  "claims": [
    {{
      "text": "...",
      "theme": "ai_foundation_models",
      "confidence": "high",
      "significance": 4,
      "actionable": false,
      "action_suggestion": ""
    }}
  ]
}}

ARTICLE SOURCE: {source_name}
ARTICLE URL: {url}
ARTICLE TITLE: {title}
ARTICLE CONTENT:
{content}"""


class Extractor:
    """Extract claims from articles using an LLM (Anthropic or OpenAI)."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, item: FeedItem) -> Optional[Source]:
        if not item.content or len(item.content.strip()) < 100:
            logger.info(f"Skipping {item.url} — too little content")
            return None

        prompt = EXTRACTION_PROMPT.format(
            source_name=item.source_name,
            url=item.url,
            title=item.title,
            content=item.content[:12000],  # stay within reasonable token budget
        )

        try:
            text = self.llm.complete(prompt, max_tokens=4096)

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]

            data = json.loads(text)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse JSON from extraction for {item.url}")
            return None
        except Exception:
            logger.exception(f"API call failed for {item.url}")
            return None

        claims = []
        for cd in data.get("claims", []):
            theme = cd.get("theme", "")
            if theme not in CANONICAL_THEMES:
                # Try to fuzzy match
                for ct in CANONICAL_THEMES:
                    if theme.replace(" ", "_").lower() in ct or ct in theme.replace(" ", "_").lower():
                        theme = ct
                        break
                else:
                    theme = item.themes[0] if item.themes else "ai_foundation_models"

            claims.append(Claim(
                text=cd.get("text", ""),
                theme=theme,
                confidence=cd.get("confidence", "medium"),
                significance=cd.get("significance", 1),
                actionable=cd.get("actionable", False),
                action_suggestion=cd.get("action_suggestion", ""),
            ))

        raw_summary = data.get("summary", "")
        if isinstance(raw_summary, list):
            raw_summary = "\n".join(str(s) for s in raw_summary)

        source = Source(
            url=item.url,
            title=data.get("title", item.title),
            author=data.get("author", item.author),
            date_published=data.get("date_published", ""),
            summary=raw_summary,
            claims=claims,
            themes=data.get("themes", item.themes),
            significance=data.get("overall_significance", max((c.significance for c in claims), default=1)),
            credibility_notes=data.get("credibility_notes", ""),
        )
        return source

    def extract_batch(
        self, items: list[FeedItem], significance_threshold: int = 4,
        published_cutoff: datetime | None = None,
    ) -> tuple[list[Source], list[Source]]:
        """Extract claims from multiple items. Returns (kept, rejected)."""
        kept: list[Source] = []
        rejected: list[Source] = []
        seen_urls: set[str] = set()
        for item in items:
            if item.url in seen_urls:
                logger.debug(f"Skipping duplicate URL: {item.url}")
                continue
            seen_urls.add(item.url)

            source = self.extract(item)
            if not source:
                continue

            logger.info(f"Title: {source.title} URL: {source.url}")

            # Filter old articles (especially from web scraper where dates
            # aren't available until the LLM extracts them from content)
            if published_cutoff and source.date_published:
                try:
                    pub_dt = datetime.fromisoformat(
                        source.date_published.replace("Z", "+00:00")
                    )
                    if pub_dt.tzinfo is None:
                        from datetime import timezone
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    if pub_dt < published_cutoff:
                        logger.info(
                            f"Skipping old article: {source.title} ({source.date_published})"
                        )
                        continue
                except (ValueError, TypeError):
                    pass  # Unparseable date — let it through

            if source.significance >= significance_threshold:
                kept.append(source)
                logger.info(f"Kept: {source.title} (significance {source.significance})")
            else:
                rejected.append(source)
                logger.info(f"Below threshold: {source.title} (significance {source.significance})")
        return kept, rejected
