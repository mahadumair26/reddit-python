"""Subreddit models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubredditRule(BaseModel):
    short_name: str
    description: Optional[str] = None
    violation_reason: Optional[str] = None
    priority: int = 0


class SubredditInfo(BaseModel):
    name: str
    display_name: str
    title: str
    description: Optional[str] = None
    subscribers: int = 0
    active_users: Optional[int] = None
    created_utc: Optional[datetime] = None
    is_nsfw: bool = False
    rules: list[SubredditRule] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
