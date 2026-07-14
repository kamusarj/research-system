export type Research = {
  id: string;
  display_id: string;
  title: string;
  type: string;
  status: "draft" | "in-review" | "approved" | "archived" | "rejected";
  collection_method: string;
  summary: string | null;
  content: string;
  source_url: string | null;
  authors: string[];
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
};

export type ResearchList = { items: Research[]; total: number; page: number; page_size: number };

