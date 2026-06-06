import { useEffect, useMemo, useState } from "react";
import { BookOpenCheck, Save, X } from "lucide-react";
import type { LiteraturePatch, LiteratureRecord, LiteratureMetadataStatus } from "@/lib/types";

type LiteratureMetadataPanelProps = {
  open: boolean;
  records: LiteratureRecord[];
  loading?: boolean;
  onSave: (literatureId: string, patch: LiteraturePatch) => Promise<void>;
  onClose: () => void;
};

type DraftRecord = {
  title: string;
  authorsText: string;
  yearText: string;
  doi: string;
  journal: string;
  metadata_status: LiteratureMetadataStatus;
  human_verified: boolean;
};

const metadataStatuses: LiteratureMetadataStatus[] = ["placeholder", "extracted", "verified"];

function toDraft(record: LiteratureRecord): DraftRecord {
  return {
    title: record.title ?? "",
    authorsText: (record.authors ?? []).join(", "),
    yearText: record.year == null ? "" : String(record.year),
    doi: record.doi ?? "",
    journal: record.journal ?? "",
    metadata_status: record.metadata_status,
    human_verified: record.human_verified
  };
}

function toPatch(draft: DraftRecord): LiteraturePatch {
  return {
    title: draft.title,
    authors: draft.authorsText
      .split(",")
      .map((author) => author.trim())
      .filter(Boolean),
    year: draft.yearText.trim() ? Number(draft.yearText) : null,
    doi: draft.doi.trim() || null,
    journal: draft.journal.trim() || null,
    metadata_status: draft.metadata_status,
    human_verified: draft.human_verified
  };
}

export function LiteratureMetadataPanel({
  open,
  records,
  loading = false,
  onSave,
  onClose
}: LiteratureMetadataPanelProps) {
  const initialDrafts = useMemo(
    () => Object.fromEntries(records.map((record) => [record.literature_id, toDraft(record)])),
    [records]
  );
  const [drafts, setDrafts] = useState<Record<string, DraftRecord>>(initialDrafts);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    setDrafts(initialDrafts);
  }, [initialDrafts]);

  if (!open) return null;

  function updateDraft(literatureId: string, patch: Partial<DraftRecord>) {
    setDrafts((current) => ({
      ...current,
      [literatureId]: {
        ...current[literatureId],
        ...patch
      }
    }));
  }

  async function save(record: LiteratureRecord) {
    const draft = drafts[record.literature_id];
    if (!draft) return;
    setSavingId(record.literature_id);
    try {
      await onSave(record.literature_id, toPatch(draft));
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-5xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <BookOpenCheck size={20} className="text-[#18a058]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">文献元数据核验</h2>
                <div className="text-xs font-semibold text-slate-500">{records.length} records</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭文献元数据核验">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">加载中...</div> : null}
          <div className="rounded-[8px] border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">
            未核验文献不得作为正式引用；只有 metadata_status=verified 且 human_verified=true 的记录会进入 Verified references。
          </div>
          {records.map((record) => {
            const draft = drafts[record.literature_id] ?? toDraft(record);
            return (
              <article key={record.literature_id} className="rounded-[8px] border border-slate-200 bg-white p-4">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-black text-slate-950">{record.literature_id}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                    {record.source_type}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    {record.parse_status}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    quality={record.quality_label ?? "-"} / {record.quality_score ?? "-"}
                  </span>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                    needs_manual_review={String(record.needs_manual_review ?? false)}
                  </span>
                </div>

                <div className="mb-4 grid gap-3 text-xs font-semibold text-slate-600 sm:grid-cols-2">
                  <div>
                    <div className="text-slate-400">source_file</div>
                    <div className="mt-1 break-all font-mono text-slate-950">{record.source_file}</div>
                  </div>
                  <div>
                    <div className="text-slate-400">parsed_text_file</div>
                    <div className="mt-1 break-all font-mono text-slate-950">{record.parsed_text_file}</div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="text-xs font-bold text-slate-500">
                    title
                    <input
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.title}
                      onChange={(event) => updateDraft(record.literature_id, { title: event.target.value })}
                    />
                  </label>
                  <label className="text-xs font-bold text-slate-500">
                    authors
                    <input
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.authorsText}
                      onChange={(event) => updateDraft(record.literature_id, { authorsText: event.target.value })}
                    />
                  </label>
                  <label className="text-xs font-bold text-slate-500">
                    year
                    <input
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.yearText}
                      onChange={(event) => updateDraft(record.literature_id, { yearText: event.target.value })}
                    />
                  </label>
                  <label className="text-xs font-bold text-slate-500">
                    doi
                    <input
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.doi}
                      onChange={(event) => updateDraft(record.literature_id, { doi: event.target.value })}
                    />
                  </label>
                  <label className="text-xs font-bold text-slate-500">
                    journal
                    <input
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.journal}
                      onChange={(event) => updateDraft(record.literature_id, { journal: event.target.value })}
                    />
                  </label>
                  <label className="text-xs font-bold text-slate-500">
                    metadata_status
                    <select
                      className="mt-1 w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
                      value={draft.metadata_status}
                      onChange={(event) =>
                        updateDraft(record.literature_id, {
                          metadata_status: event.target.value as LiteratureMetadataStatus
                        })
                      }
                    >
                      {metadataStatuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-2 text-sm font-bold text-slate-700">
                    <input
                      type="checkbox"
                      checked={draft.human_verified}
                      onChange={(event) =>
                        updateDraft(record.literature_id, { human_verified: event.target.checked })
                      }
                    />
                    human_verified
                  </label>
                  <div className="flex items-end justify-end">
                    <button
                      className="primary-button"
                      onClick={() => save(record)}
                      disabled={savingId === record.literature_id}
                    >
                      <Save size={16} />
                      <span>{savingId === record.literature_id ? "保存中" : "保存"}</span>
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
