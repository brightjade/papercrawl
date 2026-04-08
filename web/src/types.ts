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
  total_citations: number;
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

export interface NgramEntry {
  ngram: string;
  count: number;
}

export interface RisingFallingEntry {
  ngram: string;
  count: number;
  delta: number;
  pct_change: number;
}

export interface CitationStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers: number[];
}

export interface TopPaper {
  title: string;
  venue: string;
  citation_count: number;
  influential_citation_count: number;
  conference_id: string;
}

export interface TrendsData {
  overview: {
    venue_counts_by_year: Record<string, Record<string, number>>;
    citation_counts_by_year: Record<string, Record<string, number>>;
    growth_pct_by_year: Record<string, Record<string, number>>;
  };
  topics: {
    top_ngrams_by_year: Record<string, NgramEntry[]>;
    rising_falling_by_year: Record<
      string,
      { rising: RisingFallingEntry[]; falling: RisingFallingEntry[] }
    >;
    ngram_trends: Record<string, Record<string, number>>;
    venue_ngram_matrix_by_year: Record<
      string,
      Record<string, Record<string, number>>
    >;
  };
  impact: {
    citation_stats_by_year: Record<string, Record<string, CitationStats>>;
    avg_citations_by_year: Record<string, Record<string, number>>;
    top_papers_by_year: Record<string, TopPaper[]>;
    influential_ratio_by_year: Record<string, Record<string, number>>;
  };
  composition: {
    track_breakdown_by_year: Record<
      string,
      Record<string, Record<string, number>>
    >;
    venue_counts_all_years: Record<string, Record<string, number>>;
    growth_rates_by_year: Record<string, Record<string, number>>;
  };
}
