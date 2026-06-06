import { BookMarked, Code2, Database, FileText, Image } from "lucide-react";
import type { ResourceSummary } from "@/lib/types";

type ResourcePanelProps = {
  resources: ResourceSummary;
};

export function ResourcePanel({ resources }: ResourcePanelProps) {
  const items = [
    { label: "文献资料", value: resources.literature_count, icon: BookMarked },
    { label: "数据集", value: resources.dataset_count, icon: Database },
    { label: "实验记录", value: 4, icon: FileText },
    { label: "代码文件", value: 9, icon: Code2 },
    { label: "图片/图表", value: resources.figure_count, icon: Image }
  ];

  return (
    <section className="panel p-5">
      <h2 className="mb-4 text-lg font-black">项目资源</h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="rounded-[8px] border border-slate-200 bg-white p-4">
              <Icon size={20} className="text-[#5b6ee1]" />
              <div className="mt-3 text-2xl font-black">{item.value}</div>
              <div className="text-sm font-semibold text-slate-500">{item.label}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
