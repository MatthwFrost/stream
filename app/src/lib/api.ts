import type { Article, Tag, Source, ApiKeyEntry } from "./types";

let baseUrl = "http://localhost";

export function setBaseUrl(url: string) {
  baseUrl = url.replace(/\/$/, "");
}

export function getBaseUrl(): string {
  return baseUrl;
}

export function getWsUrl(): string {
  const wsProto = baseUrl.startsWith("https") ? "wss" : "ws";
  const host = baseUrl.replace(/^https?:\/\//, "");
  return `${wsProto}://${host}/ws`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${baseUrl}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export const fetchArticles = (limit = 200) =>
  get<Article[]>(`/articles?limit=${limit}`);

export const fetchTopArticles = (limit = 50) =>
  get<Article[]>(`/articles/top?limit=${limit}`);

export const fetchTags = () => get<Tag[]>("/tags");

export const createTag = (name: string, keywords: string[], priority = 1) =>
  post<Tag>("/tags", { name, keywords, priority });

export const updateTag = (id: string, data: Partial<Tag>) =>
  put<Tag>(`/tags/${id}`, data);

export const deleteTag = (id: string) => del(`/tags/${id}`);

export const fetchSources = () => get<Source[]>("/sources");

export const fetchApiKeys = () => get<ApiKeyEntry[]>("/config");
export const setApiKey = (key: string, value: string) =>
  put<void>(`/config/${key}`, { value });
export const deleteApiKey = (key: string) => del(`/config/${key}`);
