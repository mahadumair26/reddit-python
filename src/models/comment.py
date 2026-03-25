"""Reddit comment models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RedditComment(BaseModel):
    id: str
    author: str
    body: str
    score: int
    parent_id: Optional[str] = None
    depth: int = 0
    created_utc: datetime
    is_submitter: bool = False
    is_stickied: bool = False
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class CommentsResponse(BaseModel):
    post_id: str
    comments: list[RedditComment]
    count: int
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
