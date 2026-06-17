"use client";

import { RefreshCw, RotateCcw, ShieldCheck, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAgentRuns,
  getLatestIterativeResearchLoop,
  runIterativeResearchLoop
} from "@/lib/api";
import type {
  AgentIterativeLoopResult,
  AgentIterativeRound,
  AgentReviewerIssue,
  AgentRunRecord
} from "@/lib/types";

type IterativeAgentLoopPanelProps = {
  projectId?: string;
};

type LoadState = "idle" | "loading" | "running";

const fallbackLoop: AgentIterativeLoopResult = {
  project_id: "demo_project",
  status: "not_run",
  mode: "mock_offline",
  max_rounds: 2,
  executed_rounds: 0,
  stopped_reason: "not_run",
  rounds: [],
  latest_outputs: {},
  formal_draft_modified: false,
  audit_log_file: "audit/audit_log.jsonl",
  available: false,
  message: "Run the local mock loop to generate audited round artifacts."
};

function issueText(issue: AgentReviewerIssue): string {
  return issue.message ?? issue.issue ?? issue.issue_id ?? "Reviewer issue requires attention.";
}

function issueTone(count: number): string {
  return count > 0
    ? "bg-rose-50 text-rose-700 ring-rose-200"
    : "bg-emerald-50 text-emerald-700 ring-emerald-200";
}

function outputValues(loop: AgentIterativeLoopResult): string[] {
  return Object.values(loop.latest_outputs ?? {}).filter((value): value is string => Boolean(value));
}

function roundHumanApproval(round: AgentIterativeRound): boolean {
  if (round.revision_plan) {
    return round.revision_plan.human_approval_required;
  }
  return round.blocking_issue_count > 0;
}

