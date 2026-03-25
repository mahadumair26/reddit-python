"""Reddit post models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class RedditPost(BaseModel):
    id: str = Field(..., description="Reddit post ID")
    title: str
    author: str
    subreddit: str
    url: HttpUrl
    permalink: str

    selftext: Optional[str] = None
    link_url: Optional[HttpUrl] = None
    is_self: bool

    score: int
    upvote_ratio: Optional[float] = None
    num_comments: int = 0
    created_utc: datetime

    flair: Optional[str] = None
    is_nsfw: bool = False
    is_spoiler: bool = False
    is_locked: bool = False
    is_stickied: bool = False
    domain: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class PostsResponse(BaseModel):
    subreddit: str
    sort_by: str
    time_filter: Optional[str] = None
    posts: list[RedditPost]
    count: int
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
