import { ExternalLink, FileText } from "lucide-react";
import type { OutputItem } from "@/lib/types";

type RecentOutputsProps = {
  outputs: OutputItem[];
  onSelect?: (output: OutputItem) => void;
};

export function RecentOutputs({ outputs, onSelect }: RecentOutputsProps) {
  const firstOutput = outputs[0];
  return (
    <section className="panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-black">最新输出</h2>
        <button
          className="text-sm font-bold text-[#4052c6] disabled:text-slate-400"
          disabled={!firstOutput}
          onClick={() => firstOutput && onSelect?.(firstOutput)}
        >
          查看输出
        </button>
      </div>
      <div className="space-y-3">
        {outputs.slice(0, 5).map((output) => (
          <button
            key={output.id}
            className="flex w-full items-start gap-3 rounded-[8px] border border-slate-200 bg-white p-3 text-left transition hover:border-[#5b6ee1] hover:bg-slate-50"
            onClick={() => onSelect?.(output)}
          >
            <FileText size={18} className="mt-0.5 text-[#5b6ee1]" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-black">{output.title}</div>
              <div className="truncate text-xs text-slate-500">{output.relative_path}</div>
            </div>
            <ExternalLink size={16} className="text-slate-400" />
          </button>
        ))}
      </div>
    </section>
  );
}
