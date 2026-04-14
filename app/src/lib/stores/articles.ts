import { writable } from "svelte/store";
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
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
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
    feed,
    top,
    connected,
    connect,
    disconnect,
    startTopRefresh,
  };
}

export const articles = createArticlesStore();

// Export sub-stores for direct $-syntax access in components
export const feedStore = articles.feed;
export const topStore = articles.top;
export const connectedStore = articles.connected;
