"""Agent-style post payload (camelCase) for NestJS / main app consumers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.post import PostsResponse


class AgentPostItem(BaseModel):
    """Matches main-app Reddit post shape; relevanceScore omitted per request."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(description="Sequential id in this response page (not DB id)")
    reddit_post_id: str = Field(serialization_alias="redditPostId")
    title: str
    selftext: str = ""
    author: str
    subreddit: str
    score: int
    num_comments: int = Field(serialization_alias="numComments")
    permalink: str = Field(description="Full Reddit thread URL")
    status: str = "new"
    keyword: str = ""
    reddit_created_at: datetime = Field(serialization_alias="redditCreatedAt")
    found_at: datetime = Field(serialization_alias="foundAt")


class AgentPostsResponse(BaseModel):
    subreddit: str
    sort_by: str
    time_filter: Optional[str] = None
    posts: list[AgentPostItem]
    count: int
    scraped_at: datetime


def posts_response_to_agent(
    pr: PostsResponse,
    *,
    keyword: str = "",
    id_offset: int = 0,
) -> AgentPostsResponse:
    """Map internal PostsResponse to agent-style items."""
    items: list[AgentPostItem] = []
    for i, p in enumerate(pr.posts):
        thread_url = str(p.url) if p.url else f"https://www.reddit.com{p.permalink}"
        items.append(
            AgentPostItem(
                id=id_offset + i + 1,
                reddit_post_id=p.id,
                title=p.title,
                selftext=p.selftext or "",
                author=p.author,
                subreddit=p.subreddit,
                score=p.score,
                num_comments=p.num_comments,
                permalink=thread_url,
                status="new",
                keyword=keyword,
                reddit_created_at=p.created_utc,
                found_at=p.scraped_at,
            )
        )
    return AgentPostsResponse(
        subreddit=pr.subreddit,
        sort_by=pr.sort_by,
        time_filter=pr.time_filter,
        posts=items,
        count=len(items),
        scraped_at=pr.scraped_at,
    )
