<script lang="ts">
  import { connectedStore } from "$lib/stores/articles";
  import { settings } from "$lib/stores/settings";
</script>

<div class="topbar">
  <div class="left">
    <span class="brand">STREAM</span>
    <span class="separator">|</span>
    <span class="status" class:online={$connectedStore} class:offline={!$connectedStore}>
      {$connectedStore ? "CONNECTED" : "DISCONNECTED"}
    </span>
  </div>
  <div class="right">
    <button class="settings-btn" on:click={() => settings.toggleSettings()}>[SETTINGS]</button>
  </div>
</div>

<style>
  .topbar { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: var(--bg-secondary); border-bottom: 1px solid var(--accent-green); flex-shrink: 0; height: 28px; }
  .left { display: flex; align-items: center; gap: 8px; }
  .brand { color: var(--accent-green); font-weight: 700; font-size: var(--font-size-lg); letter-spacing: 2px; }
  .separator { color: var(--text-dim); }
  .status { font-size: var(--font-size-sm); letter-spacing: 1px; }
  .status.online { color: var(--accent-green); }
  .status.offline { color: var(--accent-red); }
  .right { display: flex; align-items: center; }
  .settings-btn { background: none; border: 1px solid var(--border-color); color: var(--text-secondary); font-family: var(--font-mono); font-size: var(--font-size-sm); padding: 2px 8px; cursor: pointer; transition: all 0.1s; }
  .settings-btn:hover { color: var(--accent-amber); border-color: var(--accent-amber); }
</style>
