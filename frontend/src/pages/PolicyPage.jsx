import { useState, useEffect } from 'react';
import { ChevronRight, Plus, MoreVertical, Edit3, History, Trash2, Save, Info } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { policyApi, broadcasterApi } from '../api/client';
import { Card, Btn, Pill, Modal, ConfirmDialog, Input, Select } from '../components/ui';
import { RULE_CATEGORIES } from '../components/ruleCategories';

// ── Policy Form Modal ───────────────────────────────────────────

function PolicyFormModal({ open, onClose, initial, broadcasters, onSaved }) {
  const [form, setForm] = useState({ broadcaster_id: '', title: '', version: 'v1.0', status: 'draft', rules: {}, edit_summary: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(initial
        ? { ...initial, edit_summary: '' }
        : { broadcaster_id: broadcasters[0]?.id || '', title: '', version: 'v1.0', status: 'draft', rules: {}, edit_summary: '' }
      );
    }
  }, [initial, open]);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setRule = (key, val) => setForm((f) => ({ ...f, rules: { ...f.rules, [key]: val } }));

  const handleSave = async () => {
    setSaving(true);
    try {
      if (initial) {
        await policyApi.update(initial.id, form);
      } else {
        await policyApi.create(form);
      }
      onSaved();
      onClose();
    } catch (err) {
      alert(err?.response?.data?.detail || '저장 실패');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={initial ? '정책 수정' : '정책 추가'} wide>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Select label="방송사" value={form.broadcaster_id} onChange={(v) => setField('broadcaster_id', v)}
          options={broadcasters.map((b) => ({ value: b.id, label: b.name }))} />
        <Input label="정책명" value={form.title} onChange={(v) => setField('title', v)} placeholder="예: JTBC 예능 가이드라인" />
        <Input label="버전" value={form.version} onChange={(v) => setField('version', v)} placeholder="v1.0" />
        <Select label="상태" value={form.status} onChange={(v) => setField('status', v)}
          options={[{ value: 'draft', label: 'Draft' }, { value: 'review', label: 'Review' }, { value: 'active', label: 'Active' }]} />
      </div>

      <div className="mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-3 block">카테고리별 규칙</span>
        <div className="space-y-3">
          {Object.entries(RULE_CATEGORIES).map(([key, cat]) => (
            <div key={key} className="flex items-start gap-3">
              <div className="flex items-center gap-2 w-28 pt-3 shrink-0">
                <cat.icon size={14} style={{ color: cat.accent }} />
                <span className="text-[11px] font-bold text-slate-500">{cat.label}</span>
              </div>
              <textarea
                value={form.rules[key] || ''}
                onChange={(e) => setRule(key, e.target.value)}
                placeholder="규칙을 입력하세요..."
                className="flex-1 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500 resize-none h-16"
              />
            </div>
          ))}
        </div>
      </div>

      {initial && (
        <Input label="수정 내역 메모" value={form.edit_summary} onChange={(v) => setField('edit_summary', v)} placeholder="변경 사항을 간단히 기록하세요" />
      )}

      <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
        <Btn variant="ghost" onClick={onClose}>취소</Btn>
        <Btn variant="accent" onClick={handleSave} disabled={!form.title || !form.broadcaster_id || saving}>
          <Save size={14} /> {initial ? '저장' : '추가'}
        </Btn>
      </div>
    </Modal>
  );
}

// ── Policy History Modal ────────────────────────────────────────

