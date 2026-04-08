import { useMemo, useState } from "react";
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
  ReferenceLine,
  Treemap,
} from "recharts";
import type { TrendsData } from "../../types";
import { VENUE_COLORS, formatNumber } from "./constants";

const TRACK_COLORS: Record<string, string> = {
  oral: "#dc2626",
  spotlight: "#f59e0b",
  poster: "#3b82f6",
  main: "#6366f1",
};

function getTrackColor(track: string): string {
  return TRACK_COLORS[track.toLowerCase()] ?? "#94a3b8";
}

interface CompositionTabProps {
  trends: TrendsData;
  selectedYear: string;
  years: string[];
}

function TreemapContent(props: any) {
  const { x, y, width, height, name, value } = props;
  if (width < 40 || height < 30) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={4}
        fill={VENUE_COLORS[name] ?? "#888"} stroke="var(--bg-card)" strokeWidth={2}
      />
      {width > 50 && height > 35 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle"
            fontSize={Math.min(13, width / 6)} fontWeight={600} fill="#fff"
          >
            {name}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle"
            fontSize={Math.min(11, width / 7)} fill="rgba(255,255,255,0.8)"
          >
            {formatNumber(value)}
          </text>
        </>
      )}
    </g>
  );
}

export function CompositionTab({
  trends,
  selectedYear,
  years,
}: CompositionTabProps) {
  const composition = trends.composition;
  const [showAllVenues, setShowAllVenues] = useState(false);

  // Track composition stacked bar data
  const trackData = useMemo(() => {
    const breakdown = composition.track_breakdown_by_year[selectedYear] ?? {};
    return Object.entries(breakdown)
      .map(([venue, tracks]) => ({
        venue,
        ...tracks,
        total: Object.values(tracks).reduce((a, b) => a + b, 0),
      }))
      .sort((a, b) => b.total - a.total);
  }, [composition, selectedYear]);

  const allTracks = useMemo(() => {
    const tracks = new Set<string>();
    trackData.forEach((d) => {
      Object.keys(d).forEach((k) => {
        if (k !== "venue" && k !== "total") tracks.add(k);
      });
    });
    return Array.from(tracks).sort();
  }, [trackData]);

  // Venue growth line chart
  const growthLineData = useMemo(() => {
    return years.map((y) => {
      const entry: Record<string, any> = { year: y };
      for (const [venue, yearCounts] of Object.entries(
        composition.venue_counts_all_years
      )) {
        entry[venue] = yearCounts[y] ?? 0;
      }
      return entry;
    });
  }, [composition, years]);

  const venuesBySize = useMemo(() => {
    const counts = trends.overview.venue_counts_by_year[selectedYear] ?? {};
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([v]) => v);
  }, [trends, selectedYear]);

  const displayedVenues = showAllVenues
    ? venuesBySize
    : venuesBySize.slice(0, 10);

  // Treemap data
  const treemapData = useMemo(() => {
    const counts = trends.overview.venue_counts_by_year[selectedYear] ?? {};
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [trends, selectedYear]);

  // YoY growth rates
  const growthRateData = useMemo(() => {
    const rates = composition.growth_rates_by_year[selectedYear] ?? {};
    return Object.entries(rates)
      .sort((a, b) => b[1] - a[1])
      .map(([venue, rate]) => ({ venue, rate }));
  }, [composition, selectedYear]);

  return (
    <>
      {/* Track Composition */}
      {trackData.length > 0 && (
        <div className="trends-section">
          <h3>Track Composition</h3>
          <div className="chart-container">
            <ResponsiveContainer
              width="100%"
              height={Math.max(300, trackData.length * 40)}
            >
              <BarChart
                data={trackData}
                layout="vertical"
                margin={{ left: 10, right: 30 }}
              >
                <XAxis type="number" tickFormatter={formatNumber} />
                <YAxis
                  dataKey="venue"
                  type="category"
                  width={120}
                  tick={{ fontSize: 13, fontWeight: 600 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    fontSize: "0.85rem",
                  }}
                />
                <Legend />
                {allTracks.map((track) => (
                  <Bar
                    key={track}
                    dataKey={track}
                    stackId="tracks"
                    fill={getTrackColor(track)}
                    name={track}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Venue Growth Over Time */}
      <div className="trends-section">
        <h3>
          Venue Growth Over Time
          {venuesBySize.length > 10 && (
            <button
              className="trends-tab"
              style={{ marginLeft: "1rem", fontSize: "0.8rem" }}
              onClick={() => setShowAllVenues(!showAllVenues)}
            >
              {showAllVenues
                ? "Top 10"
                : `All ${venuesBySize.length}`}
            </button>
          )}
        </h3>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={growthLineData}
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
              {displayedVenues.map((venue) => (
                <Line
                  key={venue}
                  type="monotone"
                  dataKey={venue}
                  stroke={VENUE_COLORS[venue] ?? "#888"}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Venue Size Treemap */}
      <div className="trends-section">
        <h3>Venue Size ({selectedYear})</h3>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <Treemap
              data={treemapData}
              dataKey="value"
              content={<TreemapContent />}
            >
              <Tooltip
                formatter={(value: number, _: string, props: any) => [
                  value.toLocaleString(),
                  props.payload.name,
                ]}
                contentStyle={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  fontSize: "0.85rem",
                }}
              />
            </Treemap>
          </ResponsiveContainer>
        </div>
      </div>

      {/* YoY Growth Rates */}
      {growthRateData.length > 0 && (
        <div className="trends-section">
          <h3>Year-over-Year Growth</h3>
          <div className="chart-container">
            <ResponsiveContainer
              width="100%"
              height={Math.max(300, growthRateData.length * 40)}
            >
              <BarChart
                data={growthRateData}
                layout="vertical"
                margin={{ left: 10, right: 30 }}
              >
                <XAxis
                  type="number"
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  dataKey="venue"
                  type="category"
                  width={120}
                  tick={{ fontSize: 13, fontWeight: 600 }}
                />
                <Tooltip
                  formatter={(value: number) => [`${value.toFixed(1)}%`, "Growth"]}
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    fontSize: "0.85rem",
                  }}
                />
                <ReferenceLine x={0} stroke="var(--text-muted)" />
                <Bar dataKey="rate" radius={[0, 4, 4, 0]} barSize={24}>
                  {growthRateData.map((entry) => (
                    <Cell
                      key={entry.venue}
                      fill={entry.rate >= 0 ? "#16a34a" : "#dc2626"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </>
  );
}
