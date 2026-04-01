import { Link } from "react-router-dom";
import type { ConferenceMeta } from "../types";
import "./ConferenceCard.css";

export function ConferenceCard({ conf }: { conf: ConferenceMeta }) {
  return (
    <Link to={`/conference/${conf.id}`} className="conference-card">
      <div className="conference-card-header">
        <span className="conference-venue">{conf.venue}</span>
        <span className="conference-year">{conf.year}</span>
      </div>
      <div className="conference-count">
        {conf.paper_count.toLocaleString()} papers
      </div>
      {conf.top_papers.length > 0 && (
        <ol className="conference-top-papers">
          {conf.top_papers.map((p, i) => (
            <li key={i}>
              <span className="top-paper-title">{p.title}</span>
              <span className="top-paper-citations">{p.citation_count.toLocaleString()}</span>
            </li>
          ))}
        </ol>
      )}
      {!conf.has_citations && (
        <div className="conference-no-citations">No citation data yet</div>
      )}
    </Link>
  );
}
