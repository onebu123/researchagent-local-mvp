import {
  BarChart3,
  BookOpen,
  Boxes,
  ChartNoAxesCombined,
  Database,
  FilePenLine,
  FlaskConical,
  Gauge,
  LayoutDashboard,
  Library,
  Settings,
  ShieldCheck,
  Wrench
} from "lucide-react";

const menu = [
  { label: "工作台", icon: LayoutDashboard, active: true },
  { label: "项目管理", icon: Boxes },
  { label: "文献检索", icon: BookOpen },
  { label: "数据分析", icon: Database },
  { label: "实验设计", icon: FlaskConical },
  { label: "论文撰写", icon: FilePenLine },
  { label: "审稿评估", icon: ShieldCheck },
  { label: "可视化图表", icon: ChartNoAxesCombined },
  { label: "工具箱", icon: Wrench },
  { label: "知识库", icon: Library },
  { label: "本地工具网关", icon: Gauge }
];

type SidebarProps = {
  projectName: string;
  createdAt: string;
};

export function Sidebar({ projectName, createdAt }: SidebarProps) {
  return (
    <aside className="hidden min-h-screen border-r border-slate-200 bg-white/78 px-5 py-5 backdrop-blur-xl lg:block">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-[8px] bg-[#5b6ee1] text-white">
          <BarChart3 size={22} />
        </div>
        <div>
          <div className="text-lg font-black tracking-normal">ResearchAgent</div>
          <div className="text-xs font-semibold text-slate-500">AI科研助手</div>
        </div>
      </div>

      <nav className="space-y-1">
        {menu.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              className={`flex w-full items-center gap-3 rounded-[8px] px-3 py-2.5 text-left text-sm font-semibold transition ${
                item.active
                  ? "bg-[#eef1ff] text-[#4052c6]"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="panel mt-8 p-4">
        <div className="mb-3 text-xs font-bold uppercase text-slate-400">当前项目</div>
        <div className="text-sm font-black text-slate-900">{projectName}</div>
        <div className="mt-2 text-xs text-slate-500">创建时间：{new Date(createdAt).toLocaleDateString("zh-CN")}</div>
        <div className="mt-1 text-xs text-slate-500">负责人：研究员</div>
        <button className="secondary-button mt-4 w-full">
          <Settings size={16} />
          项目设置
        </button>
        <div className="mt-4">
          <div className="mb-2 flex justify-between text-xs text-slate-500">
            <span>存储空间</span>
            <span>42%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100">
            <div className="h-2 w-[42%] rounded-full bg-[#12b5cb]" />
          </div>
        </div>
      </div>
    </aside>
  );
}
