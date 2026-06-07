import { Bot, Play, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import type { LLMStatus, LLMTestResult, PromptRegistry } from "@/lib/types";

type LLMSettingsPanelProps = {
  open: boolean;
  status: LLMStatus;
  promptRegistry: PromptRegistry;
  testResult?: LLMTestResult;
  loading?: boolean;
  actionLoading?: boolean;
  onRefresh: () => void;
  onTest: (prompt: string) => Promise<void>;
  onClose: () => void;
};

export function LLMSettingsPanel({
  open,
  status,
  promptRegistry,
  testResult,
  loading = false,
  actionLoading = false,
  onRefresh,
  onTest,
  onClose
}: LLMSettingsPanelProps) {
  const [prompt, setPrompt] = useState("Return a short JSON health check.");
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/28">
      <section className="h-full w-full max-w-4xl overflow-y-auto bg-white shadow-2xl">
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <Bot size={20} className="text-[#5b6ee1]" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-black">LLM Settings</h2>
                <div className="text-xs font-semibold text-slate-500">
                  {status.effective_mode} / {status.model}
                </div>
              </div>
            </div>
            <button className="icon-button" onClick={onClose} aria-label="Close LLM Settings">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          {loading ? <div className="text-sm font-semibold text-slate-500">Loading...</div> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["mode", status.mode],
              ["effective_mode", status.effective_mode],
              ["provider", status.provider],
              ["model", status.model],
              ["base_url_host", status.base_url_host],
              ["api_key_configured", String(status.api_key_configured)],
              ["timeout_seconds", String(status.timeout_seconds)],
              ["max_retries", String(status.max_retries)]
            ].map(([label, value]) => (
              <div key={label} className="rounded-[8px] border border-slate-200 p-3">
                <div className="text-xs font-bold text-slate-400">{label}</div>
                <div className="mt-1 break-all text-sm font-black text-slate-950">{value}</div>
              </div>
            ))}
          </div>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-black text-slate-950">Prompt Registry</h3>
                <div className="text-xs font-semibold text-slate-500">{promptRegistry.count} prompts</div>
              </div>
              <button className="secondary-button" onClick={onRefresh}>
                <RefreshCw size={16} />
                <span>Refresh</span>
              </button>
            </div>
            <div className="grid gap-2">
              {promptRegistry.prompts.map((item) => (
                <div key={item.prompt_version} className="rounded-[8px] bg-slate-50 p-3">
                  <div className="font-mono text-xs font-black text-slate-950">{item.prompt_version}</div>
                  <div className="mt-1 text-xs font-semibold text-slate-600">{item.purpose}</div>
                  <div className="mt-2 break-all font-mono text-[11px] font-semibold text-slate-400">
                    {item.file_name} / {item.content_sha256.slice(0, 12)}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[8px] border border-slate-200 p-4">
            <h3 className="text-sm font-black text-slate-950">LLM Test</h3>
            <textarea
              className="mt-3 min-h-[92px] w-full rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-950"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <div className="mt-3 flex justify-end">
              <button className="primary-button" onClick={() => onTest(prompt)} disabled={actionLoading}>
                <Play size={16} />
                <span>{actionLoading ? "Testing" : "Run Test"}</span>
              </button>
            </div>
            {testResult ? (
              <pre className="mt-3 max-h-[260px] overflow-auto rounded-[8px] bg-slate-50 p-3 text-xs font-semibold text-slate-800">
                {JSON.stringify(testResult, null, 2)}
              </pre>
            ) : null}
          </article>
        </div>
      </section>
    </div>
  );
}
