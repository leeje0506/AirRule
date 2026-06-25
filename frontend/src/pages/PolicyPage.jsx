import { useState, useEffect, useMemo } from 'react';
import { Save, Pencil, Info, LayoutGrid } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { policyApi, broadcasterApi } from '../api/client';
import { Btn, Modal } from '../components/ui';

// 방송사 표시 순서 (code 기준)
const BC_ORDER = ['JTBC', 'LGHV', 'SKBB', 'TVCS', 'DLIV', 'TVNG'];

function sortBroadcasters(list) {
  return [...list].sort((a, b) => {
    const ia = BC_ORDER.indexOf(a.code);
    const ib = BC_ORDER.indexOf(b.code);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

// 셀 요약값 → 표시 스타일
function cellStyle(summary) {
  const s = (summary || '').trim();
  if (s === 'O') return { text: 'O', cls: 'text-emerald-600 font-bold' };
  if (s === 'X') return { text: 'X', cls: 'text-slate-300' };
  if (s === '△') return { text: '△', cls: 'text-amber-500 font-bold' };
  if (s === '') return { text: '·', cls: 'text-slate-200' };
  return { text: s, cls: 'text-indigo-600 font-semibold' };
}

// ── Cell Edit Modal ─────────────────────────────────────────────

function CellEditModal({ open, onClose, item, broadcaster, value, onSaved }) {
  const [summary, setSummary] = useState('');
  const [detail, setDetail] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setSummary(value?.summary || '');
      setDetail(value?.detail || '');
      setNote('');
    }
  }, [open, value]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await policyApi.upsertValue({
        item_id: item.id,
        broadcaster_id: broadcaster.id,
        summary,
        detail,
        note,
      });
      onSaved();
      onClose();
    } catch (err) {
      alert(err?.response?.data?.detail || '저장 실패');
    } finally {
      setSaving(false);
    }
  };

  if (!open || !item || !broadcaster) return null;

  return (
    <Modal open={open} onClose={onClose} title={`${broadcaster.name} · ${item.name}`} wide>
      {item.description && (
        <div className="flex items-start gap-2 mb-5 p-3 bg-slate-50 rounded-xl border border-slate-100">
          <Info size={14} className="text-slate-400 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-500 leading-relaxed">{item.description}</p>
        </div>
      )}

      <label className="block mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">
          요약값 <span className="text-slate-400 normal-case">(전체 표에 표시 — O / X / △ / 18글자 등)</span>
        </span>
        <input
          type="text"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="O"
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </label>

      <label className="block mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">
          상세 설명 <span className="text-slate-400 normal-case">(방송사별 탭에 풀어서 표시)</span>
        </span>
        <textarea
          value={detail}
          onChange={(e) => setDetail(e.target.value)}
          placeholder="이 방송사의 상세 규칙을 입력하세요..."
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none h-28"
        />
      </label>

      <label className="block mb-2">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">
          변경 사유 <span className="text-slate-400 normal-case">(수정내역에 기록)</span>
        </span>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="예: 방송사 규격 변경 반영"
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </label>

      <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 mt-4">
        <Btn variant="ghost" onClick={onClose}>취소</Btn>
        <Btn variant="accent" onClick={handleSave} disabled={saving}>
          <Save size={14} /> 저장
        </Btn>
      </div>
    </Modal>
  );
}

// ── Matrix (전체) View ──────────────────────────────────────────

