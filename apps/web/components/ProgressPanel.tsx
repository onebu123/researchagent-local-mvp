const stages = [
  ["文献调研", 100],
  ["数据分析", 76],
  ["图表生成", 64],
  ["论文草稿", 52],
  ["审稿评估", 38]
] as const;

export function ProgressPanel() {
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black">项目进度</h2>
        <span className="text-sm font-bold text-slate-500">65%</span>
      </div>
      <div className="mx-auto my-5 flex h-36 w-36 items-center justify-center rounded-full bg-[conic-gradient(#5b6ee1_0_65%,#e8edf7_65%_100%)]">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-white text-2xl font-black">
          65%
        </div>
      </div>
      <div className="space-y-3">
        {stages.map(([label, value]) => (
          <div key={label}>
            <div className="mb-1 flex justify-between text-sm font-semibold text-slate-600">
              <span>{label}</span>
              <span>{value}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-[#12b5cb]" style={{ width: `${value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
