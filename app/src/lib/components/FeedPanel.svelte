<script lang="ts">
  import { feedStore } from "$lib/stores/articles";
  import ArticleRow from "./ArticleRow.svelte";
</script>

<div class="panel">
  <div class="panel-header">
    <span class="panel-title">LIVE FEED</span>
    <span class="panel-count">{$feedStore.length}</span>
  </div>
  <div class="panel-body">
    {#each $feedStore as article (article.id)}
      <ArticleRow {article} />
    {:else}
      <div class="empty">Connecting to feed...</div>
    {/each}
  </div>
</div>

<style>
  .panel { display: flex; flex-direction: column; height: 100%; }
  .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
  .panel-title { color: var(--accent-green); font-weight: 700; font-size: var(--font-size-sm); letter-spacing: 1px; }
  .panel-count { color: var(--text-dim); font-size: var(--font-size-sm); }
  .panel-body { flex: 1; overflow-y: auto; }
  .empty { padding: 20px; color: var(--text-dim); text-align: center; }
</style>
