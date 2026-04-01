import { useEffect, useState } from "react";
import type { Paper } from "../types";

const BASE = import.meta.env.BASE_URL;
const cache = new Map<string, Paper[]>();

export function useConferenceData(id: string | undefined) {
  const [data, setData] = useState<Paper[] | null>(id && cache.has(id) ? cache.get(id)! : null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    if (cache.has(id)) {
      setData(cache.get(id)!);
      return;
    }
    setData(null);
    setError(null);
    fetch(`${BASE}data/${id}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((papers: Paper[]) => {
        cache.set(id, papers);
        setData(papers);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  return { data, error };
}
