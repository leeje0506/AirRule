import { useState, useEffect, useMemo } from 'react';
import { Plus, Edit3, Save, X, Code2, Copy, Check as CheckIcon, Search, Wand2, ShieldCheck, LayoutGrid, Building2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { techItemApi, broadcasterApi } from '../api/client';
import { Btn, Modal, Input, Select } from '../components/ui';

const FUNC_TYPE_OPTIONS = [
  { value: 'content_only', label: 'content_only (문장)' },
  { value: 'content_with_params', label: 'content_with_params' },
  { value: 'content_with_validation_params', label: 'content_with_validation_params' },
  { value: 'timing', label: 'timing (싱크)' },
  { value: 'multi_subtitle', label: 'multi_subtitle (자막 리스트)' },
  { value: 'pair_validation', label: 'pair_validation (앞뒤 쌍)' },
  { value: 'multi_validation', label: 'multi_validation' },
];

const BC_ORDER = ['JTBC', 'LGHV', 'SKBB', 'TVCS', 'DLIV', 'TVNG'];
const BC_PREFIX = { JTBC: 'jtbc', LGHV: 'lghv', SKBB: 'skbb', TVCS: 'tvcs', DLIV: 'dliv', TVNG: 'tvng' };

function sortBroadcasters(list) {
  return [...list].sort((a, b) => {
    const ia = BC_ORDER.indexOf(a.code), ib = BC_ORDER.indexOf(b.code);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

const pureName = (name) => (name || '').replace(/^\s*\[[^\]]*\]\s*/, '').trim();

// ── 함수 고정 번호 (공통C/전용S/납품F × 후처리P/검증V) ──
const groupCode = (it) => (it.stage === 'final' ? 'F' : it.scope === 'common' ? 'C' : 'S');
const typeCode = (it) => (it.type === 'processing' ? 'P' : 'V');

function buildNumbering(items) {
  const buckets = {};
  [...items].sort((a, b) => a._idx - b._idx).forEach((it) => {
    if (!it.function_name) return;
    const key = groupCode(it) + typeCode(it);
    if (!buckets[key]) buckets[key] = new Map();
    const m = buckets[key];
    if (!m.has(it.function_name)) m.set(it.function_name, m.size + 1);
  });
  return buckets;
}

function makeCodeOf(buckets) {
  return (it) => {
    if (!it.function_name) return null;
    const key = groupCode(it) + typeCode(it);
    const n = buckets[key]?.get(it.function_name);
    return n ? `${key}-${String(n).padStart(2, '0')}` : null;
  };
}

function CodeBadge({ code }) {
  if (!code) return null;
  return (
    <span className="inline-flex items-center text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-slate-700 text-white tracking-wide shrink-0">
      {code}
    </span>
  );
}

// ── Tech Item Form Modal ────────────────────────────────────────

function TechItemFormModal({ open, onClose, initial, onSaved }) {
  const [form, setForm] = useState({
    type: 'processing', name: '', function_name: '', func_type: 'content_only', stage: 'stage1',
    desc: '', params: {}, scope: 'common', tag: 'planned', source_code: '', edit_summary: '',
  });
  const [paramKey, setParamKey] = useState('');
  const [paramVal, setParamVal] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(initial
        ? { ...initial, edit_summary: '' }
        : { type: 'processing', name: '', function_name: '', func_type: 'content_only', stage: 'stage1', desc: '', params: {}, scope: 'common', tag: 'planned', source_code: '', edit_summary: '' });
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
      if (initial) await techItemApi.update(initial.id, form);
      else await techItemApi.create(form);
      onSaved();
      onClose();
    } catch (err) {
      alert(err?.response?.data?.detail || '저장 실패');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={initial ? '항목 수정' : '항목 추가'} wide>
      <div className="grid grid-cols-2 gap-4">
        <Select label="분류" value={form.type} onChange={(v) => setField('type', v)}
          options={[{ value: 'processing', label: '후처리' }, { value: 'validation', label: '검증' }]} />
        <Select label="범위" value={form.scope} onChange={(v) => setField('scope', v)}
          options={[{ value: 'common', label: 'Common' }, { value: 'specific', label: 'Specific' }]} />
        <Select label="스테이지" value={form.stage} onChange={(v) => setField('stage', v)}
          options={[{ value: 'stage1', label: 'stage1 (1차)' }, { value: 'stage2', label: 'stage2 (2차)' }, { value: 'final', label: 'final (최종 납품)' }]} />
        <Select label="태그" value={form.tag} onChange={(v) => setField('tag', v)}
          options={[{ value: 'planned', label: '예정' }, { value: 'in_progress', label: '진행 중' }, { value: 'applied', label: '적용' }]} />
      </div>

      <Input label="항목명 (표시 이름)" value={form.name} onChange={(v) => setField('name', v)} placeholder="예: [JTBC] 18자 줄바꿈" />
      <Input label="함수명 (실제 함수)" value={form.function_name} onChange={(v) => setField('function_name', v)} mono placeholder="예: postprocess_over_length_lines" />
      <Select label="함수 타입" value={form.func_type} onChange={(v) => setField('func_type', v)} options={FUNC_TYPE_OPTIONS} />
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
              <span className="text-[10px] font-mono font-bold text-indigo-600">{String(v)}</span>
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

// ── Param chips ─────────────────────────────────────────────────

function ParamChips({ params }) {
  if (!params || Object.keys(params).length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {Object.entries(params).map(([k, v]) => (
        <span key={k} className="inline-flex items-center gap-1 bg-slate-100 px-1.5 py-0.5 rounded">
          <span className="text-[9px] font-mono text-slate-400">{k}</span>
          <span className="text-[9px] font-mono font-bold text-indigo-600">{String(v)}</span>
        </span>
      ))}
    </div>
  );
}

// ── (탭1) 함수 한 줄 ─────────────────────────────────────────────

function ItemRow({ item, code, canEdit, onView, onEdit }) {
  const hasParams = item.params && Object.keys(item.params).length > 0;
  return (
    <div className="group flex items-start gap-3 px-3 py-2 border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70 transition-colors">
      <CodeBadge code={code} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-[13px] font-medium text-slate-800">{pureName(item.name)}</span>
          {item.function_name && <span className="text-[11px] text-indigo-400 font-mono">{item.function_name}()</span>}
        </div>
        {item.desc && <p className="text-[11px] text-slate-400 truncate" title={item.desc}>{item.desc}</p>}
        {hasParams && <ParamChips params={item.params} />}
      </div>
      <div className="flex items-center gap-0.5 shrink-0">
        <button onClick={() => onView(item)} className="p-1.5 text-slate-300 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors" title="코드 보기"><Code2 size={14} /></button>
        {canEdit && <button onClick={() => onEdit(item)} className="p-1.5 text-slate-300 hover:text-indigo-600 rounded hover:bg-indigo-50 transition-colors" title="수정"><Edit3 size={14} /></button>}
      </div>
    </div>
  );
}

function TypeBlock({ kind, items, codeOf, canEdit, onView, onEdit }) {
  const isProc = kind === 'processing';
  const Icon = isProc ? Wand2 : ShieldCheck;
  return (
    <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden">
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-100">
        <Icon size={12} className={isProc ? 'text-emerald-600' : 'text-purple-600'} />
        <span className={`text-[11px] font-bold uppercase tracking-wide ${isProc ? 'text-emerald-700' : 'text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
        <span className="text-[10px] font-bold text-slate-300">{items.length}</span>
      </div>
      <div className="max-h-[58vh] overflow-y-auto">
        {items.length === 0 ? <p className="text-xs text-slate-300 text-center py-6">항목 없음</p>
          : items.map((item) => <ItemRow key={item.id} item={item} code={codeOf(item)} canEdit={canEdit} onView={onView} onEdit={onEdit} />)}
      </div>
    </div>
  );
}

function StageSection({ label, sub, dot, proc, valid, codeOf, canEdit, onView, onEdit, hideValidation }) {
  return (
    <div className="mb-6">
      <div className="flex items-baseline gap-2 mb-2">
        <span className="w-2 h-2 rounded-full shrink-0 translate-y-[-1px]" style={{ background: dot }} />
        <h3 className="text-[13px] font-bold text-slate-700">{label}</h3>
        <p className="text-[11px] text-slate-400">{sub}</p>
      </div>
      <div className={`grid grid-cols-1 gap-3 ${hideValidation ? '' : 'lg:grid-cols-2'}`}>
        <TypeBlock kind="processing" items={proc} codeOf={codeOf} canEdit={canEdit} onView={onView} onEdit={onEdit} />
        {!hideValidation && <TypeBlock kind="validation" items={valid} codeOf={codeOf} canEdit={canEdit} onView={onView} onEdit={onEdit} />}
      </div>
    </div>
  );
}

function FunctionsView({ items, codeOf, canEdit, onView, onEdit }) {
  const group = (stage, type) => {
    const rows = items.filter((i) => i.stage === stage && i.type === type).sort((a, b) => (a._idx ?? 0) - (b._idx ?? 0));
    const seen = new Set();
    const uniq = [];
    for (const r of rows) {
      const key = r.function_name || r.id;
      if (seen.has(key)) continue;
      seen.add(key); uniq.push(r);
    }
    return uniq.sort((a, b) => (a.scope !== b.scope ? (a.scope === 'common' ? -1 : 1) : (a.name || '').localeCompare(b.name || '')));
  };
  return (
    <>
      <StageSection label="1차 (Stage 1)" sub="모든 방송사 공통 — 정규화·기본 검증" dot="#2563eb"
        proc={group('stage1', 'processing')} valid={group('stage1', 'validation')} codeOf={codeOf} canEdit={canEdit} onView={onView} onEdit={onEdit} />
      <StageSection label="2차 (Stage 2)" sub="공통 + 방송사별 — 줄바꿈·오버랩·마침표 등" dot="#4f46e5"
        proc={group('stage2', 'processing')} valid={group('stage2', 'validation')} codeOf={codeOf} canEdit={canEdit} onView={onView} onEdit={onEdit} />
      <StageSection label="3차 (최종 납품)" sub="납품 직전 처리 — 배너 삽입·마침표 삭제 (방송사별)" dot="#0f766e"
        proc={group('final', 'processing')} valid={[]} hideValidation codeOf={codeOf} canEdit={canEdit} onView={onView} onEdit={onEdit} />
    </>
  );
}

// ── (탭2) 방송사별 파이프라인 ────────────────────────────────────

function PipelineRow({ item, code, bcName, onView }) {
  const displayName = item.scope === 'common' ? pureName(item.name) : `[${bcName}] ${pureName(item.name)}`;
  const hasParams = item.params && Object.keys(item.params).length > 0;
  return (
    <div className="group flex items-start gap-3 px-3 py-2 border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70 transition-colors">
      <CodeBadge code={code} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-[13px] font-medium text-slate-800">{displayName}</span>
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${item.scope === 'common' ? 'bg-slate-100 text-slate-500' : 'bg-amber-50 text-amber-600'}`}>{item.scope === 'common' ? '공통' : '전용'}</span>
          {item.function_name && <span className="text-[11px] text-indigo-400 font-mono">{item.function_name}()</span>}
        </div>
        {hasParams && <ParamChips params={item.params} />}
      </div>
      <button onClick={() => onView(item)} className="p-1.5 text-slate-300 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors shrink-0" title="코드 보기"><Code2 size={14} /></button>
    </div>
  );
}

function PipelineSection({ label, dot, items, codeOf, bcName, onView }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden mb-3">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100">
        <span className="w-2 h-2 rounded-full" style={{ background: dot }} />
        <h4 className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">{label}</h4>
        <span className="text-[10px] font-bold text-slate-300">{items.length}</span>
      </div>
      <div>{items.map((item) => <PipelineRow key={item.id} item={item} code={codeOf(item)} bcName={bcName} onView={onView} />)}</div>
    </div>
  );
}

function BroadcasterView({ items, broadcasters, codeOf, onView }) {
  const [bc, setBc] = useState(null);
  useEffect(() => { if (!bc && broadcasters.length) setBc(broadcasters[0]); }, [broadcasters]);

  const pipe = useMemo(() => {
    if (!bc) return null;
    const low = BC_PREFIX[bc.code];
    const belongs = (it) => it.scope === 'common' || it.id.split('_')[1] === low;
    const mine = items.filter(belongs).slice().sort((a, b) => a._idx - b._idx);
    const sec = (stage, type) => mine.filter((i) => i.stage === stage && i.type === type);
    return {
      s1p: sec('stage1', 'processing'), s1v: sec('stage1', 'validation'),
      s2p: sec('stage2', 'processing'), s2v: sec('stage2', 'validation'),
      fp: sec('final', 'processing'),
    };
  }, [bc, items]);

  return (
    <>
      <div className="flex items-center gap-1.5 flex-wrap mb-4">
        {broadcasters.map((b) => (
          <button key={b.id} onClick={() => setBc(b)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${bc?.id === b.id ? 'text-white' : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'}`}
            style={bc?.id === b.id ? { background: b.color || '#6366f1' } : undefined}>
            {b.name}
          </button>
        ))}
      </div>

      {pipe && (
        <>
          <p className="text-[11px] text-slate-400 mb-3">
            <span className="font-bold text-slate-600">{bc.name}</span> 처리 순서 (config 기준). 코드는 분류별 고정 번호 — 공통(C)·전용(S)·납품(F) × 후처리(P)·검증(V).
          </p>
          <PipelineSection label="1차 후처리" dot="#2563eb" items={pipe.s1p} codeOf={codeOf} bcName={bc.name} onView={onView} />
          <PipelineSection label="1차 검증" dot="#2563eb" items={pipe.s1v} codeOf={codeOf} bcName={bc.name} onView={onView} />
          <PipelineSection label="2차 후처리" dot="#4f46e5" items={pipe.s2p} codeOf={codeOf} bcName={bc.name} onView={onView} />
          <PipelineSection label="2차 검증" dot="#4f46e5" items={pipe.s2v} codeOf={codeOf} bcName={bc.name} onView={onView} />
          <PipelineSection label="최종 납품" dot="#0f766e" items={pipe.fp} codeOf={codeOf} bcName={bc.name} onView={onView} />
        </>
      )}
    </>
  );
}

// ── Main Library Page ───────────────────────────────────────────

export default function LibraryPage() {
  const { canEditTech } = useAuth();
  const [items, setItems] = useState([]);
  const [broadcasters, setBroadcasters] = useState([]);
  const [view, setView] = useState('functions');
  const [query, setQuery] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [codeViewItem, setCodeViewItem] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    const [tis, bs] = await Promise.all([techItemApi.list(), broadcasterApi.list()]);
    setItems(tis.map((t, i) => ({ ...t, _idx: i })));
    setBroadcasters(sortBroadcasters(bs));
  };
  useEffect(() => { load(); }, []);

  const openEdit = (item) => { setEditTarget(item); setFormOpen(true); };
  const codeOf = useMemo(() => makeCodeOf(buildNumbering(items)), [items]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) =>
      (i.name || '').toLowerCase().includes(q) ||
      (i.function_name || '').toLowerCase().includes(q) ||
      (i.desc || '').toLowerCase().includes(q)
    );
  }, [items, query]);

  return (
    <div className="p-6 lg:p-8">
      <div className="flex justify-between items-center mb-4 gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-800">후처리 및 검증 항목 라이브러리</h2>
          <p className="text-[13px] text-slate-400 mt-0.5">함수 목록과 방송사별 처리 순서를 확인합니다. (개발팀)</p>
        </div>
        <div className="flex items-center gap-2">
          {view === 'functions' && (
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="항목·함수명 검색"
                className="w-52 pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          )}
          {canEditTech && (
            <Btn variant="accent" onClick={() => { setEditTarget(null); setFormOpen(true); }}>
              <Plus size={15} /> 항목 추가
            </Btn>
          )}
        </div>
      </div>

      {/* 탭 */}
      <div className="flex items-center gap-1.5 mb-5">
        <button onClick={() => setView('functions')}
          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${view === 'functions' ? 'bg-slate-900 text-white' : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'}`}>
          <LayoutGrid size={12} /> 함수 목록
        </button>
        <button onClick={() => setView('byBroadcaster')}
          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${view === 'byBroadcaster' ? 'bg-slate-900 text-white' : 'bg-white text-slate-500 border border-slate-200 hover:bg-slate-50'}`}>
          <Building2 size={12} /> 방송사별
        </button>
      </div>

      {view === 'functions' ? (
        <FunctionsView items={filtered} codeOf={codeOf} canEdit={canEditTech} onView={setCodeViewItem} onEdit={openEdit} />
      ) : (
        <BroadcasterView items={items} broadcasters={broadcasters} codeOf={codeOf} onView={setCodeViewItem} />
      )}

      <TechItemFormModal open={formOpen} onClose={() => { setFormOpen(false); setEditTarget(null); }} initial={editTarget} onSaved={load} />

      <Modal open={!!codeViewItem} onClose={() => { setCodeViewItem(null); setCopied(false); }} title={`${codeViewItem?.name || ''} — 소스코드`} wide>
        {codeViewItem && (
          <>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2 flex-wrap">
                <CodeBadge code={codeOf(codeViewItem)} />
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                  codeViewItem.type === 'processing' ? 'bg-emerald-50 text-emerald-700' : 'bg-purple-50 text-purple-700'
                }`}>{codeViewItem.type === 'processing' ? '후처리' : '검증'}</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 uppercase">{codeViewItem.stage}</span>
                {codeViewItem.function_name && <span className="text-[11px] font-mono text-indigo-500">{codeViewItem.function_name}()</span>}
                <span className="text-xs text-slate-500">{codeViewItem.desc}</span>
              </div>
              <button
                onClick={() => { navigator.clipboard.writeText(codeViewItem.source_code || ''); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-slate-700 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors">
                {copied ? <CheckIcon size={12} /> : <Copy size={12} />}{copied ? '복사됨' : '복사'}
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