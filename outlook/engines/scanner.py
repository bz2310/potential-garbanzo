"""Feed scanner — crawl RSS feeds, subreddits, and web pages for new content."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    url: str = ""
    title: str = ""
    author: str = ""
    published: str = ""
    content: str = ""
    source_name: str = ""
    themes: list[str] = field(default_factory=list)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]


@dataclass
class FeedConfig:
    name: str = ""
    url: str = ""
    feed_type: str = "rss"  # rss, reddit, web
    themes: list[str] = field(default_factory=list)
    max_items: int = 10

    @classmethod
    def from_dict(cls, d: dict) -> FeedConfig:
        return cls(
            name=d.get("name", ""),
            url=d.get("url", ""),
            feed_type=d.get("feed_type", "rss"),
            themes=d.get("themes", []),
            max_items=d.get("max_items", 10),
        )


class Scanner:
    """Crawl configured feeds and return new items."""

    def __init__(self, seen_path: Path, request_timeout: int = 30):
        self.seen_path = seen_path
        self.request_timeout = request_timeout
        self._seen: set[str] = set()
        self._load_seen()

    def _load_seen(self) -> None:
        if self.seen_path.exists():
            data = yaml.safe_load(self.seen_path.read_text()) or []
            self._seen = set(data)

    def _save_seen(self) -> None:
        self.seen_path.parent.mkdir(parents=True, exist_ok=True)
        self.seen_path.write_text(yaml.dump(sorted(self._seen), default_flow_style=False))

    def _mark_seen(self, url: str) -> None:
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        self._seen.add(h)

    def _is_seen(self, url: str) -> bool:
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        return h in self._seen

    def scan_all(self, feeds: list[FeedConfig], lookback_hours: int = 12) -> list[FeedItem]:
        all_items: list[FeedItem] = []
        for feed in feeds:
            try:
                if feed.feed_type == "rss":
                    items = self._scan_rss(feed, lookback_hours)
                elif feed.feed_type == "reddit":
                    items = self._scan_reddit(feed, lookback_hours)
                elif feed.feed_type == "web":
                    items = self._scan_web(feed)
                else:
                    logger.warning(f"Unknown feed type: {feed.feed_type} for {feed.name}")
                    continue
                all_items.extend(items)
            except Exception:
                logger.exception(f"Failed to scan {feed.name} ({feed.url})")
        self._save_seen()
        return all_items

    def _scan_rss(self, feed: FeedConfig, lookback_hours: int) -> list[FeedItem]:
        items: list[FeedItem] = []
        parsed = feedparser.parse(feed.url)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        for entry in parsed.entries[: feed.max_items]:
            url = entry.get("link", "")
            if not url or self._is_seen(url):
                continue

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if dt < cutoff:
                        continue
                    published = dt.isoformat()
                except (TypeError, ValueError):
                    pass

            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content = entry.get("summary", "")

            if content:
                content = BeautifulSoup(content, "html.parser").get_text(separator="\n")

            # If RSS content is just a snippet, fetch the full page
            if len(content) < 500:
                full = self._fetch_page_text(url)
                if full:
                    content = full

            items.append(FeedItem(
                url=url,
                title=entry.get("title", ""),
                author=entry.get("author", feed.name),
                published=published,
                content=content[:15000],  # cap to avoid huge payloads
                source_name=feed.name,
                themes=feed.themes,
            ))
            self._mark_seen(url)

        return items

    def _scan_reddit(self, feed: FeedConfig, lookback_hours: int) -> list[FeedItem]:
        items: list[FeedItem] = []
        # Use Reddit's JSON API
        url = feed.url.rstrip("/") + "/hot.json?limit=25"
        headers = {"User-Agent": "FutureOutlookAgent/1.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=self.request_timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception(f"Failed to fetch Reddit: {feed.url}")
            return items

        cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp()

        for post in data.get("data", {}).get("children", []):
            pd = post.get("data", {})
            post_url = pd.get("url", "")
            permalink = "https://reddit.com" + pd.get("permalink", "")
            created = pd.get("created_utc", 0)

            if created < cutoff_ts:
                continue

            # Use the linked URL if external, otherwise the reddit post
            target_url = post_url if not post_url.startswith("https://www.reddit.com") else permalink
            if self._is_seen(target_url):
                continue

            content = pd.get("selftext", "")
            if not content and post_url and not post_url.startswith("https://www.reddit.com"):
                content = self._fetch_page_text(post_url) or ""

            items.append(FeedItem(
                url=target_url,
                title=pd.get("title", ""),
                author=pd.get("author", ""),
                published=datetime.fromtimestamp(created, tz=timezone.utc).isoformat(),
                content=content[:15000],
                source_name=feed.name,
                themes=feed.themes,
            ))
            self._mark_seen(target_url)

        return items[:feed.max_items]

    def _scan_web(self, feed: FeedConfig) -> list[FeedItem]:
        """Scrape a web page for article links — simple heuristic."""
        items: list[FeedItem] = []
        text = self._fetch_page_text(feed.url)
        if not text:
            return items

        # For web pages, we just return the page itself as one item
        if not self._is_seen(feed.url):
            items.append(FeedItem(
                url=feed.url,
                title=feed.name,
                author=feed.name,
                published=datetime.now(timezone.utc).isoformat(),
                content=text[:15000],
                source_name=feed.name,
                themes=feed.themes,
            ))
            self._mark_seen(feed.url)

        return items

    def _fetch_page_text(self, url: str) -> Optional[str]:
        try:
            resp = requests.get(
                url,
                timeout=self.request_timeout,
                headers={"User-Agent": "FutureOutlookAgent/1.0"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove script/style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text
        except Exception:
            logger.exception(f"Failed to fetch {url}")
            return None
