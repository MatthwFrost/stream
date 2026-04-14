<script lang="ts">
  import TopPanel from "$lib/components/TopPanel.svelte";
  import FeedPanel from "$lib/components/FeedPanel.svelte";
</script>

<main class="panels">
  <div class="left-panel">
    <TopPanel />
  </div>
  <div class="right-panel">
    <FeedPanel />
  </div>
</main>

<style>
  .panels { display: flex; flex: 1; overflow: hidden; }
  .left-panel { width: 40%; min-width: 300px; }
  .right-panel { width: 60%; flex: 1; }
</style>
