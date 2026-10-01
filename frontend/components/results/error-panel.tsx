import { AlertTriangle } from "lucide-react";

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="flex gap-3 border-l-2 border-signal-error/60 px-5 py-5">
      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-signal-error" />
      <div>
        <p className="font-display text-lg text-ivory">Couldn&apos;t answer that one</p>
        <p className="mt-1 max-w-measure text-sm text-ivory-dim">{message}</p>
      </div>
    </div>
  );
}
