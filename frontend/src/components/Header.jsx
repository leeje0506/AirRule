import { Search, Bell } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Pill } from './ui';

const ROLE_LABEL = { admin: '관리자', dev: '개발', subtitle: '자막' };

export default function Header() {
  const { user } = useAuth();
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between shrink-0">
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            placeholder="정책, 항목, 파라미터 검색..."
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>
      <div className="flex items-center gap-4 ml-4">
        <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 border-2 border-white rounded-full" />
        </button>
        <div className="h-6 w-px bg-slate-200" />
        <div className="flex items-center gap-2 text-xs">
          <span className="font-bold text-slate-700">{user?.name}</span>
          <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100 uppercase">
            {ROLE_LABEL[user?.role] || user?.role}
          </span>
        </div>
      </div>
    </header>
  );
}