function PolicyHistoryModal({ open, onClose, policyId, policyTitle }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (open && policyId) {
      policyApi.history(policyId).then(setHistory).catch(() => setHistory([]));
    }
  }, [open, policyId]);

  return (
    <Modal open={open} onClose={onClose} title={`수정내역 — ${policyTitle || ''}`}>
      {history.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">수정 내역이 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {history.map((h) => (
            <div key={h.id} className="flex gap-4 items-start p-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-slate-800">{h.summary}</p>
                <p className="text-[10px] text-slate-400 mt-1">
                  {h.edited_at?.replace('T', ' ')?.slice(0, 19)} · {h.edited_by}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

// ── Main Policy Page ────────────────────────────────────────────

export default function PolicyPage() {
  const { canEditPolicy } = useAuth();
  const [policies, setPolicies] = useState([]);
  const [broadcasters, setBroadcasters] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [historyTarget, setHistoryTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [menuOpen, setMenuOpen] = useState(null);

  const load = async () => {
    const [p, b] = await Promise.all([policyApi.list(), broadcasterApi.list()]);
    setPolicies(p);
    setBroadcasters(b);
  };

  useEffect(() => { load(); }, []);

  const getBroadcaster = (bId) => broadcasters.find((b) => b.id === bId);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await policyApi.delete(deleteTarget.id);
    load();
  };

  return (
    <div className="p-8 lg:p-10">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">방송사별 정책 정리</h2>
          <p className="text-sm text-slate-400 mt-1">각 방송사별 세부 가이드라인을 확인하고 대조할 수 있습니다.</p>
        </div>
        {canEditPolicy && (
          <Btn variant="accent" onClick={() => { setEditTarget(null); setFormOpen(true); }}>
            <Plus size={15} /> 정책 추가
          </Btn>
        )}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                <th className="w-10 px-5 py-4" />
                <th className="px-5 py-4">방송사</th>
                <th className="px-5 py-4">정책명</th>
                <th className="px-5 py-4 text-center">규격</th>
                <th className="px-5 py-4">상태</th>
                <th className="px-5 py-4">업데이트</th>
                {canEditPolicy && <th className="px-5 py-4 text-right">관리</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100/80">
              {policies.map((pol) => {
                const b = getBroadcaster(pol.broadcaster_id);
                const isOpen = expandedId === pol.id;
                return (
                  <tr key={pol.id} className="contents">
                    <tr
                      onClick={() => setExpandedId(isOpen ? null : pol.id)}
                      className={`cursor-pointer transition-colors duration-150 ${isOpen ? 'bg-indigo-50/30' : 'hover:bg-slate-50/60'}`}
                    >
                      <td className="px-5 py-4 text-center">
                        <ChevronRight size={16} className={`text-slate-300 transition-transform duration-200 ${isOpen ? 'rotate-90 text-indigo-500' : ''}`} />
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-[10px] font-black shadow-sm" style={{ background: b?.color || '#6366f1' }}>
                            {b?.name?.[0] || '?'}
                          </div>
                          <span className="font-bold text-slate-700 text-sm">{b?.name || pol.broadcaster_id}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <p className="text-sm font-bold text-slate-800">{pol.title}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{pol.version}</p>
                      </td>
                      <td className="px-5 py-4 text-center">
                        <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                          {pol.rules?.specs || '—'}
                        </span>
                      </td>
                      <td className="px-5 py-4"><Pill type={pol.status} kind="status" /></td>
                      <td className="px-5 py-4 text-[11px] text-slate-400">{pol.updated_at?.slice(0, 10)}</td>
                      {canEditPolicy && (
                        <td className="px-5 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="relative inline-block">
                            <button onClick={() => setMenuOpen(menuOpen === pol.id ? null : pol.id)}
                              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors">
                              <MoreVertical size={15} />
                            </button>
                            {menuOpen === pol.id && (
                              <div className="absolute right-0 top-8 bg-white border border-slate-200 rounded-xl shadow-xl z-20 w-36 py-1">
                                <button onClick={() => { setEditTarget(pol); setFormOpen(true); setMenuOpen(null); }}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                                  <Edit3 size={13} /> 수정
                                </button>
                                <button onClick={() => { setHistoryTarget(pol); setMenuOpen(null); }}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                                  <History size={13} /> 수정내역
                                </button>
                                <button onClick={() => { setDeleteTarget(pol); setMenuOpen(null); }}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-red-600 hover:bg-red-50">
                                  <Trash2 size={13} /> 삭제
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={canEditPolicy ? 7 : 6} className="px-8 py-6 bg-slate-50/40 border-y border-indigo-100/40">
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {Object.entries(RULE_CATEGORIES).map(([key, cat]) => (
                              <div key={key} className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
                                <div className="flex items-center gap-2 mb-2">
                                  <cat.icon size={13} style={{ color: cat.accent }} />
                                  <span className="text-[10px] font-black text-slate-500 uppercase">{cat.label}</span>
                                </div>
                                <p className="text-xs text-slate-700 leading-relaxed">{pol.rules?.[key] || '공통 규격 준수'}</p>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <PolicyFormModal open={formOpen} onClose={() => { setFormOpen(false); setEditTarget(null); }} initial={editTarget} broadcasters={broadcasters} onSaved={load} />
      <PolicyHistoryModal open={!!historyTarget} onClose={() => setHistoryTarget(null)} policyId={historyTarget?.id} policyTitle={historyTarget?.title} />
      <ConfirmDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete}
        title="정책 삭제" message={`"${deleteTarget?.title}" 정책을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`} />
    </div>
  );
}