export function IterativeAgentLoopPanel({ projectId = "demo_project" }: IterativeAgentLoopPanelProps) {
  const [loop, setLoop] = useState<AgentIterativeLoopResult>(fallbackLoop);
  const [runs, setRuns] = useState<AgentRunRecord[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [apiOnline, setApiOnline] = useState(false);
  const [message, setMessage] = useState<string>("Mock/offline mode is the default.");

  const refresh = useCallback(async () => {
    setLoadState("loading");
    try {
      const [latest, agentRuns] = await Promise.all([
        getLatestIterativeResearchLoop(projectId),
        getAgentRuns(projectId)
      ]);
      setLoop({ ...fallbackLoop, ...latest, project_id: projectId });
      setRuns(agentRuns);
      setApiOnline(true);
      setMessage(latest.available === false ? latest.message ?? "No loop run yet." : "Latest loop loaded.");
    } catch (error) {
      setLoop({ ...fallbackLoop, project_id: projectId });
      setRuns([]);
      setApiOnline(false);
      setMessage(error instanceof Error ? error.message : "Backend unavailable; showing demo state.");
    } finally {
      setLoadState("idle");
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleRun() {
    setLoadState("running");
    try {
      const result = await runIterativeResearchLoop(projectId, 2);
      const agentRuns = await getAgentRuns(projectId);
      setLoop(result);
      setRuns(agentRuns);
      setApiOnline(true);
      setMessage("Iterative loop completed in mock/offline mode.");
    } catch (error) {
      setApiOnline(false);
      setMessage(error instanceof Error ? error.message : "Loop could not run.");
    } finally {
      setLoadState("idle");
    }
  }

  const outputs = useMemo(() => outputValues(loop), [loop]);

  return (
    <section className="mb-8 rounded-[8px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-cyan-50 px-2 py-1 text-xs font-bold text-cyan-700 ring-1 ring-cyan-200">
              Mock Mode
            </span>
            <span
              className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${
                apiOnline ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-amber-50 text-amber-700 ring-amber-200"
              }`}
            >
              {apiOnline ? "Backend connected" : "Demo Mode"}
            </span>
          </div>
          <h3 className="text-xl font-semibold text-slate-950">Iterative Agent Loop</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Generator to reviewer group to reviser, with round artifacts, blocking issues, revision plan paths,
            and human approval status kept explicit.
          </p>
          <p className="mt-2 text-xs font-semibold text-slate-500">{message}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleRun}
            disabled={loadState === "running"}
            className="inline-flex items-center gap-2 rounded-[8px] bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            <RotateCcw size={16} />
            {loadState === "running" ? "Running" : "Run Loop"}
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loadState === "loading"}
            className="inline-flex items-center gap-2 rounded-[8px] border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Executed rounds</div>
          <div className="mt-1 text-2xl font-semibold text-slate-950">{loop.executed_rounds}</div>
        </div>
        <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Max rounds</div>
          <div className="mt-1 text-2xl font-semibold text-slate-950">{loop.max_rounds}</div>
        </div>
        <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Stopped reason</div>
          <div className="mt-2 break-words text-sm font-semibold text-slate-950">{loop.stopped_reason}</div>
        </div>
        <div className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Agent runs</div>
          <div className="mt-1 text-2xl font-semibold text-slate-950">{runs.length}</div>
        </div>
      </div>

      {loop.rounds.length === 0 ? (
        <div className="mt-5 rounded-[8px] border border-dashed border-slate-300 p-4 text-sm font-semibold text-slate-600">
          Round 1 / Round 2 will appear here after the mock loop runs.
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {loop.rounds.map((round) => (
            <article key={round.round_id} className="rounded-[8px] border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h4 className="text-base font-semibold text-slate-950">Round {round.round_number}</h4>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
                    <span>{round.draft_file}</span>
                    <span>{round.revised_file}</span>
                  </div>
                </div>
                <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${issueTone(round.blocking_issue_count)}`}>
                  {round.blocking_issue_count} blocking issues
                </span>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {round.reviewer_records.map((reviewer) => (
                  <div key={`${round.round_id}-${reviewer.reviewer_name}`} className="rounded-[8px] border border-slate-200 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-950">{reviewer.reviewer_name}</div>
                      <span className={`rounded-full px-2 py-1 text-xs font-bold ring-1 ${issueTone(reviewer.blocking_issues.length)}`}>
                        {reviewer.blocking_issues.length}
                      </span>
                    </div>
                    <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
                      {reviewer.blocking_issues.slice(0, 2).map((issue) => (
                        <li key={issue.issue_id ?? issueText(issue)} className="flex gap-2">
                          <TriangleAlert size={14} className="mt-0.5 shrink-0 text-rose-600" />
                          <span>{issueText(issue)}</span>
                        </li>
                      ))}
                      {reviewer.blocking_issues.length === 0 ? (
                        <li className="flex gap-2">
                          <ShieldCheck size={14} className="mt-0.5 shrink-0 text-emerald-600" />
                          <span>No blocking issue recorded.</span>
                        </li>
                      ) : null}
                    </ul>
                  </div>
                ))}
              </div>

              <div className="mt-4 rounded-[8px] border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-slate-950">Revision plan</div>
                    <div className="mt-1 font-mono text-xs text-slate-500">{round.revision_plan_file}</div>
                  </div>
                  <span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700 ring-1 ring-amber-200">
                    human approval required: {String(roundHumanApproval(round))}
                  </span>
                </div>
                {round.revision_plan?.patches.length ? (
                  <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-600">
                    {round.revision_plan.patches.slice(0, 3).map((patch) => (
                      <li key={patch.patch_id}>
                        <span className="font-mono font-semibold text-slate-800">{patch.patch_id}</span>: {patch.issue}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}

      {outputs.length ? (
        <div className="mt-5">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Latest output files</div>
          <div className="flex flex-wrap gap-2">
            {outputs.map((output) => (
              <span key={output} className="rounded bg-slate-50 px-2 py-1 font-mono text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                {output}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
