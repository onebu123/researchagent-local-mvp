import { FileUp, Play, UploadCloud } from "lucide-react";

type UploadPanelProps = {
  running: boolean;
  onRunWorkflow: () => void;
  onUpload: (kind: "literature" | "data", file: File) => void;
};

export function UploadPanel({ running, onRunWorkflow, onUpload }: UploadPanelProps) {
  return (
    <section className="panel p-5">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-black">工作流入口</h2>
          <div className="text-sm font-semibold text-slate-500">上传资料后运行完整 v0.1 pipeline</div>
        </div>
        <button className="primary-button" onClick={onRunWorkflow} disabled={running}>
          <Play size={17} />
          {running ? "运行中" : "运行工作流"}
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex cursor-pointer items-center justify-between rounded-[8px] border border-dashed border-slate-300 bg-white p-4 transition hover:border-[#5b6ee1]">
          <span className="flex items-center gap-3 font-bold text-slate-700">
            <FileUp size={20} className="text-[#5b6ee1]" />
            上传文献
          </span>
          <UploadCloud size={18} className="text-slate-400" />
          <input
            className="hidden"
            type="file"
            accept=".pdf,.md,.markdown,.txt"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onUpload("literature", file);
              event.currentTarget.value = "";
            }}
          />
        </label>
        <label className="flex cursor-pointer items-center justify-between rounded-[8px] border border-dashed border-slate-300 bg-white p-4 transition hover:border-[#12b5cb]">
          <span className="flex items-center gap-3 font-bold text-slate-700">
            <FileUp size={20} className="text-[#12b5cb]" />
            上传数据
          </span>
          <UploadCloud size={18} className="text-slate-400" />
          <input
            className="hidden"
            type="file"
            accept=".csv"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onUpload("data", file);
              event.currentTarget.value = "";
            }}
          />
        </label>
      </div>
    </section>
  );
}
