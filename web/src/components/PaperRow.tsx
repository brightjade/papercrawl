import { useState } from "react";
import { Link } from "react-router-dom";
import type { Paper } from "../types";
import { TrackBadge } from "./TrackBadge";
import "./PaperRow.css";

export function PaperRow({ paper, rank }: { paper: Paper; rank: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`paper-row ${expanded ? "expanded" : ""}`}>
      <div className="paper-row-main" onClick={() => setExpanded(!expanded)}>
        <span className="paper-rank">{rank}</span>
        <div className="paper-info">
          <div className="paper-title">{paper.title}</div>
          <div className="paper-authors">
            {paper.authors.map((a, i) => (
              <span key={i}>
                {i > 0 && ", "}
                <Link
                  to={`/author/${encodeURIComponent(a)}`}
                  className="author-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  {a}
                </Link>
              </span>
            ))}
          </div>
        </div>
        <TrackBadge track={paper.selection} />
        <span className="paper-citations">
          {paper.citation_count != null
            ? paper.citation_count.toLocaleString()
            : "\u2014"}
        </span>
      </div>
      {expanded && (
        <div className="paper-details">
          {paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}
          {paper.keywords.length > 0 && (
            <div className="paper-keywords">
              {paper.keywords.map((kw, i) => (
                <span key={i} className="keyword-tag">
                  {kw}
                </span>
              ))}
            </div>
          )}
          <div className="paper-links">
            {paper.link && (
              <a href={paper.link} target="_blank" rel="noopener noreferrer">
                PDF &rarr;
              </a>
            )}
            {paper.forum_id && (
              <a
                href={`https://openreview.net/forum?id=${paper.forum_id}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                OpenReview &rarr;
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
