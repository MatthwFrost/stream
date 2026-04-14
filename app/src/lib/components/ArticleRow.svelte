<script lang="ts">
  import type { Article } from "$lib/types";
  import { open } from "@tauri-apps/plugin-shell";

  export let article: Article;

  function timeAgo(dateStr: string): string {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diff = Math.floor((now - then) / 1000);
    if (diff < 60) return diff + "s";
    if (diff < 3600) return Math.floor(diff / 60) + "m";
    if (diff < 86400) return Math.floor(diff / 3600) + "h";
    return Math.floor(diff / 86400) + "d";
  }

  async function openArticle() {
    try {
      await open(article.url);
    } catch {
      window.open(article.url, "_blank");
    }
  }

  $: ago = timeAgo(article.ingested_at);
  $: tagList = article.matched_tags.length > 0 ? article.matched_tags.join(", ") : null;
</script>

<button class="article-row" on:click={openArticle}>
  <span class="meta">
    {#if article.is_paywalled}<span class="paywall">[$]</span>{/if}
    <span class="time">{ago}</span>
  </span>
  <span class="title">{article.title}</span>
  <span class="source">{article.source_name}</span>
  {#if tagList}<span class="tags">{tagList}</span>{/if}
</button>

<style>
  .article-row {
    display: flex; align-items: baseline; gap: 8px;
    padding: 4px 8px; border: none; background: none;
    color: var(--text-primary); font-family: var(--font-mono);
    font-size: var(--font-size-base); text-align: left;
    width: 100%; cursor: pointer;
    border-bottom: 1px solid var(--border-color);
    transition: background 0.1s;
  }
  .article-row:hover { background: var(--bg-hover); }
  .meta { display: flex; gap: 4px; flex-shrink: 0; min-width: 40px; }
  .time { color: var(--text-dim); font-size: var(--font-size-sm); }
  .paywall { color: var(--paywall-color); font-weight: 700; }
  .title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .source { color: var(--accent-green); font-size: var(--font-size-sm); flex-shrink: 0; }
  .tags { color: var(--accent-amber); font-size: var(--font-size-sm); flex-shrink: 0; }
</style>
