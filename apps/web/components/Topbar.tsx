import { Bell, CircleHelp, Moon, Search } from "lucide-react";

type TopbarProps = {
  projectName: string;
  apiOnline: boolean;
};

export function Topbar({ projectName, apiOnline }: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-[#f6f8fc]/82 px-5 py-4 backdrop-blur-xl">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="text-xs font-bold text-slate-500">当前项目</div>
          <h1 className="text-xl font-black tracking-normal text-slate-950">{projectName}</h1>
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-3 xl:max-w-3xl">
          <div className="flex min-w-0 flex-1 items-center gap-2 rounded-[8px] border border-slate-200 bg-white px-3 py-2.5">
            <Search size={18} className="text-slate-400" />
            <input
              className="min-w-0 flex-1 bg-transparent text-sm outline-none"
              placeholder="搜索文献、数据、任务或输入..."
            />
          </div>
          <button className="icon-button" title="通知">
            <Bell size={18} />
          </button>
          <button className="icon-button" title="帮助">
            <CircleHelp size={18} />
          </button>
          <button className="icon-button" title="主题">
            <Moon size={18} />
          </button>
          <div className="flex items-center gap-2 rounded-[8px] border border-slate-200 bg-white px-2 py-1.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-[#152033] text-xs font-black text-white">
              研
            </div>
            <div className="hidden sm:block">
              <div className="text-xs font-black">研究员</div>
              <div className="flex items-center gap-1 text-[11px] text-slate-500">
                <span className="status-dot" />
                {apiOnline ? "后端在线" : "本地 mock"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
