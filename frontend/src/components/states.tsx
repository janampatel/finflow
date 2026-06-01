import { Loader2, AlertCircle, Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-muted py-12 justify-center">
      <Loader2 className="animate-spin" size={18} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 text-danger py-12 text-center">
      <AlertCircle size={22} />
      <div className="text-sm font-medium">Request failed</div>
      <div className="text-xs text-muted max-w-md">{message}</div>
      <div className="text-xs text-muted mt-2">
        Is the API running? <code className="text-accent">uvicorn src.api.main:app --reload</code>
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 text-muted py-12 text-center">
      <Inbox size={22} />
      <div className="text-sm">{children}</div>
    </div>
  );
}
