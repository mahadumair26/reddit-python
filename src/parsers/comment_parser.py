"""HTML parser for Reddit comments."""

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag

from src.models.comment import RedditComment


class CommentParser:
    """Parse comments from old.reddit post pages."""

    def parse_comments(self, soup: BeautifulSoup, max_comments: int = 100) -> list[RedditComment]:
        comments: list[RedditComment] = []
        elements = soup.select("div.thing.comment[data-fullname^='t1_']")
        for element in elements:
            parsed = self._parse_comment_element(element)
            if parsed:
                comments.append(parsed)
            if len(comments) >= max_comments:
                break
        return comments

    def _parse_comment_element(self, element: Tag) -> RedditComment | None:
        comment_fullname = element.get("data-fullname", "")
        comment_id = comment_fullname.replace("t1_", "") or element.get("id", "").replace("thing_t1_", "")
        if not comment_id:
            return None

        author_elem = element.select_one("a.author")
        author = author_elem.get_text(strip=True) if author_elem else "[deleted]"

        body_elem = element.select_one("div.md")
        body = body_elem.get_text(" ", strip=True) if body_elem else ""

        score_elem = element.select_one("span.score.unvoted") or element.select_one("span.score")
        score = self._parse_score(score_elem.get_text(strip=True) if score_elem else "0")

        created_utc = datetime.now(tz=timezone.utc)
        time_elem = element.select_one("time")
        if time_elem and time_elem.get("datetime"):
            try:
                created_utc = datetime.fromisoformat(time_elem["datetime"].replace("Z", "+00:00"))
            except ValueError:
                pass

        depth = int(element.get("data-depth", "0") or 0)
        parent_id = element.get("data-parent-fullname")
        classes = element.get("class", [])

        return RedditComment(
            id=comment_id,
            author=author,
            body=body,
            score=score,
            parent_id=parent_id,
            depth=depth,
            created_utc=created_utc,
            is_submitter="submitter" in classes,
            is_stickied="stickied" in classes,
        )

    @staticmethod
    def _parse_score(text: str) -> int:
        normalized = text.lower().strip().replace("points", "").replace("point", "")
        match = re.search(r"-?\d+", normalized)
        return int(match.group(0)) if match else 0
