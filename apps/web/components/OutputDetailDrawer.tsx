import { FileJson, FileText, Image, Table, X } from "lucide-react";
import { getOutputFileUrl } from "@/lib/api";
import type { OutputContent, OutputItem } from "@/lib/types";

type OutputDetailDrawerProps = {
  open: boolean;
  projectId: string;
  output?: OutputItem;
  content?: OutputContent;
  loading?: boolean;
  onClose: () => void;
};

function textContent(content: OutputContent | undefined): string {
  if (!content || content.content === null) return "";
  if (typeof content.content === "string") return content.content;
  return JSON.stringify(content.content, null, 2);
}

function csvRows(value: string): string[][] {
  return value
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(0, 21)
    .map((line) => line.split(","));
}

function previewIcon(mimeType: string) {
  if (mimeType.includes("json")) return FileJson;
  if (mimeType.includes("csv")) return Table;
  if (mimeType.includes("image")) return Image;
  return FileText;
}

function Preview({
  projectId,
  output,
  content
}: {
  projectId: string;
  output: OutputItem;
  content?: OutputContent;
}) {
  const body = textContent(content);
  if (output.mime_type === "image/png" || output.relative_path.endsWith(".png")) {
    return (
      <div className="rounded-[8px] border border-slate-200 bg-slate-100 p-3">
        <img
          src={getOutputFileUrl(projectId, output.id)}
          alt={output.title}
          className="max-h-[520px] w-full object-contain"
        />
      </div>
    );
  }
  if (output.mime_type === "image/svg+xml" || output.relative_path.endsWith(".svg")) {
    return (
      <div className="rounded-[8px] border border-slate-200 bg-white p-3">
        <iframe title={output.title} srcDoc={body} className="h-[420px] w-full rounded-[8px] bg-white" />
      </div>
    );
  }
  if (output.mime_type === "text/csv" || output.relative_path.endsWith(".csv")) {
    const rows = csvRows(body);
    return (
      <div className="overflow-auto rounded-[8px] border border-slate-200">
        <table className="min-w-full text-left text-xs">
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${rowIndex}-${row.join("|")}`} className={rowIndex === 0 ? "bg-slate-100 font-black" : ""}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`} className="border-b border-slate-200 px-3 py-2">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <pre className="max-h-[620px] overflow-auto whitespace-pre-wrap rounded-[8px] border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
      {body || "该输出没有可内联预览的文本内容。"}
    </pre>
  );
}

export function OutputDetailDrawer({
  open,
  projectId,
  output,
  content,
  loading = false,
  onClose
}: OutputDetailDrawerProps) {
  if (!open || !output) return null;
  const Icon = previewIcon(output.mime_type);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Icon size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">{output.title}</h2>
                <div className="truncate text-xs font-semibold text-slate-500">{output.relative_path}</div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="关闭输出详情">
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="p-5">
          {loading ? (
            <div className="rounded-[8px] border border-slate-200 p-4 text-sm font-semibold text-slate-500">
              加载中...
            </div>
          ) : (
            <Preview projectId={projectId} output={output} content={content} />
          )}
        </div>
      </section>
    </div>
  );
}
