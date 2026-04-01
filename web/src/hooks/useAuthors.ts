import { useEffect, useState } from "react";
import type { AuthorSummary } from "../types";

const BASE = import.meta.env.BASE_URL;
let cached: AuthorSummary[] | null = null;

export function useAuthors() {
  const [data, setData] = useState<AuthorSummary[] | null>(cached);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cached) {
      setData(cached);
      return;
    }
    fetch(`${BASE}data/authors.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((authors: AuthorSummary[]) => {
        cached = authors;
        setData(authors);
      })
      .catch((e) => setError(e.message));
  }, []);

  return { data, error };
}
