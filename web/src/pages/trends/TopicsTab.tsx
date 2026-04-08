import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  Legend,
} from "recharts";
import cloud from "d3-cloud";
import type { TrendsData, NgramEntry } from "../../types";
import { VENUE_COLORS, formatNumber } from "./constants";

const TOPIC_COLORS = [
  "#1a6b5a", "#9333ea", "#0369a1", "#dc2626", "#b45309",
  "#6366f1", "#059669", "#ec4899", "#0891b2", "#d946ef",
  "#2563eb", "#ea580c", "#7c3aed", "#15803d", "#a16207",
  "#0d9488", "#be185d", "#4f46e5", "#0e7490", "#a855f7",
  "#6d28d9", "#78716c", "#06b6d4", "#10b981", "#f59e0b",
  "#3b82f6", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316",
];

interface TopicsTabProps {
  trends: TrendsData;
  selectedYear: string;
  years: string[];
}

function WordCloud({ data }: { data: NgramEntry[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [words, setWords] = useState<any[]>([]);
  const width = 700;
  const height = 400;

  useEffect(() => {
    if (data.length === 0) return;

    const maxCount = data[0].count;
    const minCount = data[data.length - 1]?.count ?? 1;
    const scale = (count: number) => {
      const normalized = (count - minCount) / (maxCount - minCount || 1);
      return 14 + Math.sqrt(normalized) * 50;
    };

    const layout = cloud()
      .size([width, height])
      .words(
        data.slice(0, 100).map((d, i) => ({
          text: d.ngram,
          size: scale(d.count),
          color: TOPIC_COLORS[i % TOPIC_COLORS.length],
        }))
      )
      .padding(3)
      .rotate(() => (Math.random() > 0.7 ? 90 : 0))
      .fontSize((d: any) => d.size)
      .on("end", (output: any[]) => setWords(output));

    layout.start();
  }, [data]);

  return (
    <div className="wordcloud-container">
      <svg ref={svgRef} width={width} height={height}>
        <g transform={`translate(${width / 2},${height / 2})`}>
          {words.map((w, i) => (
            <text
              key={i}
              textAnchor="middle"
              transform={`translate(${w.x},${w.y}) rotate(${w.rotate})`}
              fontSize={w.size}
              fontWeight={w.size > 30 ? 700 : 500}
              fill={w.color}
              style={{ cursor: "default" }}
            >
              {w.text}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}

export function TopicsTab({ trends, selectedYear, years }: TopicsTabProps) {
  const topics = trends.topics;
  const topNgrams = topics.top_ngrams_by_year[selectedYear] ?? [];
  const risingFalling = topics.rising_falling_by_year[selectedYear];
  const ngramTrends = topics.ngram_trends;
  const venueMatrix =
    topics.venue_ngram_matrix_by_year[selectedYear] ?? {};

  // Top 20 bar chart data
  const top20 = useMemo(() => topNgrams.slice(0, 20), [topNgrams]);

  // Topic trend line chart
  const trendNgrams = useMemo(
    () => Object.keys(ngramTrends).slice(0, 30),
    [ngramTrends]
  );
  const [activeTrends, setActiveTrends] = useState<Set<string>>(new Set());

  // Default to top 5 when year changes
  useEffect(() => {
    setActiveTrends(new Set(trendNgrams.slice(0, 5)));
  }, [selectedYear]); // eslint-disable-line react-hooks/exhaustive-deps

  const trendLineData = useMemo(
    () =>
      years.map((y) => {
        const entry: Record<string, any> = { year: y };
        for (const ngram of activeTrends) {
          entry[ngram] = ngramTrends[ngram]?.[y] ?? 0;
        }
        return entry;
      }),
    [years, activeTrends, ngramTrends]
  );

  const toggleTrend = (ngram: string) => {
    setActiveTrends((prev) => {
      const next = new Set(prev);
      if (next.has(ngram)) next.delete(ngram);
      else next.add(ngram);
      return next;
    });
  };

  // Heatmap data
  const heatmapNgrams = useMemo(
    () => topNgrams.slice(0, 15).map((e) => e.ngram),
    [topNgrams]
  );
  const heatmapVenues = useMemo(
    () => Object.keys(venueMatrix).sort(),
    [venueMatrix]
  );
  const heatmapMax = useMemo(() => {
    let max = 1;
    for (const venue of heatmapVenues) {
      for (const ngram of heatmapNgrams) {
        const v = venueMatrix[venue]?.[ngram] ?? 0;
        if (v > max) max = v;
      }
    }
    return max;
  }, [venueMatrix, heatmapVenues, heatmapNgrams]);

  return (
    <>
      {/* Word Cloud */}
      <div className="trends-section">
        <h3>Topic Word Cloud ({selectedYear})</h3>
        <WordCloud data={topNgrams} />
      </div>

      {/* Top N-grams Bar */}
      {top20.length > 0 && (
        <div className="trends-section">
          <h3>Top Research Topics</h3>
          <div className="chart-container">
            <ResponsiveContainer
              width="100%"
              height={Math.max(300, top20.length * 36)}
            >
              <BarChart
                data={top20}
                layout="vertical"
                margin={{ left: 10, right: 30 }}
              >
                <XAxis type="number" tickFormatter={formatNumber} />
                <YAxis
                  dataKey="ngram"
                  type="category"
                  width={180}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value: number) => [
                    value.toLocaleString(),
                    "Occurrences",
                  ]}
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    fontSize: "0.85rem",
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={22}>
                  {top20.map((_, i) => (
                    <Cell
                      key={i}
                      fill={TOPIC_COLORS[i % TOPIC_COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Rising & Falling */}
      {risingFalling && (
        <div className="trends-section">
          <h3>Rising & Falling Topics</h3>
          <div className="rising-falling-row">
            <div className="chart-container">
              <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem" }}>
                Rising
              </h4>
              <ul className="rising-falling-list">
                {risingFalling.rising.map((entry, i) => (
                  <li key={i}>
                    <span>{entry.ngram}</span>
                    <span className="delta-positive">
                      +{entry.delta.toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="chart-container">
              <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.9rem" }}>
                Falling
              </h4>
              <ul className="rising-falling-list">
                {risingFalling.falling.map((entry, i) => (
                  <li key={i}>
                    <span>{entry.ngram}</span>
                    <span className="delta-negative">
                      {entry.delta.toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Topic Trends Line Chart */}
      {trendNgrams.length > 0 && (
        <div className="trends-section">
          <h3>Topic Trends Over Time</h3>
          <div className="topic-toggles">
            {trendNgrams.map((ngram, i) => (
              <button
                key={ngram}
                className={`topic-toggle ${activeTrends.has(ngram) ? "active" : ""}`}
                onClick={() => toggleTrend(ngram)}
                style={
                  activeTrends.has(ngram)
                    ? { background: TOPIC_COLORS[i % TOPIC_COLORS.length], borderColor: TOPIC_COLORS[i % TOPIC_COLORS.length] }
                    : undefined
                }
              >
                {ngram}
              </button>
            ))}
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={trendLineData}
                margin={{ left: 10, right: 30 }}
              >
                <XAxis dataKey="year" />
                <YAxis tickFormatter={formatNumber} />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    fontSize: "0.8rem",
                  }}
                  formatter={(value: number) => value.toLocaleString()}
                />
                <Legend />
                {Array.from(activeTrends).map((ngram) => {
                  const idx = trendNgrams.indexOf(ngram);
                  return (
                    <Line
                      key={ngram}
                      type="monotone"
                      dataKey={ngram}
                      stroke={TOPIC_COLORS[idx % TOPIC_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Venue x Topic Heatmap */}
      {heatmapVenues.length > 0 && heatmapNgrams.length > 0 && (
        <div className="trends-section">
          <h3>Venue x Topic Heatmap</h3>
          <div className="chart-container heatmap-container">
            <table className="heatmap-table">
              <thead>
                <tr>
                  <th></th>
                  {heatmapVenues.map((v) => (
                    <th
                      key={v}
                      style={{ color: VENUE_COLORS[v] ?? "inherit" }}
                    >
                      {v}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapNgrams.map((ngram) => (
                  <tr key={ngram}>
                    <td className="ngram-label">{ngram}</td>
                    {heatmapVenues.map((venue) => {
                      const count = venueMatrix[venue]?.[ngram] ?? 0;
                      const intensity = count / heatmapMax;
                      return (
                        <td
                          key={venue}
                          title={`${ngram} @ ${venue}: ${count}`}
                          style={{
                            background: `rgba(26, 107, 90, ${intensity * 0.85})`,
                            color: intensity > 0.5 ? "#fff" : "var(--text-primary)",
                          }}
                        >
                          {count > 0 ? count : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
