import { useMemo, useState } from "react";
import { Download, ScrollText, X } from "lucide-react";
import type { AuditLogEntry } from "@/lib/types";

type AuditLogPanelProps = {
  open: boolean;
  entries: AuditLogEntry[];
  loading?: boolean;
  onOpenExport?: () => void;
  onClose: () => void;
};

export function AuditLogPanel({
  open,
  entries,
  loading = false,
  onOpenExport,
  onClose
}: AuditLogPanelProps) {
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const categories = useMemo(
    () => Array.from(new Set(entries.map((entry) => entry.event_category ?? "uncategorized"))),
    [entries]
  );
  const riskLevels = useMemo(
    () => Array.from(new Set(entries.map((entry) => entry.risk_level ?? "unknown"))),
    [entries]
  );
  const filteredEntries = entries.filter((entry) => {
    const category = entry.event_category ?? "uncategorized";
    const risk = entry.risk_level ?? "unknown";
    return (
      (categoryFilter === "all" || categoryFilter === category) &&
      (riskFilter === "all" || riskFilter === risk)
    );
  });
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <ScrollText size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">审计日志</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {filteredEntries.length} / {entries.length} events
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="secondary-button" disabled={loading} onClick={onOpenExport}>
                <Download size={16} />
                <span>Export</span>
              </button>
              <button className="icon-button" onClick={onClose} aria-label="关闭审计日志">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <div className="flex flex-wrap gap-2">
            <select
              className="rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="all">All categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <select
              className="rounded-[8px] border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700"
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
            >
              <option value="all">All risk levels</option>
              {riskLevels.map((risk) => (
                <option key={risk} value={risk}>
                  {risk}
                </option>
              ))}
            </select>
          </div>
          {!loading && filteredEntries.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              当前没有 audit_log.jsonl 记录。
            </div>
          ) : null}
          {filteredEntries.map((entry) => (
            <article key={entry.audit_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{entry.audit_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {entry.event_type}
                </span>
                <span className="rounded-full bg-slate-50 px-2 py-1 font-mono text-[11px] font-bold text-slate-500 ring-1 ring-slate-200">
                  event_category={entry.event_category ?? "uncategorized"}
                </span>
                <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-200">
                  {entry.event_category ?? "uncategorized"}
                </span>
                <span className="rounded-full bg-slate-50 px-2 py-1 font-mono text-[11px] font-bold text-slate-500 ring-1 ring-slate-200">
                  risk_level={entry.risk_level ?? "unknown"}
                </span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                  {entry.risk_level ?? "unknown"}
                </span>
                <span className="text-xs font-semibold text-slate-500">{entry.timestamp}</span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-800">{entry.summary}</p>
              <div className="mt-2 text-xs font-semibold text-slate-500">
                actor={entry.actor.type}:{entry.actor.id} / source={entry.source} / entity=
                {entry.entity_type ?? "-"}:{entry.entity_id ?? "-"}
              </div>
              <dl className="mt-3 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                <div>
                  <dt className="text-slate-400">prev_hash</dt>
                  <dd className="mt-1 break-all font-mono text-slate-950">
                    {entry.prev_hash ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-400">entry_hash</dt>
                  <dd className="mt-1 break-all font-mono text-slate-950">
                    {entry.entry_hash ?? "-"}
                  </dd>
                </div>
              </dl>
              <pre className="mt-3 overflow-x-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(entry.details, null, 2)}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
