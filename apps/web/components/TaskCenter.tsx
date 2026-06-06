const tasks = [
  ["分析钙钛矿材料 XRD 数据", "Analysis Agent", "进行中", "高", "今日", "查看"],
  ["设计材料稳定性实验方案", "Topic Agent", "待处理", "中", "明日", "创建"],
  ["撰写结果与讨论部分", "Manuscript Agent", "待处理", "高", "周五", "打开"],
  ["评估论文创新性与完整性", "Reviewer Agent", "已完成", "中", "昨日", "查看"],
  ["收集相关领域最新文献", "Literature Agent", "待处理", "低", "下周", "检索"]
];

export function TaskCenter() {
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 p-5">
        <h2 className="text-lg font-black">任务中心</h2>
        <button className="secondary-button">创建任务</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              {["任务名称", "所属智能体", "状态", "优先级", "截止时间", "操作"].map((head) => (
                <th key={head} className="px-5 py-3 font-black">
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task[0]} className="border-t border-slate-100">
                {task.map((cell, index) => (
                  <td key={cell} className="px-5 py-3 font-semibold text-slate-700">
                    {index === 5 ? <button className="text-[#4052c6]">{cell}</button> : cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
