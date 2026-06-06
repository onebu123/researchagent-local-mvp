import { AlertTriangle, X } from "lucide-react";
import type { SentenceIssue } from "@/lib/types";

type SentenceIssuesPanelProps = {
  open: boolean;
  issues: SentenceIssue[];
  loading?: boolean;
  onClose: () => void;
};

const severityTone: Record<string, string> = {
  major: "bg-rose-50 text-rose-700 ring-rose-200",
  critical: "bg-rose-100 text-rose-800 ring-rose-300",
  minor: "bg-amber-50 text-amber-700 ring-amber-200"
};

export function SentenceIssuesPanel({
  open,
  issues,
  loading = false,
  onClose
}: SentenceIssuesPanelProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <AlertTriangle size={20} className="text-[#f59e0b]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">句子级审稿问题</h2>
                <div className="text-xs font-semibold text-slate-500">{issues.length} issues</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭句子级审稿问题">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-3 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          {!loading && issues.length === 0 ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              review_report.json 当前没有 sentence_issues。
            </div>
          ) : null}
          {issues.map((issue) => (
            <article key={issue.issue_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-black text-slate-950">{issue.issue_id}</span>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                  {issue.section} · P{issue.paragraph_index ?? "-"} / S{issue.sentence_index ?? "-"}
                </span>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                    severityTone[issue.severity] ?? severityTone.minor
                  }`}
                >
                  {issue.severity}
                </span>
                <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                  {issue.issue_type}
                </span>
              </div>
              <p className="text-sm font-semibold leading-6 text-slate-800">{issue.sentence}</p>
              <dl className="mt-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                <div>
                  <dt className="text-slate-400">related_claim_id</dt>
                  <dd className="mt-1 font-mono text-slate-950">{issue.related_claim_id ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">evidence_status</dt>
                  <dd className="mt-1 text-slate-950">{issue.evidence_status ?? "-"}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-slate-400">suggested_revision</dt>
                  <dd className="mt-1 text-slate-950">{issue.suggested_revision}</dd>
                </div>
                {issue.revision_diff ? (
                  <div className="sm:col-span-2">
                    <dt className="text-slate-400">revision_diff</dt>
                    <dd className="mt-1 rounded-[8px] bg-slate-50 p-3 text-slate-950">
                      <div className="font-mono text-xs">{issue.revision_diff.change_type}</div>
                      <div className="mt-2 text-sm leading-6">{issue.revision_diff.after}</div>
                    </dd>
                  </div>
                ) : null}
              </dl>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
