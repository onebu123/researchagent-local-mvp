import type { LucideIcon } from "lucide-react";

type StatCardProps = {
  label: string;
  value: string;
  tone: "indigo" | "cyan" | "green" | "amber";
  icon: LucideIcon;
};

const tones = {
  indigo: "bg-[#eef1ff] text-[#4052c6]",
  cyan: "bg-[#e8fbfe] text-[#087f8f]",
  green: "bg-[#eaf8f0] text-[#157347]",
  amber: "bg-[#fff7e6] text-[#b7791f]"
};

export function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  return (
    <div className="panel flex min-h-[104px] items-center justify-between p-4">
      <div>
        <div className="text-2xl font-black text-slate-950">{value}</div>
        <div className="mt-1 text-sm font-semibold text-slate-500">{label}</div>
      </div>
      <div className={`flex h-11 w-11 items-center justify-center rounded-[8px] ${tones[tone]}`}>
        <Icon size={22} />
      </div>
    </div>
  );
}
