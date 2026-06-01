"use client";

import { useRef, type ReactNode } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

export interface Column<T> {
  key: string;
  header: string;
  width?: number;
  render: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
}

interface VirtualTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T, index: number) => string | number;
  height?: number;
  rowHeight?: number;
}

/**
 * Windowed table: only rows in the viewport are mounted in the DOM.
 * Renders 50 or 50,000 rows with the same memory footprint.
 */
export function VirtualTable<T>({
  rows,
  columns,
  rowKey,
  height = 560,
  rowHeight = 44,
}: VirtualTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 12,
  });

  const totalWidth = columns.reduce((sum, c) => sum + (c.width ?? 140), 0);

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      {/* Header */}
      <div
        className="flex bg-surface2 border-b border-border text-xs uppercase tracking-wide text-muted"
        style={{ minWidth: totalWidth }}
      >
        {columns.map((c) => (
          <div
            key={c.key}
            className="px-4 py-3 font-medium shrink-0"
            style={{ width: c.width ?? 140, textAlign: c.align ?? "left" }}
          >
            {c.header}
          </div>
        ))}
      </div>

      {/* Body */}
      <div ref={parentRef} style={{ height, overflow: "auto" }}>
        <div
          style={{
            height: virtualizer.getTotalSize(),
            position: "relative",
            minWidth: totalWidth,
          }}
        >
          {virtualizer.getVirtualItems().map((vRow) => {
            const row = rows[vRow.index];
            return (
              <div
                key={rowKey(row, vRow.index)}
                className="flex items-center border-b border-border/50 text-sm hover:bg-surface2/60 absolute top-0 left-0 w-full"
                style={{ height: vRow.size, transform: `translateY(${vRow.start}px)` }}
              >
                {columns.map((c) => (
                  <div
                    key={c.key}
                    className="px-4 shrink-0 truncate"
                    style={{ width: c.width ?? 140, textAlign: c.align ?? "left" }}
                  >
                    {c.render(row)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
