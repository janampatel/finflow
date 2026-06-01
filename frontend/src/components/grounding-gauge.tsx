import clsx from "clsx";

export function GroundingGauge({ score, threshold = 0.85 }: { score: number; threshold?: number }) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const passed = score >= threshold;

  return (
    <div className="bg-surface rounded-xl border border-border p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-muted">Grounding Score</span>
        <span
          className={clsx(
            "text-xs font-medium px-2 py-0.5 rounded-full",
            passed ? "bg-success/15 text-success" : "bg-danger/15 text-danger"
          )}
        >
          {passed ? "✓ Passed" : "⚠ Below threshold"}
        </span>
      </div>
      <div className="text-3xl font-bold mb-3">{score.toFixed(3)}</div>
      <div className="h-2.5 rounded-full bg-surface2 overflow-hidden relative">
        <div
          className={clsx("h-full transition-all", passed ? "bg-success" : "bg-danger")}
          style={{ width: `${pct}%` }}
        />
        {/* threshold marker */}
        <div
          className="absolute top-0 h-full w-px bg-white/60"
          style={{ left: `${threshold * 100}%` }}
          title={`threshold ${threshold}`}
        />
      </div>
      <div className="text-[11px] text-muted mt-1.5">
        threshold {threshold} · claims traceable to tool outputs
      </div>
    </div>
  );
}
