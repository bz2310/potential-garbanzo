"""Feed scanner — crawl RSS feeds, subreddits, and web pages for new content.

Uses stdlib xml.etree instead of feedparser to avoid sgmllib3k build issues on Python 3.11+.
"""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_HOURS = 12


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

    def scan_all(self, feeds: list[FeedConfig], lookback_hours: int = DEFAULT_LOOKBACK_HOURS) -> list[FeedItem]:
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
        """Parse RSS/Atom feeds using stdlib xml.etree."""
        items: list[FeedItem] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        try:
            resp = requests.get(
                feed.url,
                timeout=self.request_timeout,
                headers={"User-Agent": "FutureOutlookAgent/1.0"},
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch RSS: {feed.url}")
            return items

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            logger.exception(f"Failed to parse XML from {feed.url}")
            return items

        # Handle both RSS 2.0 and Atom feeds
        entries = self._extract_rss_entries(root, feed)

        for entry in entries[: feed.max_items]:
            url = entry.get("url", "")
            if not url or self._is_seen(url):
                continue

            # Check date — skip entries with no parseable date
            published = entry.get("published", "")
            pub_dt = None
            if published:
                try:
                    pub_dt = parsedate_to_datetime(published)
                except (TypeError, ValueError):
                    try:
                        pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except (TypeError, ValueError):
                        pass

            if pub_dt:
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
                published = pub_dt.isoformat()
            else:
                # No date or unparseable — skip to avoid dumping old articles
                logger.debug(f"Skipping {url} — no parseable date")
                continue

            content = entry.get("content", "")
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
                content=content[:15000],
                source_name=feed.name,
                themes=feed.themes,
            ))
            self._mark_seen(url)

        return items

    def _extract_rss_entries(self, root: ET.Element, feed: FeedConfig) -> list[dict]:
        """Extract entries from RSS 2.0 or Atom XML."""
        entries = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # Try RSS 2.0: <channel><item>
        for item in root.iter("item"):
            entry = {
                "url": self._xml_text(item, "link") or "",
                "title": self._xml_text(item, "title") or "",
                "author": self._xml_text(item, "author") or self._xml_text(item, "dc:creator") or feed.name,
                "published": self._xml_text(item, "pubDate") or "",
                "content": self._xml_text(item, "content:encoded")
                           or self._xml_text(item, "description") or "",
            }
            if entry["url"]:
                entries.append(entry)

        # Try Atom: <entry>
        if not entries:
            for item in root.iter("{http://www.w3.org/2005/Atom}entry"):
                link_el = item.find("{http://www.w3.org/2005/Atom}link[@rel='alternate']")
                if link_el is None:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                url = link_el.get("href", "") if link_el is not None else ""

                author_el = item.find("{http://www.w3.org/2005/Atom}author")
                author = ""
                if author_el is not None:
                    name_el = author_el.find("{http://www.w3.org/2005/Atom}name")
                    author = name_el.text if name_el is not None and name_el.text else feed.name

                content_el = item.find("{http://www.w3.org/2005/Atom}content")
                summary_el = item.find("{http://www.w3.org/2005/Atom}summary")
                content = ""
                if content_el is not None and content_el.text:
                    content = content_el.text
                elif summary_el is not None and summary_el.text:
                    content = summary_el.text

                published_el = item.find("{http://www.w3.org/2005/Atom}published")
                updated_el = item.find("{http://www.w3.org/2005/Atom}updated")
                published = ""
                if published_el is not None and published_el.text:
                    published = published_el.text
                elif updated_el is not None and updated_el.text:
                    published = updated_el.text

                entry = {
                    "url": url,
                    "title": self._xml_text_ns(item, "title", ns) or "",
                    "author": author or feed.name,
                    "published": published,
                    "content": content,
                }
                if entry["url"]:
                    entries.append(entry)

        return entries

    @staticmethod
    def _xml_text(el: ET.Element, tag: str) -> Optional[str]:
        """Get text of a child element, handling namespaced tags gracefully."""
        child = el.find(tag)
        if child is None:
            # Try with common RSS namespaces
            for prefix, uri in [("content", "http://purl.org/rss/1.0/modules/content/"),
                                ("dc", "http://purl.org/dc/elements/1.1/")]:
                if tag.startswith(prefix + ":"):
                    local = tag.split(":", 1)[1]
                    child = el.find(f"{{{uri}}}{local}")
                    if child is not None:
                        break
        if child is not None and child.text:
            return child.text
        return None

    @staticmethod
    def _xml_text_ns(el: ET.Element, tag: str, ns: dict) -> Optional[str]:
        child = el.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
        if child is not None and child.text:
            return child.text
        return None

    def _scan_reddit(self, feed: FeedConfig, lookback_hours: int) -> list[FeedItem]:
        items: list[FeedItem] = []
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
            if post_url.startswith("/"):
                post_url = "https://www.reddit.com" + post_url
            permalink = "https://reddit.com" + pd.get("permalink", "")
            created = pd.get("created_utc", 0)

            if created < cutoff_ts:
                continue

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

    # Paths that are almost never articles
    _NON_ARTICLE_PATHS = {
        "about", "contact", "privacy", "terms", "tag", "tags", "category",
        "categories", "author", "authors", "page", "login", "signup",
        "search", "faq", "subscribe", "newsletter", "careers", "team",
        "advertise", "sitemap", "feed", "rss", "legal", "cookies",
        "archive", "archives",
    }

    def _scan_web(self, feed: FeedConfig) -> list[FeedItem]:
        """Scrape a blog/index page, discover article links, fetch unseen ones."""
        from urllib.parse import urlparse, urljoin

        items: list[FeedItem] = []
        try:
            resp = requests.get(
                feed.url,
                timeout=self.request_timeout,
                headers={"User-Agent": "FutureOutlookAgent/1.0"},
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch web page: {feed.url}")
            return items

        soup = BeautifulSoup(resp.text, "html.parser")
        base_domain = urlparse(feed.url).netloc
        base_path = urlparse(feed.url).path.rstrip("/")
        candidate_urls: list[str] = []

        for a_tag in soup.find_all("a", href=True):
            href = urljoin(feed.url, a_tag["href"])
            parsed = urlparse(href)
            path = parsed.path.rstrip("/")
            segments = [s for s in path.split("/") if s]

            if parsed.netloc != base_domain or path == "/" or not segments:
                continue
            if parsed.path.endswith((".css", ".js", ".png", ".jpg", ".svg", ".xml", ".pdf")):
                continue

            # Skip non-article paths
            if segments[0].lower() in self._NON_ARTICLE_PATHS:
                continue

            # Require either 2+ path segments (e.g. /blog/my-post) or a long slug
            # (e.g. /my-really-interesting-article-about-ai)
            is_deep = len(segments) >= 2
            is_slug = len(segments[-1]) > 20
            if not is_deep and not is_slug:
                continue

            clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            # Don't include the feed URL itself
            if clean_url.rstrip("/") == feed.url.rstrip("/"):
                continue
            if clean_url not in candidate_urls:
                candidate_urls.append(clean_url)

        # Blog pages typically list newest first — only try the first 5
        max_fetches = min(5, feed.max_items)
        fetched = 0
        for url in candidate_urls:
            if fetched >= max_fetches:
                break
            if self._is_seen(url):
                continue
            fetched += 1

            # Fetch the article page and get its own title
            try:
                art_resp = requests.get(
                    url,
                    timeout=self.request_timeout,
                    headers={"User-Agent": "FutureOutlookAgent/1.0"},
                )
                art_resp.raise_for_status()
                art_soup = BeautifulSoup(art_resp.text, "html.parser")
                for tag in art_soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                title_tag = art_soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else feed.name
                text = art_soup.get_text(separator="\n", strip=True)
            except Exception:
                logger.exception(f"Failed to fetch article: {url}")
                self._mark_seen(url)
                continue

            if len(text.strip()) < 200:
                self._mark_seen(url)
                continue

            items.append(FeedItem(
                url=url,
                title=title,
                author=feed.name,
                published=datetime.now(timezone.utc).isoformat(),
                content=text[:15000],
                source_name=feed.name,
                themes=feed.themes,
            ))
            self._mark_seen(url)

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
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text
        except requests.exceptions.HTTPError as e:
            # Paywalled / forbidden pages are expected (e.g. Bloomberg)
            logger.debug(f"Could not fetch {url}: {e}")
            return None
        except Exception:
            logger.exception(f"Failed to fetch {url}")
            return None