function MatrixView({ categories, broadcasters, canEdit, onCellClick }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[720px]">
          <thead className="sticky top-0 z-10">
            <tr className="bg-white border-b border-slate-200">
              <th className="sticky left-0 bg-white px-4 py-2.5 text-[10px] font-bold tracking-wider uppercase text-slate-400 min-w-[220px]">
                항목
              </th>
              {broadcasters.map((b) => (
                <th key={b.id} className="px-2 py-2.5 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span className="w-4 h-4 rounded flex items-center justify-center text-white text-[8px] font-black shrink-0"
                      style={{ background: b.color || '#6366f1' }}>
                      {b.name[0]}
                    </span>
                    <span className="text-[11px] font-bold text-slate-600">{b.name}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {categories.map((cat) => (
              <CategoryRows key={cat.id} cat={cat} broadcasters={broadcasters} canEdit={canEdit} onCellClick={onCellClick} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CategoryRows({ cat, broadcasters, canEdit, onCellClick }) {
  return (
    <>
      <tr>
        <td colSpan={broadcasters.length + 1}
          className="sticky left-0 bg-slate-50 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-y border-slate-100">
          {cat.name}
        </td>
      </tr>
      {cat.items.map((item) => {
        const byBc = {};
        (item.values || []).forEach((v) => { byBc[v.broadcaster_id] = v; });
        return (
          <tr key={item.id} className="border-b border-slate-100/70 hover:bg-slate-50/60 transition-colors">
            <td className="sticky left-0 bg-white px-4 py-2 align-middle">
              <span className="text-[13px] font-medium text-slate-700">{item.name}</span>
              {item.description && (
                <span className="block text-[10px] text-slate-400 leading-snug truncate max-w-[200px]" title={item.description}>
                  {item.description}
                </span>
              )}
            </td>
            {broadcasters.map((b) => {
              const v = byBc[b.id];
              const st = cellStyle(v?.summary);
              const hasDetail = !!(v && v.detail);
              return (
                <td key={b.id} className="px-2 py-1 text-center">
                  <button
                    onClick={() => canEdit && onCellClick(item, b, v)}
                    title={hasDetail ? v.detail : ''}
                    className={`inline-flex items-center justify-center min-w-[34px] px-1.5 py-1 rounded-md text-[13px] ${st.cls} ${canEdit ? 'hover:bg-indigo-50 cursor-pointer' : 'cursor-default'} ${hasDetail ? 'underline decoration-dotted decoration-slate-300 underline-offset-4' : ''}`}
                  >
                    {st.text}
                  </button>
                </td>
              );
            })}
          </tr>
        );
      })}
    </>
  );
}

// ── Broadcaster Detail View ─────────────────────────────────────

function DetailView({ categories, broadcaster, canEdit, onCellClick }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden">
      {categories.map((cat) => (
        <div key={cat.id}>
          <div className="bg-slate-50 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-y border-slate-100">
            {cat.name}
          </div>
          {cat.items.map((item) => {
            const v = (item.values || []).find((x) => x.broadcaster_id === broadcaster.id);
            const st = cellStyle(v?.summary);
            const isMarker = ['O', 'X', '△', '·'].includes(st.text);
            return (
              <div key={item.id} className="flex items-center gap-4 px-4 py-2 border-b border-slate-100/70 hover:bg-slate-50/60 transition-colors group">
                <div className="w-56 shrink-0 flex items-center gap-2.5">
                  {isMarker ? (
                    <span className={`inline-flex items-center justify-center w-5 shrink-0 text-[13px] ${st.cls}`}>{st.text}</span>
                  ) : (
                    <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 text-[11px] font-bold whitespace-nowrap shrink-0">{st.text}</span>
                  )}
                  <span className="text-[13px] font-medium text-slate-700 truncate" title={item.name}>{item.name}</span>
                </div>
                <p className="flex-1 text-[13px] text-slate-600 leading-relaxed min-w-0">
                  {v?.detail || (item.description ? <span className="text-slate-400">{item.description}</span> : <span className="text-slate-300">—</span>)}
                </p>
                {canEdit && (
                  <button
                    onClick={() => onCellClick(item, broadcaster, v)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition-all shrink-0"
                    title="수정"
                  >
                    <Pencil size={13} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// ── Main Policy Page ────────────────────────────────────────────

export default function PolicyPage() {
  const { canEditPolicy } = useAuth();
  const [categories, setCategories] = useState([]);
  const [broadcasters, setBroadcasters] = useState([]);
  const [tab, setTab] = useState('all');
  const [editCell, setEditCell] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const [cats, bs] = await Promise.all([policyApi.matrix(), broadcasterApi.list()]);
    setCategories(cats);
    setBroadcasters(sortBroadcasters(bs));
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const activeBroadcaster = useMemo(
    () => broadcasters.find((b) => b.id === tab) || null,
    [tab, broadcasters]
  );

  const handleCellClick = (item, broadcaster, value) => {
    setEditCell({ item, broadcaster, value });
  };

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-slate-800">방송사별 정책 정리</h2>
        <p className="text-[13px] text-slate-400 mt-0.5">
          전체 탭에서 한눈에 비교하고, 방송사별 탭에서 상세 규칙을 확인합니다.
          {canEditPolicy && ' 셀을 눌러 수정할 수 있습니다.'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 flex-wrap mb-4">
        <button
          onClick={() => setTab('all')}
          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            tab === 'all' ? 'bg-slate-900 text-white' : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          <LayoutGrid size={12} /> 전체
        </button>
        {broadcasters.map((b) => (
          <button
            key={b.id}
            onClick={() => setTab(b.id)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              tab === b.id ? 'text-white' : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'
            }`}
            style={tab === b.id ? { background: b.color || '#6366f1' } : undefined}
          >
            {b.name}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-slate-400 py-12 text-center">불러오는 중...</p>
      ) : tab === 'all' ? (
        <MatrixView categories={categories} broadcasters={broadcasters} canEdit={canEditPolicy} onCellClick={handleCellClick} />
      ) : activeBroadcaster ? (
        <DetailView categories={categories} broadcaster={activeBroadcaster} canEdit={canEditPolicy} onCellClick={handleCellClick} />
      ) : null}

      <CellEditModal
        open={!!editCell}
        onClose={() => setEditCell(null)}
        item={editCell?.item}
        broadcaster={editCell?.broadcaster}
        value={editCell?.value}
        onSaved={load}
      />
    </div>
  );
}