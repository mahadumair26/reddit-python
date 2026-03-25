"""HTTP routes for scraper service."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_reddit_scraper
from src.models import CommentsResponse, PostsResponse, SubredditInfo
from src.scrapers.reddit_scraper import RedditScraper

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    """Service heartbeat endpoint."""
    return {"status": "ok"}


@router.get("/subreddit/{name}/posts", response_model=PostsResponse)
async def get_subreddit_posts(
    name: str,
    sort_by: str = Query(default="hot", pattern="^(hot|new|top|rising)$"),
    time_filter: Optional[str] = Query(default=None, pattern="^(hour|day|week|month|year|all)$"),
    limit: int = Query(default=25, ge=1, le=100),
    scraper: RedditScraper = Depends(get_reddit_scraper),
) -> PostsResponse:
    return await scraper.get_subreddit_posts(name, sort_by=sort_by, time_filter=time_filter, limit=limit)


@router.get("/post/{post_id}", response_model=CommentsResponse)
async def get_post_comments(
    post_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    scraper: RedditScraper = Depends(get_reddit_scraper),
) -> CommentsResponse:
    return await scraper.get_post_comments(post_id, limit=limit)


@router.get("/subreddit/{name}/rules", response_model=SubredditInfo)
async def get_subreddit_rules(
    name: str, scraper: RedditScraper = Depends(get_reddit_scraper)
) -> SubredditInfo:
    return await scraper.get_subreddit_info(name)
