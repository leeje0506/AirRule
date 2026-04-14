import { useState, useEffect, useMemo } from 'react';
import { Plus, Edit3, Save, X, Info, Code2, Copy, Check as CheckIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { techItemApi } from '../api/client';
import { Card, Btn, Pill, Modal, Input, Select } from '../components/ui';

// ── Tech Item Form Modal ────────────────────────────────────────

function TechItemFormModal({ open, onClose, initial, onSaved }) {
  const [form, setForm] = useState({ type: 'processing', name: '', desc: '', params: {}, scope: 'common', tag: 'planned', source_code: '', edit_summary: '' });
  const [paramKey, setParamKey] = useState('');
  const [paramVal, setParamVal] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(initial ? { ...initial, edit_summary: '' } : { type: 'processing', name: '', desc: '', params: {}, scope: 'common', tag: 'planned', source_code: '', edit_summary: '' });
      setParamKey(''); setParamVal('');
    }
  }, [initial, open]);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const addParam = () => {
    if (paramKey.trim()) {
      setForm((f) => ({ ...f, params: { ...f.params, [paramKey.trim()]: paramVal.trim() } }));
      setParamKey(''); setParamVal('');
    }
  };
  const removeParam = (k) => setForm((f) => { const p = { ...f.params }; delete p[k]; return { ...f, params: p }; });

  const handleSave = async () => {
    setSaving(true);
    try {
      if (initial) {
        await techItemApi.update(initial.id, form);
      } else {
        await techItemApi.create(form);
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
    <Modal open={open} onClose={onClose} title={initial ? '항목 수정' : '항목 추가'}>
      <div className="grid grid-cols-2 gap-4">
        <Select label="분류" value={form.type} onChange={(v) => setField('type', v)}
          options={[{ value: 'processing', label: '후처리' }, { value: 'validation', label: '검증' }]} />
        <Select label="범위" value={form.scope} onChange={(v) => setField('scope', v)}
          options={[{ value: 'common', label: 'Common' }, { value: 'specific', label: 'Specific' }]} />
      </div>
      <Select label="태그" value={form.tag} onChange={(v) => setField('tag', v)}
        options={[{ value: 'planned', label: '예정' }, { value: 'in_progress', label: '진행 중' }, { value: 'applied', label: '적용' }]} />
      <Input label="항목명" value={form.name} onChange={(v) => setField('name', v)} placeholder="예: Loudness Normalization" />
      <Input label="설명" value={form.desc} onChange={(v) => setField('desc', v)} textarea placeholder="항목에 대한 설명" />

      <div className="mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2 block">파라미터</span>
        <div className="flex gap-2 mb-3">
          <input value={paramKey} onChange={(e) => setParamKey(e.target.value)} placeholder="Key"
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500" />
          <input value={paramVal} onChange={(e) => setParamVal(e.target.value)} placeholder="Value"
            onKeyDown={(e) => e.key === 'Enter' && addParam()}
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500" />
          <Btn small variant="primary" onClick={addParam}><Plus size={12} /></Btn>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(form.params).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1 bg-slate-100 pl-2.5 pr-1 py-1 rounded-lg border border-slate-200">
              <span className="text-[10px] font-mono text-slate-500">{k}:</span>
              <span className="text-[10px] font-mono font-bold text-indigo-600">{v}</span>
              <button onClick={() => removeParam(k)} className="p-0.5 text-slate-400 hover:text-red-500 ml-1"><X size={10} /></button>
            </div>
          ))}
        </div>
      </div>

      {initial && <Input label="수정 내역 메모" value={form.edit_summary} onChange={(v) => setField('edit_summary', v)} placeholder="변경 사항 기록" />}

      <div className="mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">소스코드</span>
        <textarea
          value={form.source_code || ''}
          onChange={(e) => setField('source_code', e.target.value)}
          placeholder="# 후처리/검증 함수 코드를 입력하세요..."
          className="w-full px-4 py-3 bg-slate-900 text-slate-300 border border-slate-700 rounded-xl text-[11px] font-mono outline-none focus:ring-2 focus:ring-indigo-500 resize-none h-40 leading-relaxed"
        />
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
        <Btn variant="ghost" onClick={onClose}>취소</Btn>
        <Btn variant="accent" onClick={handleSave} disabled={!form.name || saving}>
          <Save size={14} /> {initial ? '저장' : '추가'}
        </Btn>
      </div>
    </Modal>
  );
}

// ── Main Library Page ───────────────────────────────────────────

