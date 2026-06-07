import { BarChart3, RefreshCw, X } from "lucide-react";
import type { StatisticalAssistantReport } from "@/lib/types";

type StatisticalAssistantPanelProps = {
  open: boolean;
  report: StatisticalAssistantReport;
  loading?: boolean;
  actionLoading?: boolean;
  onGenerate: () => Promise<void>;
  onClose: () => void;
};

export function StatisticalAssistantPanel({
  open,
  report,
  loading = false,
  actionLoading = false,
  onGenerate,
  onClose
}: StatisticalAssistantPanelProps) {
  if (!open) return null;

  const healthItems = [
    ["rows", report.dataset.row_count],
    ["columns", report.dataset.column_count],
    ["missing columns", report.data_health.missing_value_columns],
    ["outlier flags", report.data_health.outlier_flagged_columns]
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-6xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BarChart3 size={20} className="text-[#2f6fed]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">Statistical Assistant</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {report.relative_path} / {report.dataset.numeric_columns.length} numeric columns
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close Statistical Assistant">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="flex flex-wrap gap-2">
            <button className="secondary-button" onClick={onGenerate} disabled={actionLoading}>
              <RefreshCw size={16} />
              <span>{actionLoading ? "Generating" : "Generate Local Report"}</span>
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            {healthItems.map(([label, value]) => (
              <div key={label} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold text-slate-400">{label}</div>
                <div className="mt-1 text-sm font-black text-slate-950">{String(value)}</div>
              </div>
            ))}
          </div>

          {report.data_health.warnings.length ? (
            <section className="rounded-[8px] border border-amber-200 bg-amber-50 p-4">
              <h3 className="text-sm font-black text-amber-950">Data Health Warnings</h3>
              <div className="mt-2 space-y-1 text-sm font-semibold text-amber-900">
                {report.data_health.warnings.map((warning) => (
                  <div key={warning}>{warning}</div>
                ))}
              </div>
            </section>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Variable Role Suggestions</h3>
              {report.variable_roles.slice(0, 8).map((item) => (
                <article key={item.column} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-mono text-xs font-black text-slate-950">{item.column}</div>
                    <span className="rounded bg-slate-50 px-2 py-1 text-xs font-black text-slate-700 ring-1 ring-slate-200">
                      {item.dtype}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.role_suggestions.map((role) => (
                      <span key={role} className="rounded bg-slate-50 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                        {role}
                      </span>
                    ))}
                  </div>
                  <div className="mt-3 space-y-1 text-xs font-semibold leading-5 text-slate-500">
                    {item.reasons.map((reason) => (
                      <div key={reason}>{reason}</div>
                    ))}
                  </div>
                </article>
              ))}
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-black text-slate-950">Descriptive Cards</h3>
              {report.descriptive_cards.slice(0, 8).map((card) => (
                <article key={card.column} className="rounded-[8px] border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-mono text-xs font-black text-slate-950">{card.column}</div>
                    <span className="rounded bg-slate-50 px-2 py-1 text-xs font-black text-slate-700 ring-1 ring-slate-200">
                      {card.recommended_visualization}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                    <span>mean {card.mean ?? "-"}</span>
                    <span>std {card.std ?? "-"}</span>
                    <span>min {card.min ?? "-"}</span>
                    <span>max {card.max ?? "-"}</span>
                  </div>
                  <div className="mt-3 text-xs font-semibold text-slate-500">
                    {card.notes.join(" ")}
                  </div>
                </article>
              ))}
            </section>
          </div>

          <section className="space-y-3">
            <h3 className="text-sm font-black text-slate-950">Association Candidates</h3>
            {report.correlation_review.length ? (
              <div className="grid gap-3 lg:grid-cols-2">
                {report.correlation_review.slice(0, 8).map((item) => (
                  <article key={`${item.x}-${item.y}`} className="rounded-[8px] border border-slate-200 p-4">
                    <div className="font-mono text-xs font-black text-slate-950">
                      {item.x} / {item.y}
                    </div>
                    <div className="mt-2 text-sm font-black text-slate-800">
                      r = {item.correlation} · {item.association_strength}
                    </div>
                    <div className="mt-2 text-xs font-semibold leading-5 text-slate-500">
                      {item.recommendation}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
                No moderate or strong local association candidates were flagged.
              </div>
            )}
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-[8px] border border-slate-200 p-4">
              <h3 className="text-sm font-black text-slate-950">Method Suggestions</h3>
              <div className="mt-3 space-y-3">
                {report.method_suggestions.map((item) => (
                  <div key={item.method} className="text-sm font-semibold text-slate-600">
                    <span className="font-mono text-xs font-black text-slate-950">{item.method}</span>
                    <span className="ml-2 rounded bg-slate-50 px-2 py-1 text-xs font-black text-slate-700 ring-1 ring-slate-200">
                      {item.status}
                    </span>
                    <div className="mt-1 text-xs leading-5 text-slate-500">{item.reason}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[8px] border border-slate-200 p-4">
              <h3 className="text-sm font-black text-slate-950">Guardrails</h3>
              <div className="mt-3 space-y-2 text-sm font-semibold leading-6 text-slate-600">
                {report.guardrails.map((item) => (
                  <div key={item}>{item}</div>
                ))}
              </div>
            </div>
          </section>

          <div className="rounded-[8px] border border-slate-200 p-4 text-xs font-semibold leading-6 text-slate-500">
            {report.limitations.join(" ")}
          </div>
        </div>
      </section>
    </div>
  );
}
