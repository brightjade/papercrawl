export const VENUE_COLORS: Record<string, string> = {
  // ML
  ICLR: "#1a6b5a",
  NeurIPS: "#9333ea",
  ICML: "#0369a1",
  AAAI: "#6366f1",
  IJCAI: "#4f46e5",
  COLM: "#ec4899",
  CoRL: "#d946ef",
  // NLP
  EMNLP: "#b45309",
  ACL: "#dc2626",
  NAACL: "#059669",
  EACL: "#10b981",
  COLING: "#ea580c",
  // CV
  CVPR: "#2563eb",
  ICCV: "#7c3aed",
  ECCV: "#a855f7",
  WACV: "#6d28d9",
  // Robotics
  ICRA: "#0891b2",
  IROS: "#0e7490",
  RSS: "#06b6d4",
  // Security
  "USENIX Security": "#78716c",
  // SE
  ICSE: "#0d9488",
  FSE: "#a16207",
  ASE: "#15803d",
  ISSTA: "#be185d",
};

export function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}
