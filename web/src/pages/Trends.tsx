import { useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
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
  ICSE: "#0d9488",
  FSE: "#a16207",
  ASE: "#7c3aed",
  ISSTA: "#be185d",
};

function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

interface RankingChartProps {
  title: string;
  data: Record<string, Record<string, number>>;
}

function RankingChart({ title, data }: RankingChartProps) {
  const years = useMemo(() => Object.keys(data).sort(), [data]);
  const [selectedYear, setSelectedYear] = useState(() => years[years.length - 1] ?? "");

  const chartData = useMemo(() => {
    const counts = data[selectedYear] ?? {};
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([venue, value]) => ({ venue, value }));
  }, [data, selectedYear]);

  if (years.length === 0) return null;

  return (
    <section className="trends-section">
      <div className="trends-section-header">
        <h3>{title}</h3>
        <div className="year-tabs">
          {years.map((year) => (
            <button
              key={year}
              className={`year-tab ${year === selectedYear ? "active" : ""}`}
              onClick={() => setSelectedYear(year)}
            >
              {year}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 40)}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30 }}>
            <XAxis type="number" tickFormatter={formatNumber} />
            <YAxis
              dataKey="venue"
              type="category"
              width={120}
              tick={{ fontSize: 13, fontWeight: 600 }}
            />
            <Tooltip
              formatter={(value: number) => value.toLocaleString()}
              contentStyle={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                fontSize: "0.85rem",
              }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.venue}
                  fill={VENUE_COLORS[entry.venue] ?? "#888"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function Trends() {
  const { data: trends, error } = useTrends();

  if (error) return <div className="loading">Error: {error}</div>;
  if (!trends) return <div className="loading">Loading trends...</div>;

  return (
    <div className="trends-page">
      <h2 className="page-title">Trends</h2>
      <p className="page-subtitle">Paper counts and citation trends across conferences</p>

      <RankingChart title="Papers per Venue" data={trends.venue_counts_by_year} />
      <RankingChart title="Total Citations per Venue" data={trends.citation_counts_by_year} />
    </div>
  );
}
