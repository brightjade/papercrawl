import { useEffect, useState } from "react";
import type { TrendsData } from "../types";

const BASE = import.meta.env.BASE_URL;
let cached: TrendsData | null = null;

export function useTrends() {
  const [data, setData] = useState<TrendsData | null>(cached);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cached) {
      setData(cached);
      return;
    }
    fetch(`${BASE}data/trends.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((trends: TrendsData) => {
        cached = trends;
        setData(trends);
      })
      .catch((e) => setError(e.message));
  }, []);

  return { data, error };
}
