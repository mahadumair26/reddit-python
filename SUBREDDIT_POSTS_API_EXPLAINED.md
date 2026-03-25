# How the subreddit posts API works (detailed)

This document explains **end-to-end** what happens when you call:

```
https://reddit-python-production.up.railway.app/api/v1/subreddit/technology/posts?sort_by=hot&limit=25
```

The same logic applies on any host (local Docker, Render, etc.); only the **base URL** changes.

---

## 1. What you are calling

| Piece | Value |
|--------|--------|
| **Method** | `GET` |
| **Host** | Your deployed app (example: `reddit-python-production.up.railway.app`) |
| **Path** | `/api/v1/subreddit/technology/posts` |
| **Path parameter** | `technology` → subreddit name (without `r/`) |
| **Query** | `sort_by=hot`, `limit=25` |

So the server receives:

- **Subreddit**: `technology`
- **Sort**: hot feed
- **Max posts**: 25 (capped by config `MAX_POSTS_PER_REQUEST`, max 100 in the API)

---

## 2. How the URL maps to code

The app is created in `src/main.py` and mounts routes under a prefix from settings (default `API_PREFIX=/api/v1`).

The route is defined in `src/api/routes.py`:

```20:28:src/api/routes.py
@router.get("/subreddit/{name}/posts", response_model=PostsResponse)
async def get_subreddit_posts(
    name: str,
    sort_by: str = Query(default="hot", pattern="^(hot|new|top|rising)$"),
    time_filter: Optional[str] = Query(default=None, pattern="^(hour|day|week|month|year|all)$"),
    limit: int = Query(default=25, ge=1, le=100),
    scraper: RedditScraper = Depends(get_reddit_scraper),
) -> PostsResponse:
    return await scraper.get_subreddit_posts(name, sort_by=sort_by, time_filter=time_filter, limit=limit)
```

So for your URL:

- `name` = `technology`
- `sort_by` = `hot`
- `time_filter` = omitted → `None`
- `limit` = `25`

FastAPI injects a shared `RedditScraper` instance via `get_reddit_scraper` (`src/api/dependencies.py`).

---

## 3. Validation (before any scraping)

FastAPI validates query parameters **before** `get_subreddit_posts` runs:

- **`sort_by`**: must match `hot`, `new`, `top`, or `rising` (regex on the route).
- **`time_filter`** (optional): only used with `top`; must be `hour`, `day`, `week`, `month`, `year`, or `all` if provided.
- **`limit`**: integer between **1** and **100**.

Invalid values return **422 Unprocessable Entity** with a JSON error body (standard FastAPI validation).

---

## 4. What the scraper does (`RedditScraper.get_subreddit_posts`)

Implementation: `src/scrapers/reddit_scraper.py`.

### 4.1 Cache lookup (Redis)

A cache key is built:

```text
posts:technology:hot:None:25
```

If Redis is connected and this key exists, the cached JSON is deserialized into `PostsResponse` and returned **without** hitting Reddit.

If Redis is unavailable, cache reads/writes are skipped and the flow continues (fetch + parse).

### 4.2 upstream request (old.reddit HTML listing)

Production often **cannot** use Reddit’s public `*.json` listing (blocked or throttled for server IPs). This service therefore loads **HTML** from **old.reddit.com** (`REDDIT_BASE_URL`).

For `sort_by=hot` and subreddit `technology`:

- Path: `/r/technology/hot/`
- Query: `limit=25`

Example:

```text
https://old.reddit.com/r/technology/hot/?limit=25
```

For `sort_by=top` and `time_filter` set (e.g. `week`), the scraper adds `t=week`.

### 4.3 HTTP client behavior (`BaseScraper._request`)

In `src/scrapers/base.py`, `_request`:

- Uses a shared **`httpx.AsyncClient`** (async).
- Applies **rate limiting** (`rate_limiter.acquire()`) before each request.
- Sends a **rotating User-Agent** (`pick_user_agent()`).
- Retries on **HTTP/network errors** using **tenacity** (`AsyncRetrying`, exponential backoff).
- Optionally caches the **raw HTML** in Redis under a key derived from URL + params.

### 4.4 Parsing and selftext

