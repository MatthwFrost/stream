<script lang="ts">
  import { topStore } from "$lib/stores/articles";
  import ArticleRow from "./ArticleRow.svelte";
</script>

<div class="panel">
  <div class="panel-header">
    <span class="panel-title">TOP ARTICLES</span>
    <span class="panel-count">{$topStore.length}</span>
  </div>
  <div class="panel-body">
    {#each $topStore as article (article.id)}
      <ArticleRow {article} />
    {:else}
      <div class="empty">Waiting for articles...</div>
    {/each}
  </div>
</div>

<style>
  .panel { display: flex; flex-direction: column; height: 100%; border-right: 1px solid var(--border-color); }
  .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); flex-shrink: 0; }
  .panel-title { color: var(--accent-amber); font-weight: 700; font-size: var(--font-size-sm); letter-spacing: 1px; }
  .panel-count { color: var(--text-dim); font-size: var(--font-size-sm); }
  .panel-body { flex: 1; overflow-y: hidden; }
  .empty { padding: 20px; color: var(--text-dim); text-align: center; }
</style>
