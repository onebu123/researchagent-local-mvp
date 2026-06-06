const steps = [
  { label: "文献索引", status: "已完成" },
  { label: "数据分析", status: "已完成" },
  { label: "图表来源", status: "已完成" },
  { label: "证据链", status: "已完成" },
  { label: "论文草稿", status: "已完成" },
  { label: "Claim 对齐", status: "已完成" },
  { label: "审稿检查", status: "待处理" }
];

export function WorkflowTimeline() {
  return (
    <section className="panel p-5">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-lg font-black">科研工作流</h2>
        <span className="text-sm font-semibold text-slate-500">v0.3 pipeline</span>
      </div>
      <div className="grid gap-3 md:grid-cols-7">
        {steps.map((step, index) => (
          <div key={step.label} className="relative rounded-[8px] border border-slate-200 bg-white p-3">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-[#eef1ff] text-sm font-black text-[#4052c6]">
              {index + 1}
            </div>
            <div className="font-black text-slate-900">{step.label}</div>
            <div
              className={`mt-1 text-sm font-semibold ${
                step.status === "已完成"
                  ? "text-[#157347]"
                  : step.status === "进行中"
                    ? "text-[#4052c6]"
                    : "text-slate-500"
              }`}
            >
              {step.status}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
