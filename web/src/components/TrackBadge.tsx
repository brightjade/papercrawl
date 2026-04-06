import "./TrackBadge.css";

const TRACK_COLORS: Record<string, string> = {
  oral: "#b45309",
  spotlight: "#9333ea",
  poster: "#0369a1",
  main: "#1a6b5a",
  findings: "#6b7280",
};

export function TrackBadge({ track }: { track: string }) {
  const color = TRACK_COLORS[track.toLowerCase()] ?? "#6b7280";
  return (
    <span className="track-badge" style={{ "--badge-color": color } as React.CSSProperties}>
      {track}
    </span>
  );
}
