import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useConferenceData } from "../hooks/useConferenceData";
import { useManifest } from "../hooks/useManifest";
import { PaperRow } from "../components/PaperRow";
import { SearchInput } from "../components/SearchInput";
import "./Conference.css";

type SortKey = "citations" | "title";

export function Conference() {
  const { id } = useParams<{ id: string }>();
  const { data: papers, error } = useConferenceData(id);
  const { data: manifest } = useManifest();
  const [search, setSearch] = useState("");
  const [trackFilter, setTrackFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortKey>("citations");

  const meta = manifest?.find((c) => c.id === id);

  const filtered = useMemo(() => {
    if (!papers) return [];
    let result = papers;

    if (trackFilter !== "all") {
      result = result.filter((p) => p.selection === trackFilter);
    }

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.authors.some((a) => a.toLowerCase().includes(q)) ||
          (p.keywords ?? []).some((k) => k.toLowerCase().includes(q))
      );
    }

    result = [...result].sort((a, b) => {
      if (sortBy === "citations") {
        return (b.citation_count ?? -1) - (a.citation_count ?? -1);
      }
      return a.title.localeCompare(b.title);
    });

    return result;
  }, [papers, search, trackFilter, sortBy]);

  if (error) return <div className="loading">Error: {error}</div>;
  if (!papers) return <div className="loading">Loading papers...</div>;

  const tracks = [...new Set(papers.map((p) => p.selection))].filter(Boolean).sort();

  return (
    <div className="conference-page">
      <h2 className="page-title">{meta?.venue ?? id} {meta?.year ?? ""}</h2>
      <p className="page-subtitle">
        {papers.length.toLocaleString()} papers
        {filtered.length !== papers.length && ` · ${filtered.length.toLocaleString()} shown`}
      </p>

      <div className="conference-controls">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search titles, authors, keywords..."
        />
        <div className="conference-filters">
          <select
            className="track-select"
            value={trackFilter}
            onChange={(e) => setTrackFilter(e.target.value)}
          >
            <option value="all">All tracks</option>
            {tracks.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select
            className="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortKey)}
          >
            <option value="citations">Sort by citations</option>
            <option value="title">Sort by title</option>
          </select>
        </div>
      </div>

      <div className="paper-table-header">
        <span className="col-rank">#</span>
        <span className="col-title">Paper</span>
        <span className="col-track">Track</span>
        <span className="col-citations">Citations</span>
      </div>

      <div className="paper-list">
        {filtered.map((paper, i) => (
          <PaperRow key={paper.title} paper={paper} rank={i + 1} />
        ))}
        {filtered.length === 0 && (
          <div className="loading">No papers match your search.</div>
        )}
      </div>
    </div>
  );
}
