# Reddit Scraper Service

Standalone Python microservice for scraping public Reddit web pages.

## Stack
- FastAPI + Uvicorn
- HTTPX
- BeautifulSoup + lxml
- Redis (optional cache)
- Docker

## Quick Start
1. Create and activate a Python 3.11+ virtualenv.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env:
   - `cp .env.example .env`
4. Run service:
   - `uvicorn src.main:app --reload`

API docs: `http://localhost:8000/api/v1/docs`

## Current Endpoints
- `GET /api/v1/health`
- `GET /api/v1/subreddit/{name}/posts`
- `GET /api/v1/subreddit/{name}/posts/agent` — same posts, **camelCase** shape for the main agent (`redditPostId`, `numComments`, `redditCreatedAt`, `foundAt`, optional `keyword`)
- `GET /api/v1/post/{post_id}`
- `GET /api/v1/subreddit/{name}/rules`

## Notes
- Scraper orchestration, cache, retry, and rate-limit foundations are implemented.
- HTML parsing logic and full production scraping behavior can be layered in next.
