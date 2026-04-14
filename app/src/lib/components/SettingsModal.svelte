<script lang="ts">
  import { settings } from "$lib/stores/settings";
  import { tagsStore } from "$lib/stores/tags";
  import { articles } from "$lib/stores/articles";
  import { fetchApiKeys, setApiKey, deleteApiKey } from "$lib/api";
  import type { ApiKeyEntry } from "$lib/types";

  const tagsList = tagsStore.tags;
  const sourcesList = tagsStore.sources;

  let serverUrl = "";
  let newTagName = "";
  let newTagKeywords = "";
  let activeTab: "tags" | "sources" | "apikeys" | "connection" = "tags";

  let apiKeys: ApiKeyEntry[] = [];
  let apiKeyInputs: Record<string, string> = {};
  let apiKeySaving: Record<string, boolean> = {};
  let apiKeySaved: Record<string, boolean> = {};

  settings.subscribe((s) => { serverUrl = s.serverUrl; });

  tagsStore.loadTags();
  tagsStore.loadSources();

  async function loadApiKeys() {
    apiKeys = await fetchApiKeys();
    apiKeyInputs = {};
  }

  $: if (activeTab === "apikeys") loadApiKeys();

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

  async function saveApiKey(key: string) {
    const val = (apiKeyInputs[key] || "").trim();
    if (!val) return;
    apiKeySaving = { ...apiKeySaving, [key]: true };
    try {
      await setApiKey(key, val);
      apiKeyInputs = { ...apiKeyInputs, [key]: "" };
      apiKeySaved = { ...apiKeySaved, [key]: true };
      setTimeout(() => {
        apiKeySaved = { ...apiKeySaved, [key]: false };
      }, 2000);
      await loadApiKeys();
    } finally {
      apiKeySaving = { ...apiKeySaving, [key]: false };
    }
  }

  async function clearApiKey(key: string) {
    await deleteApiKey(key);
    await loadApiKeys();
  }
</script>

<div class="overlay" on:click|self={() => settings.closeSettings()}>
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">SETTINGS</span>
      <button class="close-btn" on:click={() => settings.closeSettings()}>[X]</button>
    </div>

    <div class="tabs">
      <button class="tab" class:active={activeTab === "tags"} on:click={() => (activeTab = "tags")}>TAGS</button>
      <button class="tab" class:active={activeTab === "sources"} on:click={() => (activeTab = "sources")}>SOURCES</button>
      <button class="tab" class:active={activeTab === "apikeys"} on:click={() => (activeTab = "apikeys")}>API KEYS</button>
      <button class="tab" class:active={activeTab === "connection"} on:click={() => (activeTab = "connection")}>CONNECTION</button>
    </div>

    <div class="modal-body">
      {#if activeTab === "tags"}
        <div class="section">
          <div class="tag-list">
            {#each $tagsList as tag (tag.id)}
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
            {#each $sourcesList as source (source.id)}
              <div class="source-item">
                <span class="source-name">{source.name}</span>
                <span class="source-type">{source.type}</span>
                <span class="source-score">{source.authority_score.toFixed(1)}</span>
              </div>
            {/each}
          </div>
        </div>
      {:else if activeTab === "apikeys"}
        <div class="section">
          {#each apiKeys as entry (entry.key)}
            <div class="apikey-row">
              <div class="apikey-header">
                <span class="apikey-label">{entry.label}</span>
                {#if entry.masked_value}
                  <span class="apikey-current">{entry.masked_value}</span>
                  <button class="remove-btn" on:click={() => clearApiKey(entry.key)}>[CLEAR]</button>
                {:else}
                  <span class="apikey-none">not set</span>
                {/if}
              </div>
              <div class="url-form">
                <input
                  bind:value={apiKeyInputs[entry.key]}
                  class="input wide"
                  placeholder="Paste new key…"
                  type="password"
                />
                <button
                  class="action-btn"
                  class:saved={apiKeySaved[entry.key]}
                  on:click={() => saveApiKey(entry.key)}
                  disabled={apiKeySaving[entry.key]}
                >
                  {apiKeySaved[entry.key] ? "[OK]" : "[SAVE]"}
                </button>
              </div>
            </div>
          {/each}
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

<style>
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
  .modal { background: var(--bg-primary); border: 1px solid var(--accent-green); width: 600px; max-height: 80vh; display: flex; flex-direction: column; }
  .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border-color); }
  .modal-title { color: var(--accent-green); font-weight: 700; letter-spacing: 1px; }
  .close-btn { background: none; border: none; color: var(--text-secondary); font-family: var(--font-mono); cursor: pointer; }
  .close-btn:hover { color: var(--accent-red); }
  .tabs { display: flex; border-bottom: 1px solid var(--border-color); }
  .tab { flex: 1; padding: 6px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-secondary); font-family: var(--font-mono); font-size: var(--font-size-sm); cursor: pointer; letter-spacing: 1px; }
  .tab.active { color: var(--accent-amber); border-bottom-color: var(--accent-amber); }
  .modal-body { padding: 12px; overflow-y: auto; flex: 1; }
  .section { display: flex; flex-direction: column; gap: 8px; }
  .tag-list, .source-list { display: flex; flex-direction: column; gap: 4px; }
  .tag-item, .source-item { display: flex; align-items: center; gap: 8px; padding: 4px 8px; border-bottom: 1px solid var(--border-color); }
  .tag-name, .source-name { color: var(--accent-amber); min-width: 100px; }
  .tag-keywords { color: var(--text-secondary); font-size: var(--font-size-sm); flex: 1; }
  .source-type { color: var(--text-dim); font-size: var(--font-size-sm); }
  .source-score { color: var(--accent-green); font-size: var(--font-size-sm); }
  .remove-btn { background: none; border: none; color: var(--text-dim); font-family: var(--font-mono); cursor: pointer; }
  .remove-btn:hover { color: var(--accent-red); }
  .add-form, .url-form { display: flex; gap: 8px; align-items: center; }
  .label { color: var(--text-secondary); font-size: var(--font-size-sm); margin-bottom: 4px; }
  .input { background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-primary); font-family: var(--font-mono); font-size: var(--font-size-base); padding: 4px 8px; }
  .input:focus { outline: none; border-color: var(--accent-green); }
  .input.wide { flex: 1; }
  .action-btn { background: none; border: 1px solid var(--accent-green); color: var(--accent-green); font-family: var(--font-mono); font-size: var(--font-size-sm); padding: 4px 8px; cursor: pointer; }
  .action-btn:hover { background: var(--accent-green); color: var(--bg-primary); }
  .action-btn.saved { border-color: var(--accent-amber); color: var(--accent-amber); }
  .apikey-row { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
  .apikey-header { display: flex; align-items: center; gap: 8px; }
  .apikey-label { color: var(--accent-amber); min-width: 80px; font-size: var(--font-size-sm); }
  .apikey-current { color: var(--text-secondary); font-size: var(--font-size-sm); flex: 1; font-family: var(--font-mono); }
  .apikey-none { color: var(--text-dim); font-size: var(--font-size-sm); flex: 1; font-style: italic; }
</style>
