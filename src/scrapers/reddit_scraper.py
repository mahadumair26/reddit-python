"""Reddit scraper implementation using old.reddit HTML + reddit JSON for metadata."""

from datetime import datetime, timezone
from typing import Optional

from src.config.settings import settings
from src.models.comment import CommentsResponse
from src.models.post import PostsResponse
from src.models.subreddit import SubredditInfo, SubredditRule
from src.parsers.comment_parser import CommentParser
from src.parsers.post_parser import PostParser
from src.parsers.subreddit_parser import SubredditParser
from src.scrapers.base import BaseScraper
from src.utils.cache import cache


class RedditScraper(BaseScraper):
    """Scrapes posts, comments, and subreddit metadata."""

    def __init__(self) -> None:
        super().__init__()
        self.post_parser = PostParser()
        self.comment_parser = CommentParser()
        self.subreddit_parser = SubredditParser()

    async def get_subreddit_posts(
        self,
        subreddit: str,
        sort_by: str = "hot",
        time_filter: Optional[str] = None,
        limit: int = 25,
    ) -> PostsResponse:
        safe_limit = min(limit, settings.MAX_POSTS_PER_REQUEST)
        cache_key = f"posts:{subreddit}:{sort_by}:{time_filter}:{safe_limit}"
        cached = await cache.get(cache_key)
        if cached:
            return PostsResponse.model_validate(cached)

        # old.reddit uses /top/?t=<window> for time-scoped top posts.
        path = f"/r/{subreddit}/{sort_by}/"
        params = {"limit": safe_limit}
        if sort_by == "top" and time_filter:
            params["t"] = time_filter

        html = await self._request(
            self._build_url(path),
            params=params,
            use_cache=True,
            cache_ttl=settings.CACHE_TTL_POSTS,
        )
        soup = self._parse_html(html)
        posts = self.post_parser.parse_listing(soup, subreddit=subreddit, limit=safe_limit)

        payload = PostsResponse(
            subreddit=subreddit,
            sort_by=sort_by,
            time_filter=time_filter,
            posts=posts,
            count=len(posts),
            scraped_at=datetime.now(tz=timezone.utc),
        )
        await cache.set(cache_key, payload.model_dump(mode="json"), ttl=settings.CACHE_TTL_POSTS)
        return payload

    async def get_post_comments(self, post_id: str, limit: int = 100) -> CommentsResponse:
        safe_limit = min(limit, settings.MAX_COMMENTS_PER_POST)
        cache_key = f"comments:{post_id}:{safe_limit}"
        cached = await cache.get(cache_key)
        if cached:
            return CommentsResponse.model_validate(cached)

        # /comments/{id}/ works without subreddit in old.reddit.
        html = await self._request(
            self._build_url(f"/comments/{post_id}/"),
            use_cache=True,
            cache_ttl=settings.CACHE_TTL_POSTS,
        )
        soup = self._parse_html(html)
        comments = self.comment_parser.parse_comments(soup, max_comments=safe_limit)

        payload = CommentsResponse(
            post_id=post_id,
            comments=comments,
            count=len(comments),
            scraped_at=datetime.now(tz=timezone.utc),
        )
        await cache.set(cache_key, payload.model_dump(mode="json"), ttl=settings.CACHE_TTL_POSTS)
        return payload

    async def get_subreddit_info(self, subreddit: str) -> SubredditInfo:
        cache_key = f"subreddit:{subreddit}"
        cached = await cache.get(cache_key)
        if cached:
            return SubredditInfo.model_validate(cached)

        # Use reddit JSON endpoints for subreddit metadata (more stable than old.reddit HTML /about/).
        about_url = f"https://www.reddit.com/r/{subreddit}/about.json"
        about_payload = await self._request_json(
            about_url, use_cache=True, cache_ttl=settings.CACHE_TTL_SUBREDDIT
        )
        data = (about_payload or {}).get("data") or {}

        created_utc = None
        created_utc_ts = data.get("created_utc")
        if isinstance(created_utc_ts, (int, float)):
            created_utc = datetime.fromtimestamp(created_utc_ts, tz=timezone.utc)

        info = SubredditInfo(
            name=subreddit,
            display_name=data.get("display_name") or subreddit,
            title=data.get("title") or f"r/{subreddit}",
            description=data.get("public_description") or data.get("description") or None,
            subscribers=int(data.get("subscribers") or 0),
            active_users=data.get("active_user_count"),
            created_utc=created_utc,
            is_nsfw=bool(data.get("over18") or False),
            rules=[],
            scraped_at=datetime.now(tz=timezone.utc),
        )

        rules_url = f"https://www.reddit.com/r/{subreddit}/about/rules.json"
        rules_payload = await self._request_json(
            rules_url, use_cache=True, cache_ttl=settings.CACHE_TTL_SUBREDDIT
        )
        rules_list = (rules_payload or {}).get("rules") or []
        parsed_rules: list[SubredditRule] = []
        for idx, rule in enumerate(rules_list):
            if not isinstance(rule, dict):
                continue
            parsed_rules.append(
                SubredditRule(
                    short_name=rule.get("short_name") or f"Rule {idx+1}",
                    description=rule.get("description"),
                    violation_reason=rule.get("violation_reason"),
                    priority=int(rule.get("priority") or (idx + 1)),
                )
            )
        info.rules = parsed_rules

        await cache.set(cache_key, info.model_dump(mode="json"), ttl=settings.CACHE_TTL_SUBREDDIT)
        return info

    async def scrape(self, *args, **kwargs) -> PostsResponse:
        return await self.get_subreddit_posts(*args, **kwargs)
