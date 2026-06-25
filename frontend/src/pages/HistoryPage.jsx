import { useState, useEffect, useMemo } from 'react';
import { History } from 'lucide-react';
import { historyApi, policyApi } from '../api/client';
import { Card, EmptyState } from '../components/ui';

// 정책 이력 항목 → 표시용 summary (필드명이 조금 달라도 견디게 방어적으로)
function policySummary(h) {
  if (h.summary) return h.summary;
  const item = h.item_name || h.item || '';
  const bc = h.broadcaster_name || h.broadcaster || '';
  const ov = h.old_summary ?? h.old ?? '';
  const nv = h.new_summary ?? h.new ?? '';
  const change = (ov !== '' || nv !== '') ? `${ov === '' ? '∅' : ov} → ${nv === '' ? '∅' : nv}` : '';
  const note = h.note ? ` (${h.note})` : '';
  const head = [item, bc].filter(Boolean).join(' · ');
  const body = `${head}${head && change ? ': ' : ''}${change}${note}`.trim();
  return body || '정책 변경';
}

export default function HistoryPage() {
  const [tech, setTech] = useState([]);
  const [policy, setPolicy] = useState([]);
  const [filter, setFilter] = useState('all'); // all | policy | tech

  useEffect(() => {
    historyApi.all().then(setTech).catch(() => setTech([]));
    policyApi.history().then(setPolicy).catch(() => setPolicy([]));
  }, []);

  const merged = useMemo(() => {
    const t = (tech || []).map((h) => ({
      id: h.id,
      kind: 'tech',
      summary: h.summary || '기술 항목 변경',
      edited_by: h.edited_by,
      edited_at: h.edited_at,
    }));
    const p = (policy || []).map((h) => ({
      id: h.id,
      kind: 'policy',
      summary: policySummary(h),
      edited_by: h.edited_by,
      edited_at: h.edited_at,
    }));
    return [...t, ...p].sort((a, b) => (b.edited_at || '').localeCompare(a.edited_at || ''));
  }, [tech, policy]);

  const shown = useMemo(
    () => (filter === 'all' ? merged : merged.filter((h) => h.kind === filter)),
    [merged, filter]
  );

  const filters = [
    { k: 'all', l: '전체' },
    { k: 'policy', l: '정책' },
    { k: 'tech', l: '기술항목' },
  ];

  return (
    <div className="p-8 lg:p-10">
      <div className="flex justify-between items-end mb-8 gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">전체 수정내역</h2>
          <p className="text-sm text-slate-400 mt-1">정책 및 기술 항목의 모든 변경 이력을 시간순으로 확인합니다.</p>
        </div>
        <div className="flex bg-white p-1 rounded-xl border border-slate-200 shadow-sm">
          {filters.map((f) => (
            <button key={f.k} onClick={() => setFilter(f.k)}
              className={`px-4 py-2 text-[11px] font-bold rounded-lg transition-all ${
                filter === f.k ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50'
              }`}>
              {f.l}
            </button>
          ))}
        </div>
      </div>

      <Card>
        {shown.length === 0 ? (
          <EmptyState icon={History} text="수정 내역이 없습니다" />
        ) : (
          <div className="divide-y divide-slate-100">
            {shown.map((h) => (
              <div key={`${h.kind}_${h.id}`} className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50/50 transition-colors">
                <div className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${h.kind === 'policy' ? 'bg-blue-500' : 'bg-emerald-500'}`} />
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