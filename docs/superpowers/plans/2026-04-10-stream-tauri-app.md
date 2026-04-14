# Stream Tauri Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Bloomberg terminal-style desktop app that displays a live news stream from the Stream backend via WebSocket, with two panes (top articles + live firehose) and tag/source settings.

**Architecture:** Tauri v2 provides the native macOS shell with a webview. Svelte renders the terminal-aesthetic UI. A WebSocket connection to the backend pushes new articles in real-time. REST calls manage tags and sources. All state is managed in Svelte stores.

**Tech Stack:** Tauri v2, Svelte 5, TypeScript, Vite

---

## File Structure

```
app/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tsconfig.json
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   └── lib.rs                      # Tauri entry point
│   ├── icons/                          # App icons
│   └── capabilities/
│       └── default.json
├── src/
│   ├── app.html                        # HTML shell
│   ├── app.css                         # Global terminal styles
│   ├── App.svelte                      # Root component
│   ├── lib/
│   │   ├── stores/
│   │   │   ├── articles.ts             # Article state + WebSocket
│   │   │   ├── settings.ts             # Server URL, persisted to localStorage
│   │   │   └── tags.ts                 # Tags state + REST calls
│   │   ├── api.ts                      # REST client helpers
│   │   └── types.ts                    # TypeScript interfaces
│   ├── components/
│   │   ├── TopBar.svelte               # Connection status + settings gear
│   │   ├── ArticleRow.svelte           # Single article row
│   │   ├── TopPanel.svelte             # Left pane: top ranked articles
│   │   ├── FeedPanel.svelte            # Right pane: live chronological stream
│   │   └── SettingsModal.svelte        # Tag/source/connection settings
│   └── vite-env.d.ts
└── static/
    └── favicon.png
```

---

### Task 1: Scaffold Tauri + Svelte Project

**Files:**
- Create: `app/` directory with full Tauri v2 + Svelte scaffold

- [ ] **Step 1: Create the Tauri project**

```bash
cd /Users/matthewfrost/stream
npm create tauri-app@latest app -- --template svelte-ts --manager npm
```

When prompted:
- Project name: `stream`
- Identifier: `com.stream.app`
- Frontend: Svelte
- TypeScript: Yes

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/matthewfrost/stream/app && npm install
```

- [ ] **Step 3: Verify it builds and opens**

```bash
cd /Users/matthewfrost/stream/app && npm run tauri dev
```

Expected: A window opens with the default Svelte template. Close it after confirming.

- [ ] **Step 4: Commit**

```bash
cd /Users/matthewfrost/stream && git add app/
git commit -m "feat: scaffold Tauri v2 + Svelte app"
```

---

### Task 2: TypeScript Types + API Client

**Files:**
- Create: `app/src/lib/types.ts`
- Create: `app/src/lib/api.ts`

- [ ] **Step 1: Create types.ts**

```typescript
// app/src/lib/types.ts

export interface Article {
  id: string;
  title: string;
  author: string | null;
  source_name: string;
  url: string;
  is_paywalled: boolean;
  published_at: string;
  ingested_at: string;
  relevance_score: number;
  matched_tags: string[];
}

export interface Tag {
  id: string;
  name: string;
  keywords: string[];
  priority: number;
  active: boolean;
}

export interface Source {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  authority_score: number;
  poll_interval: number;
  active: boolean;
}

export interface WsMessage {
  type: "new_article" | "top_articles_update" | "pong";
  data?: Article | Article[];
}
```

- [ ] **Step 2: Create api.ts**

```typescript
// app/src/lib/api.ts

import type { Article, Tag, Source } from "./types";

let baseUrl = "http://localhost";

export function setBaseUrl(url: string) {
  baseUrl = url.replace(/\/$/, "");
}

export function getBaseUrl(): string {
  return baseUrl;
}

