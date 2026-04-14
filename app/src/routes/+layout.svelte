<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { articles } from "$lib/stores/articles";
  import { settings } from "$lib/stores/settings";
  import TopBar from "$lib/components/TopBar.svelte";
  import SettingsModal from "$lib/components/SettingsModal.svelte";

  onMount(() => {
    articles.connect();
    articles.startTopRefresh();
    return () => { articles.disconnect(); };
  });
</script>

<TopBar />
<slot />
{#if $settings.showSettings}
  <SettingsModal />
{/if}
