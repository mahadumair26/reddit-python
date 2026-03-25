"""Parser for subreddit metadata and rules."""

import re

from bs4 import BeautifulSoup

from src.models.subreddit import SubredditInfo, SubredditRule


class SubredditParser:
    """Parse subreddit data from old.reddit HTML pages."""

    def parse_subreddit_info(self, soup: BeautifulSoup, subreddit: str) -> SubredditInfo:
        header = soup.select_one("span.pagename.redditname a")
        display_name = header.get_text(strip=True) if header else f"r/{subreddit}"

        title_elem = soup.select_one("title")
        title = title_elem.get_text(strip=True) if title_elem else display_name

        description_elem = soup.select_one("div.side div.md")
        description = description_elem.get_text(" ", strip=True) if description_elem else None

        subscribers = self._parse_stat_number(soup, "subscribers")
        active_users = self._parse_stat_number(soup, "users here now")
        is_nsfw = bool(soup.select_one("span.nsfw-stamp") or soup.select_one("div.over18"))

        return SubredditInfo(
            name=subreddit,
            display_name=display_name.replace("r/", ""),
            title=title,
            description=description,
            subscribers=subscribers or 0,
            active_users=active_users,
            is_nsfw=is_nsfw,
            rules=[],
        )

    def parse_rules(self, soup: BeautifulSoup) -> list[SubredditRule]:
        rules: list[SubredditRule] = []
        items = soup.select("div.md ol li, div.md ul li")
        for idx, item in enumerate(items):
            text = item.get_text(" ", strip=True)
            if not text:
                continue
            rules.append(SubredditRule(short_name=text[:100], description=text, priority=idx + 1))
        return rules

    @staticmethod
    def _parse_stat_number(soup: BeautifulSoup, label: str) -> int | None:
        candidate = soup.find(string=re.compile(label, re.IGNORECASE))
        if not candidate:
            return None
        nearby = candidate.parent.get_text(" ", strip=True)
        digits = re.search(r"([\d,]+)", nearby)
        return int(digits.group(1).replace(",", "")) if digits else None
