import { useState, useEffect } from 'react';
import { History } from 'lucide-react';
import { historyApi } from '../api/client';
import { Card, EmptyState } from '../components/ui';

export default function HistoryPage() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    historyApi.all().then(setHistory).catch(() => setHistory([]));
  }, []);

  return (
    <div className="p-8 lg:p-10">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-800">전체 수정내역</h2>
        <p className="text-sm text-slate-400 mt-1">정책 및 기술 항목의 모든 변경 이력을 확인합니다.</p>
      </div>
      <Card>
        {history.length === 0 ? (
          <EmptyState icon={History} text="수정 내역이 없습니다" />
        ) : (
          <div className="divide-y divide-slate-100">
            {history.map((h) => (
              <div key={h.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/50 transition-colors">
                <div className={`w-2 h-2 rounded-full shrink-0 ${h.kind === 'policy' ? 'bg-blue-500' : 'bg-emerald-500'}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-slate-800">{h.summary}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {h.edited_at?.replace('T', ' ')?.slice(0, 19)} · {h.edited_by} ·
                    <span className={`ml-1 font-bold ${h.kind === 'policy' ? 'text-blue-600' : 'text-emerald-600'}`}>
                      {h.kind === 'policy' ? '정책' : '기술항목'}
                    </span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
