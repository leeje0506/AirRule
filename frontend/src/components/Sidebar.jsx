import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutGrid, Layers, GitBranch, History, Settings, LogOut, FlaskConical } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV = [
  { path: '/policies',  label: '방송사 정책',     icon: LayoutGrid,   desc: '채널별 정책 아카이브' },
  { path: '/library',   label: '마스터 라이브러리', icon: Layers,       desc: '후처리/검증 항목 관리' },
  { path: '/mapping',   label: '매핑 매트릭스',    icon: GitBranch,    desc: '정책-기술 연결 대시보드' },
  { path: '/test',      label: '테스트',          icon: FlaskConical, desc: 'SRT 파이프라인 테스트' },
  { path: '/history',   label: '수정내역',         icon: History,      desc: '전체 변경 이력' },
];

const ROLE_LABEL = { admin: '관리자', dev: '개발', subtitle: '자막' };

export default function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const nav = useNavigate();

  return (
    <aside className="w-64 bg-slate-900 flex flex-col shrink-0 shadow-2xl">
      {/* Logo */}
      <div className="p-6 pb-4">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Settings className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-base font-black tracking-tight text-white uppercase">AirRule</h1>
            <p className="text-[9px] font-bold text-indigo-400 tracking-widest uppercase">Admin Console</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="space-y-1.5">
          {NAV.map((item) => {
            const active = location.pathname.startsWith(item.path);
            return (
              <button
                key={item.path}
                onClick={() => nav(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                  active
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/40'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <item.icon size={18} className={active ? 'text-white' : 'text-slate-500'} />
                <div className="text-left">
                  <p className="leading-tight text-[13px]">{item.label}</p>
                  <p className={`text-[9px] font-bold uppercase opacity-50 tracking-tight ${active ? 'text-white' : 'text-slate-500'}`}>
                    {item.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* User */}
      <div className="mt-auto p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-black shadow-md">
            {user?.name?.[0] || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-white truncate">{user?.name}</p>
            <p className="text-[10px] text-slate-500">{ROLE_LABEL[user?.role] || user?.role} · {user?.username}</p>
          </div>
          <button onClick={logout} className="p-1.5 text-slate-500 hover:text-red-400 transition-colors" title="로그아웃">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