export default function LibraryPage() {
  const { canEditTech } = useAuth();
  const [items, setItems] = useState([]);
  const [filterType, setFilterType] = useState('all');
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [codeViewItem, setCodeViewItem] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = () => techItemApi.list().then(setItems);
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (filterType === 'all') return items;
    return items.filter((i) => i.type === filterType);
  }, [items, filterType]);

  const filters = [
    { k: 'all', l: '전체', c: '#1e293b' },
    { k: 'processing', l: '후처리', c: '#059669' },
    { k: 'validation', l: '검증', c: '#7c3aed' },
  ];

  return (
    <div className="p-8 lg:p-10">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">후처리 및 검증 항목 라이브러리</h2>
          <p className="text-sm text-slate-400 mt-1">공통 및 특화 기술 항목을 관리합니다.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-white p-1 rounded-xl border border-slate-200 shadow-sm">
            {filters.map((f) => (
              <button key={f.k} onClick={() => setFilterType(f.k)}
                className="px-4 py-2 text-[11px] font-bold rounded-lg transition-all"
                style={filterType === f.k ? { background: f.c, color: 'white' } : { color: '#64748b' }}>
                {f.l}
              </button>
            ))}
          </div>
          {canEditTech && (
            <Btn variant="accent" onClick={() => { setEditTarget(null); setFormOpen(true); }}>
              <Plus size={15} /> 항목 추가
            </Btn>
          )}
        </div>
      </div>

      <Card>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-100 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
              <th className="px-5 py-4 w-20">분류</th>
              <th className="px-5 py-4">항목명</th>
              <th className="px-5 py-4">설명</th>
              <th className="px-5 py-4">파라미터</th>
              <th className="px-5 py-4 text-center">범위</th>
              <th className="px-5 py-4 text-center">태그</th>
              <th className="px-5 py-4 text-right w-24">관리</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100/80">
            {filtered.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-5 py-5">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                    item.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                  }`}>
                    {item.type === 'processing' ? '후처리' : '검증'}
                  </span>
                </td>
                <td className="px-5 py-5 text-sm font-bold text-slate-800">{item.name}</td>
                <td className="px-5 py-5 text-xs text-slate-500 max-w-[200px]">{item.desc}</td>
                <td className="px-5 py-5">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(item.params || {}).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        <span className="text-[9px] font-mono text-slate-400 uppercase">{k}</span>
                        <span className="text-[9px] font-mono font-bold text-indigo-600">{v}</span>
                      </div>
                    ))}
                  </div>
                </td>
                <td className="px-5 py-5 text-center">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                    item.scope === 'common' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-amber-50 text-amber-600 border-amber-100'
                  }`}>
                    {item.scope}
                  </span>
                </td>
                <td className="px-5 py-5 text-center"><Pill type={item.tag} kind="tag" /></td>
                <td className="px-5 py-5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => setCodeViewItem(item)}
                      className="p-1.5 text-slate-300 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors" title="코드 보기">
                      <Code2 size={15} />
                    </button>
                    {canEditTech && (
                      <button onClick={() => { setEditTarget(item); setFormOpen(true); }}
                        className="p-1.5 text-slate-300 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors" title="수정">
                        <Edit3 size={15} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-6 flex items-center gap-3 p-4 bg-blue-50 border border-blue-100 rounded-2xl">
        <div className="p-2 bg-blue-600 text-white rounded-lg shadow-md shadow-blue-200"><Info size={14} /></div>
        <p className="text-xs text-blue-800 font-medium">
          라이브러리 항목은 <span className="font-black underline">'매핑 매트릭스'</span>에서 방송사 정책과 연결하여 실제 검증 엔진에 적용할 수 있습니다.
        </p>
      </div>

      <TechItemFormModal open={formOpen} onClose={() => { setFormOpen(false); setEditTarget(null); }} initial={editTarget} onSaved={load} />

      {/* Code Viewer Modal */}
      <Modal open={!!codeViewItem} onClose={() => { setCodeViewItem(null); setCopied(false); }} title={`${codeViewItem?.name || ''} — 소스코드`} wide>
        {codeViewItem && (
          <>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                  codeViewItem.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                }`}>
                  {codeViewItem.type === 'processing' ? '후처리' : '검증'}
                </span>
                <span className="text-xs text-slate-500">{codeViewItem.desc}</span>
              </div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(codeViewItem.source_code || '');
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-slate-700 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors"
              >
                {copied ? <CheckIcon size={12} /> : <Copy size={12} />}
                {copied ? '복사됨' : '복사'}
              </button>
            </div>
            {codeViewItem.source_code ? (
              <div className="bg-slate-900 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 bg-slate-800/80 border-b border-slate-700">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Python</span>
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
                  </div>
                </div>
                <pre className="p-5 overflow-x-auto text-[12px] leading-relaxed">
                  <code className="text-slate-300 font-mono whitespace-pre">{codeViewItem.source_code}</code>
                </pre>
              </div>
            ) : (
              <div className="bg-slate-50 rounded-xl p-10 text-center">
                <Code2 size={40} className="text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-400">등록된 소스코드가 없습니다.</p>
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}
