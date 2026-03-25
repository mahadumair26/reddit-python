# How This API Works

Endpoint you called:

`http://127.0.0.1:8000/api/v1/subreddit/Recruitment/posts?sort_by=hot&limit=25`

## 1) What this request means

- `subreddit=Recruitment` comes from the path `/subreddit/Recruitment/posts`
- `sort_by=hot` means fetch "hot" posts
- `limit=25` means return up to 25 posts

Internally this maps to:

- Route: `GET /api/v1/subreddit/{name}/posts`
- Handler function: `get_subreddit_posts(...)` in `src/api/routes.py`
- Scraper method: `RedditScraper.get_subreddit_posts(...)` in `src/scrapers/reddit_scraper.py`

## 2) Request validation (FastAPI)

Before scraping starts, FastAPI validates query params:

- `sort_by` must be one of: `hot | new | top | rising`
- `time_filter` (optional) must be one of: `hour | day | week | month | year | all`
- `limit` must be between `1` and `100`

So your call is valid:

- `sort_by=hot` ✅
- `limit=25` ✅

## 3) End-to-end flow inside service

1. FastAPI receives the request in `src/main.py`.
2. Router dispatches it to `get_subreddit_posts(...)` in `src/api/routes.py`.
3. Dependency injection provides a singleton `RedditScraper` instance from `src/api/dependencies.py`.
4. `RedditScraper.get_subreddit_posts(...)`:
   - clamps limit with `MAX_POSTS_PER_REQUEST`
   - checks Redis cache key:
     - `posts:Recruitment:hot:None:25`
   - if cache miss, builds old Reddit URL:
     - `https://old.reddit.com/r/Recruitment/hot/`
   - calls base scraper `_request(...)`
5. `BaseScraper._request(...)` in `src/scrapers/base.py`:
   - applies rate limiting (`rate_limiter.acquire()`)
   - sends HTTP request with rotated user-agent
   - retries on network/HTTP errors with exponential backoff
   - stores HTML in cache when successful
6. HTML is parsed by `PostParser.parse_listing(...)` in `src/parsers/post_parser.py`.
7. Parsed posts are converted into `RedditPost` models and wrapped in `PostsResponse`.
8. JSON response is returned to you.

## 4) Response shape

The endpoint returns a `PostsResponse` object:

```json
{
  "subreddit": "Recruitment",
  "sort_by": "hot",
  "time_filter": null,
  "posts": [
    {
      "id": "...",
      "title": "...",
      "author": "...",
      "subreddit": "Recruitment",
      "url": "https://...",
      "permalink": "/r/Recruitment/comments/...",
      "selftext": null,
      "link_url": "https://...",
      "is_self": false,
      "score": 123,
      "upvote_ratio": null,
      "num_comments": 10,
      "created_utc": "2026-03-20T00:00:00+00:00",
      "flair": null,
      "is_nsfw": false,
      "is_spoiler": false,
      "is_locked": false,
      "is_stickied": false,
      "domain": "example.com",
      "thumbnail_url": null,
      "scraped_at": "2026-03-20T00:00:00+00:00"
    }
  ],
  "count": 25,
  "scraped_at": "2026-03-20T00:00:00+00:00"
}
```

## 5) Caching behavior

- Cache backend: Redis (`src/utils/cache.py`)
- Posts TTL: `CACHE_TTL_POSTS` (default `3600` seconds = 1 hour)
- If the same request is repeated within TTL, data is served from cache faster.

## 6) Important notes

- This service scrapes `old.reddit.com` HTML, not official Reddit API.
- Returned post count may be less than 25 if parser finds fewer valid post elements.
- If Reddit blocks/rate-limits temporarily, retries/backoff run automatically.

## 7) Quick test command

```bash
curl "http://127.0.0.1:8000/api/v1/subreddit/Recruitment/posts?sort_by=hot&limit=25"
```

