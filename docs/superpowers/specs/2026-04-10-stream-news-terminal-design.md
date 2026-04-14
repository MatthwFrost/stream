# Stream — Bloomberg-Style News Terminal

## Overview

A real-time news aggregation system with a terminal-aesthetic desktop app. Backend agents on a VPS continuously ingest news from RSS feeds, news APIs, and web scrapers. Articles are ranked by tag relevance, source authority, and recency, then pushed to a Tauri desktop app over WebSockets.

## Architecture

```
Tauri Desktop App (macOS)
    ↕ WebSocket
VPS (Docker Compose)
    ├── API Server (FastAPI) — WebSocket + REST
    ├── Ingestion Workers — RSS, API, Scraper agents
    ├── PostgreSQL — article storage, tags, sources
    └── Redis — pub/sub for real-time push
```

### Flow

1. Workers continuously ingest articles from RSS/APIs/scrapers
2. Articles are deduplicated (by URL), tag-matched, paywall-detected, and stored in Postgres
3. On insert, worker publishes `new_article` event to Redis pub/sub
4. API server subscribes to Redis, pushes article to all connected clients via WebSocket
5. Ranker runs every 60s, recomputing `relevance_score` for recent articles
6. Tauri app displays two panels fed by the same WebSocket connection

## Data Model

### articles

| Column          | Type        | Notes                                      |
|-----------------|-------------|---------------------------------------------|
| id              | UUID        | Primary key                                 |
| title           | text        |                                             |
| author          | text (null) |                                             |
| source_name     | text        | e.g. "Reuters", "TechCrunch"                |
| url             | text        | Unique — dedupe key                         |
| is_paywalled    | boolean     |                                             |
| published_at    | timestamp   |                                             |
| ingested_at     | timestamp   |                                             |
| relevance_score | float       | Computed by ranker                          |
| raw_tags        | text[]      | Tags from source metadata                   |
| matched_tags    | text[]      | User tags this article matched              |

### tags

| Column   | Type     | Notes                              |
|----------|----------|------------------------------------|
| id       | UUID     | Primary key                        |
| name     | text     | e.g. "technology", "oil"           |
| keywords | text[]   | Expanded keyword list for matching |
| priority | int      | Weight in ranking                  |
| active   | boolean  |                                    |

### sources

| Column          | Type   | Notes                                         |
|-----------------|--------|-----------------------------------------------|
| id              | UUID   | Primary key                                   |
| name            | text   | e.g. "Reuters"                                |
| type            | enum   | rss, api, scraper                             |
| config          | jsonb  | Feed URL, API key ref, scrape selectors, etc. |
| authority_score | float  | Source reputation weight (0.0-1.0)            |
| poll_interval   | int    | Seconds between fetches                       |
| active          | boolean|                                               |

## Ingestion Agents

All agents run as async tasks in the worker process.

### RSS Agent

- Parses feeds using `feedparser`, respects `ETag`/`Last-Modified` headers
- Default poll interval: 60 seconds
- Starting sources: Reuters, AP, BBC, TechCrunch, Ars Technica, The Verge, Guardian, Bloomberg, CNBC, Politico, E&E News, OilPrice.com

### News API Agent

- Hits NewsAPI.org, GNews, Bing News APIs
- Runs every 5-10 minutes to stay within rate limits
- Broader discovery of long-tail sources

### Scraper Agent

- `httpx` + `BeautifulSoup` for sources without RSS/API
- Per-source CSS selector config in `sources.config`
- Used sparingly — only where RSS/API can't reach

### Shared Pipeline

After any agent fetches articles:

1. Normalize data (title, author, source, URL, published_at)
2. Deduplicate by URL against Postgres
3. Tag matching — title + metadata against user tag keywords
4. Paywall detection — known domain list + HTTP header/meta tag hints
5. Store in Postgres
6. Publish `new_article` event to Redis pub/sub

## Ranking System

Runs every 60 seconds as a worker task.

```
score = (tag_relevance * 0.5) + (source_authority * 0.3) + (recency * 0.2)
```

- **tag_relevance**: matched tag count * tag priority weights, normalized 0-1
- **source_authority**: from `sources.authority_score`
- **recency**: exponential decay over hours

External signals (social mentions, share counts) are a future enhancement, not in MVP.

## API Server (FastAPI)

### WebSocket `/ws`

- Pushes `new_article` messages as they arrive from Redis pub/sub
- Pushes periodic `top_articles_update` with refreshed rankings
- Message format: `{ "type": "new_article" | "top_articles_update", "data": {...} }`

### REST Endpoints

| Method | Path           | Purpose                    |
|--------|----------------|----------------------------|
| GET    | /articles      | Paginated, filterable list |
| GET    | /articles/top  | Current top-ranked articles|
| GET    | /tags          | List configured tags       |
| POST   | /tags          | Add a tag                  |
| PUT    | /tags/:id      | Update tag                 |
| DELETE | /tags/:id      | Remove a tag               |
| GET    | /sources       | List sources               |
| POST   | /sources       | Add a source               |

## Tauri Desktop App

### Tech Stack

- Tauri (Rust shell + native webview)
- Svelte for the UI
- Terminal aesthetic: dark background, monospace font, green/amber accents

### Layout

- **Two-pane split**: Left (40%) top articles ranked by score, Right (60%) live chronological firehose
- **Article row**: `[PAYWALL] Title | Source | Author | 2m ago`
- **Click action**: Opens article URL in default system browser
- **Top bar**: Connection status indicator + settings gear icon

### Settings Panel (modal overlay)

- **Tags**: Add/remove tags, set keywords per tag, adjust priority
- **Sources**: View active sources, toggle on/off
- **Connection**: VPS server URL configuration

## Deployment

### VPS — Docker Compose

```yaml
services:
  api:        # FastAPI server
  worker:     # Ingestion agents + ranker
  postgres:   # Article storage
  redis:      # Pub/sub for real-time push
  nginx:      # Reverse proxy + SSL (Let's Encrypt)
```

- Worker auto-restarts on crash via Docker restart policy
- Postgres data persisted via Docker volume

### Desktop App

- Built with `cargo tauri build` → `.dmg` for macOS
- Connects to VPS WebSocket URL configured in settings

## Starting Topics

| Tag              | Keywords                                                              |
|------------------|-----------------------------------------------------------------------|
| technology       | tech, AI, software, hardware, startup, silicon valley, computing      |
| sustainability   | climate, renewable, green energy, carbon, ESG, environmental          |
| oil              | oil, petroleum, OPEC, crude, energy, natural gas, drilling            |
| politics         | election, congress, senate, policy, legislation, government, geopolitics |

## Future Enhancements (not in MVP)

- External ranking signals (Twitter/X, Reddit, share counts)
- AI-generated article summaries
- Notification system for breaking news on high-priority tags
- Multiple layout themes
- Article bookmarking/saving
- Search across ingested articles
