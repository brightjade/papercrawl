export interface Paper {
  title: string;
  authors: string[];
  selection: string;
  keywords?: string[];
  abstract?: string;
  link?: string;
  forum_id?: string;
  citation_count?: number;
  influential_citation_count?: number;
  reference_count?: number;
  tldr?: string;
  publication_date?: string;
  fields_of_study?: string[];
  open_access_pdf?: string;
  external_ids?: Record<string, string>;
}

export interface ConferenceMeta {
  id: string;
  venue: string;
  year: number;
  paper_count: number;
  has_citations: boolean;
  tracks: string[];
  top_papers: {
    title: string;
    citation_count: number;
  }[];
}

export interface AuthorSummary {
  name: string;
  conferences: string[];
  paper_count: number;
  total_citations: number;
}

export interface TrendsData {
  keywords_by_year: Record<string, Record<string, number>>;
  venue_counts_by_year: Record<string, Record<string, number>>;
}
