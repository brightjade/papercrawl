import { useMemo, useState } from "react";
import { useTrends } from "../hooks/useTrends";
import { OverviewTab } from "./trends/OverviewTab";
import { TopicsTab } from "./trends/TopicsTab";
import { ImpactTab } from "./trends/ImpactTab";
import { CompositionTab } from "./trends/CompositionTab";
import "./Trends.css";

type Tab = "overview" | "topics" | "impact" | "composition";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "topics", label: "Topics" },
  { id: "impact", label: "Impact" },
  { id: "composition", label: "Composition" },
];

export function Trends() {
  const { data: trends, error } = useTrends();
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const years = useMemo(() => {
    if (!trends) return [];
    return Object.keys(trends.overview.venue_counts_by_year).sort();
  }, [trends]);

  const [selectedYear, setSelectedYear] = useState("");

  // Set default year to latest when data loads
  const effectiveYear = selectedYear || years[years.length - 1] || "";

  if (error) return <div className="loading">Error: {error}</div>;
  if (!trends) return <div className="loading">Loading trends...</div>;

  return (
    <div className="trends-page">
      <h2 className="page-title">Trends</h2>
      <p className="page-subtitle">
        Paper counts, topic analysis, citation impact, and venue composition
      </p>

      <div className="trends-controls">
        <div className="trends-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`trends-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="year-tabs">
          {years.map((year) => (
            <button
              key={year}
              className={`year-tab ${year === effectiveYear ? "active" : ""}`}
              onClick={() => setSelectedYear(year)}
            >
              {year}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "overview" && (
        <OverviewTab
          trends={trends}
          selectedYear={effectiveYear}
          years={years}
        />
      )}
      {activeTab === "topics" && (
        <TopicsTab
          trends={trends}
          selectedYear={effectiveYear}
          years={years}
        />
      )}
      {activeTab === "impact" && (
        <ImpactTab
          trends={trends}
          selectedYear={effectiveYear}
          years={years}
        />
      )}
      {activeTab === "composition" && (
        <CompositionTab
          trends={trends}
          selectedYear={effectiveYear}
          years={years}
        />
      )}
    </div>
  );
}