`PostParser.parse_listing` reads each post card from the listing HTML. **`selftext`** is taken from **`div.expando div.md`** when Reddit embeds it on the listing.

If a **self post** still has no body (common), the scraper may fetch up to **`MAX_SELFTEXT_ENRICH_FETCH`** (default `10`) individual thread pages: `old.reddit.com/comments/{id}/`, parse the main post again, and copy **`selftext`**. This uses **HTML only** (no JSON listing). Set `MAX_SELFTEXT_ENRICH_FETCH=0` in env to disable extra fetches.

### 4.5 Response assembly

The scraper builds a **`PostsResponse`**:

- `subreddit`: `technology`
- `sort_by`: `hot`
- `time_filter`: `null` if omitted
- `posts`: list of `RedditPost`
- `count`: actual number of posts parsed (can be **less than** `limit` if the page has fewer items)
- `scraped_at`: UTC timestamp

The result is written to Redis (if available) with TTL `CACHE_TTL_POSTS` (default 1 hour), then returned as **JSON** to the client.

---

## 5. JSON response shape

The endpoint returns a JSON object matching `PostsResponse` + nested `RedditPost` models. Conceptually:

```json
{
  "subreddit": "technology",
  "sort_by": "hot",
  "time_filter": null,
  "posts": [
    {
      "id": "…",
      "title": "…",
      "author": "…",
      "subreddit": "technology",
      "url": "https://www.reddit.com/r/technology/comments/…",
      "permalink": "/r/technology/comments/…",
      "selftext": null,
      "link_url": "https://external-site.com/article",
      "is_self": false,
      "score": 123,
      "upvote_ratio": null,
      "num_comments": 45,
      "created_utc": "2026-01-01T12:00:00+00:00",
      "flair": null,
      "is_nsfw": false,
      "is_spoiler": false,
      "is_locked": false,
      "is_stickied": false,
      "domain": "…",
      "thumbnail_url": null,
      "scraped_at": "2026-03-20T00:00:00+00:00"
    }
  ],
  "count": 25,
  "scraped_at": "2026-03-20T00:00:00+00:00"
}
```

OpenAPI docs (if enabled):  
`https://reddit-python-production.up.railway.app/api/v1/docs`

### `url` vs `link_url` (important)

On Reddit, most **r/technology** “hot” items are **link posts**: the big title usually opens the **article** (e.g. howtogeek.com), while **comments** open the Reddit thread.

- **`url`** — Always the **Reddit discussion URL** (canonical `https://www.reddit.com/r/.../comments/...`). Use this when you want “open this post on Reddit.”
- **`link_url`** — For link posts, the **external article** URL (same as Reddit’s `data-url`). For **text/self** posts, this is `null`.
- **`permalink`** — Relative path only (e.g. `/r/technology/comments/1s39x77/...`); prepend `https://www.reddit.com` to match `url`.

Previously the parser put the external site in `url`; that matched Reddit’s listing `data-url` but is confusing if you expect “Reddit post URL.” The parser now matches the fields above.

---

## 6. Failure modes you might see

| Situation | Typical result |
|-----------|----------------|
| Reddit returns 403/429/5xx | `httpx` raises after retries; your API may return **500** unless you add a global exception handler. |
| Empty or changed HTML | Fewer posts or empty `posts`; not necessarily an HTTP error. |
| Invalid query params | **422** from FastAPI. |
| Redis down | Service still works; cache is skipped. |

---

## 7. How this differs from “subreddit rules”

The **`/subreddit/{name}/rules`** endpoint uses **Reddit JSON** (`about.json` / `about/rules.json`) for metadata (may fail on some production IPs; subreddit info can still error).  
The **posts** listing uses **old.reddit HTML** only.  
**Comments** for a single post use **old.reddit HTML** (`/comments/{id}/`).

---

## 8. Example commands

**Production (your Railway URL):**

```bash
curl "https://reddit-python-production.up.railway.app/api/v1/subreddit/technology/posts?sort_by=hot&limit=25"
```

**Local:**

```bash
curl "http://127.0.0.1:8000/api/v1/subreddit/technology/posts?sort_by=hot&limit=25"
```

**Health check:**

```bash
curl "https://reddit-python-production.up.railway.app/api/v1/health"
```