export function getWsUrl(): string {
  const wsProto = baseUrl.startsWith("https") ? "wss" : "ws";
  const host = baseUrl.replace(/^https?:\/\//, "");
  return `${wsProto}://${host}/ws`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${baseUrl}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

// Articles
export const fetchArticles = (limit = 200) =>
  get<Article[]>(`/articles?limit=${limit}`);

export const fetchTopArticles = (limit = 50) =>
  get<Article[]>(`/articles/top?limit=${limit}`);

// Tags
export const fetchTags = () => get<Tag[]>("/tags");

export const createTag = (name: string, keywords: string[], priority = 1) =>
  post<Tag>("/tags", { name, keywords, priority });

export const updateTag = (id: string, data: Partial<Tag>) =>
  put<Tag>(`/tags/${id}`, data);

export const deleteTag = (id: string) => del(`/tags/${id}`);

// Sources
export const fetchSources = () => get<Source[]>("/sources");
```

- [ ] **Step 3: Commit**

```bash
git add app/src/lib/types.ts app/src/lib/api.ts
git commit -m "feat: add TypeScript types and REST API client"
```

---

### Task 3: Svelte Stores (Articles + WebSocket)

**Files:**
- Create: `app/src/lib/stores/settings.ts`
- Create: `app/src/lib/stores/articles.ts`
- Create: `app/src/lib/stores/tags.ts`

- [ ] **Step 1: Create settings store**

```typescript
// app/src/lib/stores/settings.ts

import { writable } from "svelte/store";
import { setBaseUrl } from "../api";

const STORAGE_KEY = "stream_server_url";
const DEFAULT_URL = "http://localhost";

function createSettingsStore() {
  const saved = typeof localStorage !== "undefined"
    ? localStorage.getItem(STORAGE_KEY) || DEFAULT_URL
    : DEFAULT_URL;

  setBaseUrl(saved);

  const { subscribe, set, update } = writable({
    serverUrl: saved,
    showSettings: false,
  });

  return {
    subscribe,
    setServerUrl: (url: string) => {
      const cleaned = url.replace(/\/$/, "");
      localStorage.setItem(STORAGE_KEY, cleaned);
      setBaseUrl(cleaned);
      update((s) => ({ ...s, serverUrl: cleaned }));
    },
    toggleSettings: () => {
      update((s) => ({ ...s, showSettings: !s.showSettings }));
    },
    closeSettings: () => {
      update((s) => ({ ...s, showSettings: false }));
    },
  };
}

export const settings = createSettingsStore();
```

- [ ] **Step 2: Create articles store with WebSocket**

```typescript
// app/src/lib/stores/articles.ts

import { writable, derived } from "svelte/store";
import { getWsUrl, fetchTopArticles, fetchArticles } from "../api";
import type { Article, WsMessage } from "../types";

const MAX_FEED_ARTICLES = 500;

function createArticlesStore() {
  const feed = writable<Article[]>([]);
  const top = writable<Article[]>([]);
  const connected = writable(false);

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let pingTimer: ReturnType<typeof setInterval> | null = null;

  function connect() {
    if (ws && ws.readyState <= WebSocket.OPEN) return;

    const url = getWsUrl();
    ws = new WebSocket(url);

    ws.onopen = () => {
      connected.set(true);
      // Send ping every 30s to keep connection alive
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
      // Load initial data
      loadInitialData();
    };

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);
      if (msg.type === "new_article" && msg.data && !Array.isArray(msg.data)) {
        feed.update((articles) => {
          const updated = [msg.data as Article, ...articles];
          return updated.slice(0, MAX_FEED_ARTICLES);
        });
      }
      if (msg.type === "top_articles_update" && msg.data && Array.isArray(msg.data)) {
        top.set(msg.data);
      }
    };

    ws.onclose = () => {
      connected.set(false);
      cleanup();
      // Reconnect after 3 seconds
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function cleanup() {
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = null;
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = null;
    cleanup();
    ws?.close();
    ws = null;
    connected.set(false);
  }

  async function loadInitialData() {
    try {
      const [topArticles, feedArticles] = await Promise.all([
        fetchTopArticles(50),
        fetchArticles(200),
      ]);
      top.set(topArticles);
      feed.set(feedArticles);
    } catch (e) {
      console.error("Failed to load initial data:", e);
    }
  }

  // Refresh top articles every 60 seconds
  function startTopRefresh() {
    setInterval(async () => {
      try {
        const topArticles = await fetchTopArticles(50);
        top.set(topArticles);
      } catch (e) {
        console.error("Failed to refresh top articles:", e);
      }
    }, 60000);
  }

  return {
    feed: { subscribe: feed.subscribe },
    top: { subscribe: top.subscribe },
    connected: { subscribe: connected.subscribe },
    connect,
    disconnect,
    startTopRefresh,
  };
}

export const articles = createArticlesStore();
```

- [ ] **Step 3: Create tags store**

```typescript
// app/src/lib/stores/tags.ts

import { writable } from "svelte/store";
import * as api from "../api";
import type { Tag, Source } from "../types";

function createTagsStore() {
  const tags = writable<Tag[]>([]);
  const sources = writable<Source[]>([]);

  return {
    tags: { subscribe: tags.subscribe },
    sources: { subscribe: sources.subscribe },

    async loadTags() {
      tags.set(await api.fetchTags());
    },

    async loadSources() {
      sources.set(await api.fetchSources());
    },

    async addTag(name: string, keywords: string[], priority = 1) {
      await api.createTag(name, keywords, priority);
      tags.set(await api.fetchTags());
    },

    async removeTag(id: string) {
      await api.deleteTag(id);
      tags.set(await api.fetchTags());
    },

    async editTag(id: string, data: Partial<Tag>) {
      await api.updateTag(id, data);
      tags.set(await api.fetchTags());
    },
  };
}

export const tagsStore = createTagsStore();
```

- [ ] **Step 4: Commit**

```bash
git add app/src/lib/stores/
git commit -m "feat: add Svelte stores for articles, tags, and settings with WebSocket"
```

---

### Task 4: Global Terminal Styles

**Files:**
- Modify: `app/src/app.css`

- [ ] **Step 1: Replace app.css with terminal theme**

Replace the entire contents of `app/src/app.css` with:

```css
/* app/src/app.css — Bloomberg terminal aesthetic */

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-panel: #0d0d0d;
  --bg-hover: #1a1a1a;
  --bg-active: #222222;
  --text-primary: #e0e0e0;
  --text-secondary: #888888;
  --text-dim: #555555;
  --accent-green: #00ff88;
  --accent-amber: #ffaa00;
  --accent-red: #ff4444;
  --accent-blue: #4488ff;
  --border-color: #222222;
  --paywall-color: #ff6644;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
  --font-size-sm: 11px;
  --font-size-base: 12px;
  --font-size-lg: 13px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  line-height: 1.4;
  height: 100%;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  user-select: none;
}

#app {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-dim);
}

