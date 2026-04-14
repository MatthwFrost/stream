export interface Article {
  id: string;
  title: string;
  author: string | null;
  source_name: string;
  url: string;
  is_paywalled: boolean;
  published_at: string;
  ingested_at: string;
  relevance_score: number;
  matched_tags: string[];
}

export interface Tag {
  id: string;
  name: string;
  keywords: string[];
  priority: number;
  active: boolean;
}

export interface Source {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  authority_score: number;
  poll_interval: number;
  active: boolean;
}

export interface ApiKeyEntry {
  key: string;
  label: string;
  masked_value: string | null;
}

export interface WsMessage {
  type: "new_article" | "top_articles_update" | "pong";
  data?: Article | Article[];
}
