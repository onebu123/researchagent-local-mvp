import type { LucideIcon } from "lucide-react";

type AgentStatus = "已完成" | "进行中" | "待处理";

type AgentCardProps = {
  title: string;
  description: string;
  status: AgentStatus;
  icon: LucideIcon;
};

const statusStyles: Record<AgentStatus, string> = {
  已完成: "bg-[#eaf8f0] text-[#157347]",
  进行中: "bg-[#eef1ff] text-[#4052c6]",
  待处理: "bg-slate-100 text-slate-500"
};

export function AgentCard({ title, description, status, icon: Icon }: AgentCardProps) {
  return (
    <button className="panel flex min-h-[122px] w-full flex-col items-start gap-3 p-4 text-left transition hover:-translate-y-0.5 hover:shadow-panel">
      <div className="flex w-full items-center justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-slate-950 text-white">
          <Icon size={19} />
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusStyles[status]}`}>
          {status}
        </span>
      </div>
      <div>
        <div className="font-black text-slate-950">{title}</div>
        <div className="mt-1 text-sm leading-5 text-slate-500">{description}</div>
      </div>
    </button>
  );
}
