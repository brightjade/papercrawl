import { useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { useTrends } from "../hooks/useTrends";
import "./Trends.css";

const VENUE_COLORS: Record<string, string> = {
  ICLR: "#1a6b5a",
  NeurIPS: "#9333ea",
  ICML: "#0369a1",
  EMNLP: "#b45309",
  ACL: "#dc2626",
  NAACL: "#059669",
  AAAI: "#6366f1",
  COLM: "#ec4899",
  "USENIX Security": "#78716c",
};

export function Trends() {
  const { data: trends, error } = useTrends();
  const [topN, setTopN] = useState(20);

  const venueChartData = useMemo(() => {
    if (!trends) return [];
    const years = Object.keys(trends.venue_counts_by_year).sort();
    return years.map((year) => ({
      year,
      ...trends.venue_counts_by_year[year],
    }));
  }, [trends]);

  const allVenues = useMemo(() => {
    if (!trends) return [];
    const venues = new Set<string>();
    for (const counts of Object.values(trends.venue_counts_by_year)) {
      for (const v of Object.keys(counts)) venues.add(v);
    }
    return [...venues].sort();
  }, [trends]);

  const keywordChartData = useMemo(() => {
    if (!trends) return [];
    const totals: Record<string, number> = {};
    for (const kws of Object.values(trends.keywords_by_year)) {
      for (const [kw, count] of Object.entries(kws)) {
        totals[kw] = (totals[kw] ?? 0) + count;
      }
    }
    return Object.entries(totals)
      .sort((a, b) => b[1] - a[1])
      .slice(0, topN)
      .map(([keyword, count]) => ({ keyword, count }));
  }, [trends, topN]);

  if (error) return <div className="loading">Error: {error}</div>;
  if (!trends) return <div className="loading">Loading trends...</div>;

  return (
    <div className="trends-page">
      <h2 className="page-title">Trends</h2>
      <p className="page-subtitle">Paper counts and keyword trends across conferences</p>

      <section className="trends-section">
        <h3>Papers per Venue by Year</h3>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={venueChartData}>
              <XAxis dataKey="year" />
              <YAxis />
              <Tooltip />
              <Legend />
              {allVenues.map((venue) => (
                <Line
                  key={venue}
                  type="monotone"
                  dataKey={venue}
                  stroke={VENUE_COLORS[venue] ?? "#888"}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="trends-section">
        <div className="trends-section-header">
          <h3>Top Keywords (All Years)</h3>
          <select
            className="topn-select"
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
          >
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={30}>Top 30</option>
            <option value={50}>Top 50</option>
          </select>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={Math.max(400, topN * 28)}>
            <BarChart data={keywordChartData} layout="vertical" margin={{ left: 140 }}>
              <XAxis type="number" />
              <YAxis dataKey="keyword" type="category" width={130} tick={{ fontSize: 13 }} />
              <Tooltip />
              <Bar dataKey="count" fill="var(--accent)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
