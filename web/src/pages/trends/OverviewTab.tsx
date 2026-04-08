import { useMemo } from "react";
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
} from "recharts";
import type { TrendsData } from "../../types";
import { VENUE_COLORS, formatNumber } from "./constants";

interface OverviewTabProps {
  trends: TrendsData;
  selectedYear: string;
  years: string[];
}

function RankingChart({
  title,
  data,
  growth,
}: {
  title: string;
  data: Record<string, number>;
  growth?: Record<string, number>;
}) {
  const chartData = useMemo(() => {
    return Object.entries(data)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([venue, value]) => ({
        venue,
        value,
        growth: growth?.[venue],
      }));
  }, [data, growth]);

  if (chartData.length === 0) return null;

  return (
    <div className="trends-section">
      <h3>{title}</h3>
      <div className="chart-container">
        <ResponsiveContainer
          width="100%"
          height={Math.max(300, chartData.length * 40)}
        >
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 10, right: 80 }}
          >
            <XAxis type="number" tickFormatter={formatNumber} />
            <YAxis
              dataKey="venue"
              type="category"
              width={120}
              tick={{ fontSize: 13, fontWeight: 600 }}
            />
            <Tooltip
              formatter={(value: any, _name: any, props: any) => {
                const g = props.payload.growth;
                const growthStr =
                  g !== undefined ? ` (${g > 0 ? "+" : ""}${g}%)` : "";
                return [`${Number(value).toLocaleString()}${growthStr}`, title];
              }}
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
    </div>
  );
}

export function OverviewTab({ trends, selectedYear, years }: OverviewTabProps) {
  const overview = trends.overview;
  const venueCounts = overview.venue_counts_by_year[selectedYear] ?? {};
  const citationCounts = overview.citation_counts_by_year[selectedYear] ?? {};
  const growth = overview.growth_pct_by_year[selectedYear];

  const sparklineData = useMemo(() => {
    const allYears = trends.composition.venue_counts_all_years;
    const venues = Object.keys(venueCounts).sort(
      (a, b) => (venueCounts[b] ?? 0) - (venueCounts[a] ?? 0)
    );
    return venues.map((venue) => ({
      venue,
      data: years
        .filter((y) => (allYears[venue]?.[y] ?? 0) > 0)
        .map((y) => ({ year: y, count: allYears[venue]![y] })),
    }));
  }, [trends, venueCounts, years]);

  return (
    <>
      <div className="trends-charts-row">
        <RankingChart
          title="Papers per Venue"
          data={venueCounts}
          growth={growth}
        />
        <RankingChart
          title="Total Citations per Venue"
          data={citationCounts}
        />
      </div>

      <div className="trends-section">
        <h3>Venue Growth</h3>
        <div className="sparkline-grid">
          {sparklineData.map(({ venue, data }) => (
            <div key={venue} className="sparkline-card">
              <div className="sparkline-label">
                <span
                  className="sparkline-dot"
                  style={{
                    background: VENUE_COLORS[venue] ?? "#888",
                  }}
                />
                {venue}
              </div>
              <ResponsiveContainer width="100%" height={48}>
                <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke={VENUE_COLORS[venue] ?? "#888"}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Tooltip
                    formatter={(value: any) => [
                      Number(value).toLocaleString(),
                      "Papers",
                    ]}
                    labelFormatter={(label: any) => String(label)}
                    contentStyle={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius)",
                      fontSize: "0.75rem",
                      padding: "4px 8px",
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