/* Scanline overlay effect */
body::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.03) 0px,
    rgba(0, 0, 0, 0.03) 1px,
    transparent 1px,
    transparent 2px
  );
  z-index: 9999;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/src/app.css
git commit -m "feat: add terminal-aesthetic global styles with scanline effect"
```

---

### Task 5: ArticleRow Component

**Files:**
- Create: `app/src/components/ArticleRow.svelte`

- [ ] **Step 1: Create ArticleRow.svelte**

```svelte
<!-- app/src/components/ArticleRow.svelte -->
<script lang="ts">
  import type { Article } from "../lib/types";
  import { open } from "@tauri-apps/plugin-shell";

  export let article: Article;

  function timeAgo(dateStr: string): string {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diff = Math.floor((now - then) / 1000);

    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  }

  async function openArticle() {
    try {
      await open(article.url);
    } catch {
      window.open(article.url, "_blank");
    }
  }

  $: ago = timeAgo(article.ingested_at);
  $: tagList = article.matched_tags.length > 0
    ? article.matched_tags.join(", ")
    : null;
</script>

<button class="article-row" on:click={openArticle}>
  <span class="meta">
    {#if article.is_paywalled}
      <span class="paywall">[$]</span>
    {/if}
    <span class="time">{ago}</span>
  </span>
  <span class="title">{article.title}</span>
  <span class="source">{article.source_name}</span>
  {#if article.author}
    <span class="author">{article.author}</span>
  {/if}
  {#if tagList}
    <span class="tags">{tagList}</span>
  {/if}
</button>

<style>
  .article-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 4px 8px;
    border: none;
    background: none;
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--font-size-base);
    text-align: left;
    width: 100%;
    cursor: pointer;
    border-bottom: 1px solid var(--border-color);
    transition: background 0.1s;
  }

  .article-row:hover {
    background: var(--bg-hover);
  }

  .meta {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
    min-width: 40px;
  }

  .time {
    color: var(--text-dim);
    font-size: var(--font-size-sm);
  }

  .paywall {
    color: var(--paywall-color);
    font-weight: 700;
  }

  .title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source {
    color: var(--accent-green);
    font-size: var(--font-size-sm);
    flex-shrink: 0;
  }

  .author {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    flex-shrink: 0;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tags {
    color: var(--accent-amber);
    font-size: var(--font-size-sm);
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Install the Tauri shell plugin (needed for `open()`)**

```bash
cd /Users/matthewfrost/stream/app && npm install @tauri-apps/plugin-shell
```

Then add to `src-tauri/Cargo.toml` under `[dependencies]`:

```toml
tauri-plugin-shell = "2"
```

And register the plugin in `src-tauri/src/lib.rs`:

```rust
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

Also update `src-tauri/capabilities/default.json` to include shell permissions:

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-open"
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add app/src/components/ArticleRow.svelte app/src-tauri/Cargo.toml app/src-tauri/src/lib.rs app/src-tauri/capabilities/default.json app/package.json app/package-lock.json
git commit -m "feat: add ArticleRow component with paywall indicator and external link opening"
```

---

### Task 6: TopPanel and FeedPanel Components

**Files:**
- Create: `app/src/components/TopPanel.svelte`
- Create: `app/src/components/FeedPanel.svelte`

- [ ] **Step 1: Create TopPanel.svelte**

```svelte
<!-- app/src/components/TopPanel.svelte -->
<script lang="ts">
  import { articles } from "../lib/stores/articles";
  import ArticleRow from "./ArticleRow.svelte";
</script>

<div class="panel">
  <div class="panel-header">
    <span class="panel-title">TOP ARTICLES</span>
    <span class="panel-count">{$articles.top.length}</span>
  </div>
  <div class="panel-body">
    {#each $articles.top as article (article.id)}
      <ArticleRow {article} />
    {:else}
      <div class="empty">Waiting for articles...</div>
    {/each}
  </div>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    border-right: 1px solid var(--border-color);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
  }

  .panel-title {
    color: var(--accent-amber);
    font-weight: 700;
    font-size: var(--font-size-sm);
    letter-spacing: 1px;
  }

  .panel-count {
    color: var(--text-dim);
    font-size: var(--font-size-sm);
  }

  .panel-body {
    flex: 1;
    overflow-y: auto;
  }

  .empty {
    padding: 20px;
    color: var(--text-dim);
    text-align: center;
  }
</style>
```

- [ ] **Step 2: Create FeedPanel.svelte**

```svelte
<!-- app/src/components/FeedPanel.svelte -->
<script lang="ts">
  import { articles } from "../lib/stores/articles";
  import ArticleRow from "./ArticleRow.svelte";
</script>

<div class="panel">
  <div class="panel-header">
    <span class="panel-title">LIVE FEED</span>
    <span class="panel-count">{$articles.feed.length}</span>
  </div>
  <div class="panel-body">
    {#each $articles.feed as article (article.id)}
      <ArticleRow {article} />
    {:else}
      <div class="empty">Connecting to feed...</div>
    {/each}
  </div>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
  }

  .panel-title {
    color: var(--accent-green);
    font-weight: 700;
    font-size: var(--font-size-sm);
    letter-spacing: 1px;
  }

  .panel-count {
    color: var(--text-dim);
    font-size: var(--font-size-sm);
  }

  .panel-body {
    flex: 1;
    overflow-y: auto;
  }

  .empty {
    padding: 20px;
    color: var(--text-dim);
    text-align: center;
  }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add app/src/components/TopPanel.svelte app/src/components/FeedPanel.svelte
git commit -m "feat: add TopPanel and FeedPanel components"
```

---

### Task 7: TopBar Component

**Files:**
- Create: `app/src/components/TopBar.svelte`

- [ ] **Step 1: Create TopBar.svelte**

```svelte
<!-- app/src/components/TopBar.svelte -->
<script lang="ts">
  import { articles } from "../lib/stores/articles";
  import { settings } from "../lib/stores/settings";
</script>

<div class="topbar">
  <div class="left">
    <span class="brand">STREAM</span>
    <span class="separator">|</span>
    <span class="status" class:online={$articles.connected} class:offline={!$articles.connected}>
      {$articles.connected ? "CONNECTED" : "DISCONNECTED"}
    </span>
  </div>
  <div class="right">
    <button class="settings-btn" on:click={() => settings.toggleSettings()}>
      [SETTINGS]
    </button>
  </div>
</div>

<style>
  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--accent-green);
    flex-shrink: 0;
    height: 28px;
  }

  .left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .brand {
    color: var(--accent-green);
    font-weight: 700;
    font-size: var(--font-size-lg);
    letter-spacing: 2px;
  }

  .separator {
    color: var(--text-dim);
  }

  .status {
    font-size: var(--font-size-sm);
    letter-spacing: 1px;
  }

  .status.online {
    color: var(--accent-green);
  }

  .status.offline {
    color: var(--accent-red);
  }

  .right {
    display: flex;
    align-items: center;
  }

  .settings-btn {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    padding: 2px 8px;
    cursor: pointer;
    transition: all 0.1s;
  }

  .settings-btn:hover {
    color: var(--accent-amber);
    border-color: var(--accent-amber);
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add app/src/components/TopBar.svelte
git commit -m "feat: add TopBar with connection status and settings toggle"
```

---

### Task 8: Settings Modal

**Files:**
- Create: `app/src/components/SettingsModal.svelte`

- [ ] **Step 1: Create SettingsModal.svelte**

```svelte
<!-- app/src/components/SettingsModal.svelte -->
<script lang="ts">
  import { settings } from "../lib/stores/settings";
  import { tagsStore } from "../lib/stores/tags";
  import { articles } from "../lib/stores/articles";
  import type { Tag } from "../lib/types";

  let serverUrl = "";
  let newTagName = "";
  let newTagKeywords = "";
  let activeTab: "tags" | "sources" | "connection" = "tags";

  settings.subscribe((s) => {
    serverUrl = s.serverUrl;
  });

  // Load data when modal opens
  tagsStore.loadTags();
  tagsStore.loadSources();

  function saveUrl() {
    settings.setServerUrl(serverUrl);
    articles.disconnect();
    articles.connect();
  }

  async function addTag() {
    if (!newTagName.trim() || !newTagKeywords.trim()) return;
    const keywords = newTagKeywords.split(",").map((k) => k.trim()).filter(Boolean);
    await tagsStore.addTag(newTagName.trim(), keywords);
    newTagName = "";
    newTagKeywords = "";
  }

  async function removeTag(id: string) {
    await tagsStore.removeTag(id);
  }
</script>

{#if true}
  <div class="overlay" on:click|self={() => settings.closeSettings()}>
    <div class="modal">
      <div class="modal-header">
        <span class="modal-title">SETTINGS</span>
        <button class="close-btn" on:click={() => settings.closeSettings()}>[X]</button>
      </div>

      <div class="tabs">
        <button class="tab" class:active={activeTab === "tags"} on:click={() => (activeTab = "tags")}>TAGS</button>
        <button class="tab" class:active={activeTab === "sources"} on:click={() => (activeTab = "sources")}>SOURCES</button>
        <button class="tab" class:active={activeTab === "connection"} on:click={() => (activeTab = "connection")}>CONNECTION</button>
      </div>

      <div class="modal-body">
        {#if activeTab === "tags"}
          <div class="section">
            <div class="tag-list">
              {#each $tagsStore.tags as tag (tag.id)}
                <div class="tag-item">
                  <span class="tag-name">{tag.name}</span>
                  <span class="tag-keywords">{tag.keywords.join(", ")}</span>
                  <button class="remove-btn" on:click={() => removeTag(tag.id)}>[-]</button>
                </div>
              {/each}
            </div>
            <div class="add-form">
              <input bind:value={newTagName} placeholder="Tag name" class="input" />
              <input bind:value={newTagKeywords} placeholder="Keywords (comma separated)" class="input wide" />
              <button class="action-btn" on:click={addTag}>[+ADD]</button>
            </div>
          </div>

        {:else if activeTab === "sources"}
          <div class="section">
            <div class="source-list">
              {#each $tagsStore.sources as source (source.id)}
                <div class="source-item">
                  <span class="source-name">{source.name}</span>
                  <span class="source-type">{source.type}</span>
                  <span class="source-score">{source.authority_score.toFixed(1)}</span>
                </div>
              {/each}
            </div>
          </div>

        {:else if activeTab === "connection"}
          <div class="section">
            <label class="label">Server URL</label>
            <div class="url-form">
              <input bind:value={serverUrl} class="input wide" placeholder="http://localhost" />
              <button class="action-btn" on:click={saveUrl}>[SAVE]</button>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--bg-primary);
    border: 1px solid var(--accent-green);
    width: 600px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .modal-title {
    color: var(--accent-green);
    font-weight: 700;
    letter-spacing: 1px;
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    cursor: pointer;
  }

  .close-btn:hover {
    color: var(--accent-red);
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--border-color);
  }

  .tab {
    flex: 1;
    padding: 6px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    cursor: pointer;
    letter-spacing: 1px;
  }

  .tab.active {
    color: var(--accent-amber);
    border-bottom-color: var(--accent-amber);
  }

  .modal-body {
    padding: 12px;
    overflow-y: auto;
    flex: 1;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .tag-list, .source-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tag-item, .source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    border-bottom: 1px solid var(--border-color);
  }

  .tag-name, .source-name {
    color: var(--accent-amber);
    min-width: 100px;
  }

  .tag-keywords {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    flex: 1;
  }

  .source-type {
    color: var(--text-dim);
    font-size: var(--font-size-sm);
  }

  .source-score {
    color: var(--accent-green);
    font-size: var(--font-size-sm);
  }

  .remove-btn {
    background: none;
    border: none;
    color: var(--text-dim);
    font-family: var(--font-mono);
    cursor: pointer;
  }

  .remove-btn:hover {
    color: var(--accent-red);
  }

  .add-form, .url-form {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .label {
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    margin-bottom: 4px;
  }

  .input {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--font-size-base);
    padding: 4px 8px;
  }

  .input:focus {
    outline: none;
    border-color: var(--accent-green);
  }

  .input.wide {
    flex: 1;
  }

  .action-btn {
    background: none;
    border: 1px solid var(--accent-green);
    color: var(--accent-green);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    padding: 4px 8px;
    cursor: pointer;
  }

  .action-btn:hover {
    background: var(--accent-green);
    color: var(--bg-primary);
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add app/src/components/SettingsModal.svelte
git commit -m "feat: add settings modal with tags, sources, and connection tabs"
```

---

### Task 9: Root App Component

**Files:**
- Modify: `app/src/App.svelte`

- [ ] **Step 1: Replace App.svelte**

Replace the entire contents of `app/src/App.svelte`:

```svelte
<!-- app/src/App.svelte -->
<script lang="ts">
  import { onMount } from "svelte";
  import { articles } from "./lib/stores/articles";
  import { settings } from "./lib/stores/settings";
  import TopBar from "./components/TopBar.svelte";
  import TopPanel from "./components/TopPanel.svelte";
  import FeedPanel from "./components/FeedPanel.svelte";
  import SettingsModal from "./components/SettingsModal.svelte";

  onMount(() => {
    articles.connect();
    articles.startTopRefresh();

    return () => {
      articles.disconnect();
    };
  });
</script>

<TopBar />

<main class="panels">
  <div class="left-panel">
    <TopPanel />
  </div>
  <div class="right-panel">
    <FeedPanel />
  </div>
</main>

{#if $settings.showSettings}
  <SettingsModal />
{/if}

<style>
  .panels {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .left-panel {
    width: 40%;
    min-width: 300px;
  }

  .right-panel {
    width: 60%;
    flex: 1;
  }
</style>
```

- [ ] **Step 2: Verify the app renders**

```bash
cd /Users/matthewfrost/stream/app && npm run tauri dev
```

Expected: The app opens with the terminal aesthetic — dark background, green "STREAM" header, two panels showing articles from the live backend. New articles should appear in the right panel as the worker ingests them.

- [ ] **Step 3: Commit**

```bash
git add app/src/App.svelte
git commit -m "feat: wire up root App with two-pane layout, WebSocket, and settings"
```

---

### Task 10: Tauri Window Configuration

**Files:**
- Modify: `app/src-tauri/tauri.conf.json`

- [ ] **Step 1: Update tauri.conf.json**

Find the `"windows"` array in `tauri.conf.json` and update the main window config:

```json
{
  "label": "main",
  "title": "Stream",
  "width": 1200,
  "height": 800,
  "minWidth": 800,
  "minHeight": 500,
  "decorations": true,
  "transparent": false
}
```

Also ensure the `"identifier"` field is set to `"com.stream.app"`.

- [ ] **Step 2: Build for production**

```bash
cd /Users/matthewfrost/stream/app && npm run tauri build
```

Expected: Produces a `.dmg` in `app/src-tauri/target/release/bundle/dmg/`.

- [ ] **Step 3: Commit**

```bash
git add app/src-tauri/tauri.conf.json
git commit -m "feat: configure Tauri window size and app identity"
```
