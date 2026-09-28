type Confidence = "High" | "Medium" | "Low";

const COLORS: Record<Confidence, string> = {
  High: "bg-green-100 text-green-800",
  Medium: "bg-amber-100 text-amber-800",
  Low: "bg-red-100 text-red-800",
};

export function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${COLORS[level]}`}>
      {level} confidence
    </span>
  );
}
