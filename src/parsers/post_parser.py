"""HTML parser for Reddit posts."""

import re
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup, Tag

from src.models.post import RedditPost


class PostParser:
    """Parse post cards/details from old.reddit HTML."""

    def parse_listing(self, soup: BeautifulSoup, subreddit: str, limit: int = 25) -> list[RedditPost]:
        posts: list[RedditPost] = []
        post_elements = soup.select("div.thing[data-fullname^='t3_']")
        for element in post_elements:
            post = self._parse_post_element(element, subreddit)
            if post:
                posts.append(post)
            if len(posts) >= limit:
                break
        return posts

    def parse_single_post(self, soup: BeautifulSoup, subreddit: str) -> Optional[RedditPost]:
        element = soup.select_one("div.thing.link[data-fullname^='t3_']")
        return self._parse_post_element(element, subreddit) if element else None

    def _parse_post_element(self, element: Tag, subreddit: str) -> Optional[RedditPost]:
        try:
            post_fullname = element.get("data-fullname", "")
            post_id = post_fullname.replace("t3_", "") or element.get("id", "").replace("thing_t3_", "")
            if not post_id:
                return None

            title_elem = element.select_one("a.title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            if not title:
                return None

            author_elem = element.select_one("a.author")
            author = author_elem.get_text(strip=True) if author_elem else "[deleted]"

            permalink = element.get("data-permalink") or ""
            if not permalink:
                comments_link = element.select_one("a.comments")
                permalink = comments_link.get("href", "") if comments_link else ""
            permalink = permalink if permalink.startswith("/r/") else f"/r/{subreddit}/comments/{post_id}/"

            raw_url = element.get("data-url") or (title_elem.get("href", "") if title_elem else "")
            if not raw_url.startswith("http"):
                url = f"https://old.reddit.com{raw_url}" if raw_url.startswith("/") else f"https://old.reddit.com{permalink}"
            else:
                url = raw_url

            domain = element.get("data-domain")
            is_self = bool(domain and domain.startswith("self."))
            selftext = None
            link_url = None if is_self else url

            score_elem = element.select_one("div.score.unvoted") or element.select_one("div.score")
            score = self._parse_score(score_elem.get_text(strip=True) if score_elem else "0")

            comments_elem = element.select_one("a.comments")
            num_comments = self._parse_number(comments_elem.get_text(strip=True) if comments_elem else "0")

            created_utc = datetime.now(tz=timezone.utc)
            time_elem = element.select_one("time")
            if time_elem and time_elem.get("datetime"):
                created_utc = datetime.fromisoformat(time_elem["datetime"].replace("Z", "+00:00"))

            flair_elem = element.select_one("span.linkflairlabel")
            flair = flair_elem.get_text(strip=True) if flair_elem else None

            classes = element.get("class", [])
            is_nsfw = "over18" in classes
            is_locked = "locked" in classes
            is_stickied = "stickied" in classes

            thumbnail_url = None
            thumb_img = element.select_one("a.thumbnail img")
            if thumb_img and thumb_img.get("src", "").startswith("http"):
                thumbnail_url = thumb_img["src"]

            return RedditPost(
                id=post_id,
                title=title,
                author=author,
                subreddit=subreddit,
                url=url,
                permalink=permalink,
                selftext=selftext,
                link_url=link_url,
                is_self=is_self,
                score=score,
                num_comments=num_comments,
                created_utc=created_utc,
                flair=flair,
                is_nsfw=is_nsfw,
                is_locked=is_locked,
                is_stickied=is_stickied,
                domain=domain,
                thumbnail_url=thumbnail_url,
            )
        except Exception:
            return None

    @staticmethod
    def _parse_score(text: str) -> int:
        normalized = text.lower().strip().replace("points", "").replace("point", "")
        if not normalized or normalized in {"•", "score hidden"}:
            return 0
        multiplier = 1
        if normalized.endswith("k"):
            multiplier = 1000
            normalized = normalized[:-1]
        elif normalized.endswith("m"):
            multiplier = 1_000_000
            normalized = normalized[:-1]
        try:
            return int(float(normalized) * multiplier)
        except ValueError:
            return 0

    @staticmethod
    def _parse_number(text: str) -> int:
        match = re.search(r"(\d+)", text.replace(",", ""))
        return int(match.group(1)) if match else 0
