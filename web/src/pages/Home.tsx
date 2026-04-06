import { useMemo, useState } from "react";
import { useManifest } from "../hooks/useManifest";
import { ConferenceCard } from "../components/ConferenceCard";
import "./Home.css";

type Category = "ML" | "NLP" | "SE" | "Others";

const VENUE_CATEGORIES: Record<string, Category> = {
  ICLR: "ML",
  NeurIPS: "ML",
  ICML: "ML",
  COLM: "NLP",
  AAAI: "ML",
  EMNLP: "NLP",
  ACL: "NLP",
  NAACL: "NLP",
  ICSE: "SE",
  FSE: "SE",
  ASE: "SE",
  ISSTA: "SE",
};

const ALL_CATEGORIES: Category[] = ["ML", "NLP", "SE", "Others"];

function getCategory(venue: string): Category {
  return VENUE_CATEGORIES[venue] ?? "Others";
}

export function Home() {
  const { data: manifest, error } = useManifest();
  const [activeCategories, setActiveCategories] = useState<Set<Category>>(
    new Set(ALL_CATEGORIES)
  );

  const toggleCategory = (cat: Category) => {
    setActiveCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        if (next.size > 1) next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  const filtered = useMemo(() => {
    if (!manifest) return [];
    return manifest.filter((c) => activeCategories.has(getCategory(c.venue)));
  }, [manifest, activeCategories]);

  if (error) return <div className="loading">Error: {error}</div>;
  if (!manifest) return <div className="loading">Loading conferences...</div>;

  const byYear = new Map<number, typeof filtered>();
  for (const conf of filtered) {
    if (!byYear.has(conf.year)) byYear.set(conf.year, []);
    byYear.get(conf.year)!.push(conf);
  }
  const years = [...byYear.keys()].sort((a, b) => b - a);

  return (
    <div className="home">
      <h2 className="page-title">Conferences</h2>
      <p className="page-subtitle">
        {filtered.reduce((sum, c) => sum + c.paper_count, 0).toLocaleString()} papers
        across {filtered.length} conferences
      </p>
      <div className="category-filters">
        {ALL_CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={`category-btn ${activeCategories.has(cat) ? "active" : ""}`}
            onClick={() => toggleCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>
      {years.map((year) => (
        <section key={year} className="year-section">
          <h3 className="year-heading">{year}</h3>
          <div className="conference-grid">
            {byYear.get(year)!.map((conf) => (
              <ConferenceCard key={conf.id} conf={conf} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
