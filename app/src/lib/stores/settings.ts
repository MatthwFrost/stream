import { writable } from "svelte/store";
import { setBaseUrl } from "../api";

const STORAGE_KEY = "stream_server_url";
const DEFAULT_URL = "http://72.61.17.90:8080";

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
