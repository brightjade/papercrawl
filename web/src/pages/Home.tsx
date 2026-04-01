import { useManifest } from "../hooks/useManifest";
import { ConferenceCard } from "../components/ConferenceCard";
import "./Home.css";

export function Home() {
  const { data: manifest, error } = useManifest();

  if (error) return <div className="loading">Error: {error}</div>;
  if (!manifest) return <div className="loading">Loading conferences...</div>;

  const byYear = new Map<number, typeof manifest>();
  for (const conf of manifest) {
    if (!byYear.has(conf.year)) byYear.set(conf.year, []);
    byYear.get(conf.year)!.push(conf);
  }
  const years = [...byYear.keys()].sort((a, b) => b - a);

  return (
    <div className="home">
      <h2 className="page-title">Conferences</h2>
      <p className="page-subtitle">
        {manifest.reduce((sum, c) => sum + c.paper_count, 0).toLocaleString()} papers
        across {manifest.length} conferences
      </p>
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
