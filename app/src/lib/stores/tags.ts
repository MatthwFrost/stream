import { writable } from "svelte/store";
import * as api from "../api";
import type { Tag, Source } from "../types";

function createTagsStore() {
  const tags = writable<Tag[]>([]);
  const sources = writable<Source[]>([]);

  return {
    tags,
    sources,

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
