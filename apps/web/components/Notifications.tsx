import { CheckCircle2, Info, TriangleAlert } from "lucide-react";

type NotificationsProps = {
  apiOnline: boolean;
  message?: string;
};

export function Notifications({ apiOnline, message }: NotificationsProps) {
  const notices = [
    {
      icon: apiOnline ? CheckCircle2 : TriangleAlert,
      title: apiOnline ? "后端连接正常" : "后端不可用，已切换 mock",
      text: apiOnline ? "项目数据来自 FastAPI。" : "当前页面使用本地 mock 数据渲染。",
      tone: apiOnline ? "text-[#157347]" : "text-[#b7791f]"
    },
    {
      icon: Info,
      title: "证据链提醒",
      text: "demo 与 placeholder 内容不可作为真实论文证据。",
      tone: "text-[#4052c6]"
    }
  ];

  return (
    <section className="panel p-5">
      <h2 className="mb-4 text-lg font-black">消息通知</h2>
      {message ? <div className="mb-3 rounded-[8px] bg-[#eef1ff] p-3 text-sm font-semibold text-[#4052c6]">{message}</div> : null}
      <div className="space-y-3">
        {notices.map((notice) => {
          const Icon = notice.icon;
          return (
            <div key={notice.title} className="flex items-start gap-3">
              <Icon size={18} className={notice.tone} />
              <div>
                <div className="text-sm font-black">{notice.title}</div>
                <div className="text-xs leading-5 text-slate-500">{notice.text}</div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
