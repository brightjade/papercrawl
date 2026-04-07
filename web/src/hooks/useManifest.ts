import { useEffect, useState } from "react";
import type { ConferenceMeta } from "../types";

const BASE = import.meta.env.BASE_URL;

export function useManifest() {
  const [data, setData] = useState<ConferenceMeta[] | null>(null);
  const [citationUpdated, setCitationUpdated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE}data/manifest.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        setData(json.conferences);
        setCitationUpdated(json.citation_updated ?? null);
      })
      .catch((e) => setError(e.message));
  }, []);

  return { data, citationUpdated, error };
}
