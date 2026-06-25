import { useState, useEffect, useMemo } from 'react';
import { Link2, FileText, Code2, Pencil, Info, Wand2, ShieldCheck, ArrowLeftRight, ChevronRight, Check, ArrowRight, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { policyApi, techItemApi, linkApi } from '../api/client';
import { Btn } from '../components/ui';
import { getGuide } from '../data/functionGuide';

// 예시 문자열의 \n(역슬래시 몇 개든) → 실제 줄바꿈
const nl = (s) => (s == null ? '' : String(s).replace(/\\+n/g, '\n'));

export default function MappingPage() {
  const { canEditTech } = useAuth();
  const [categories, setCategories] = useState([]);
  const [techItems, setTechItems] = useState([]);
  const [links, setLinks] = useState([]);
  const [mode, setMode] = useState('policy'); // 'policy' | 'tech'
  const [selectedId, setSelectedId] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const [cats, tis, lks] = await Promise.all([policyApi.matrix(), techItemApi.list(), linkApi.all()]);
    setCategories(cats); setTechItems(tis); setLinks(lks); setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const policyItems = useMemo(() => categories.flatMap((c) => c.items.map((i) => ({ ...i, _cat: c.name }))), [categories]);
  const techById = useMemo(() => Object.fromEntries(techItems.map((t) => [t.id, t])), [techItems]);
  const policyItemById = useMemo(() => Object.fromEntries(policyItems.map((p) => [p.id, p])), [policyItems]);
  const linkMap = useMemo(() => {
    const m = {}; links.forEach((l) => { m[`${l.policy_item_id}|${l.tech_item_id}`] = l.id; }); return m;
  }, [links]);

  const techIdsForPolicy = (pid) => links.filter((l) => l.policy_item_id === pid).map((l) => l.tech_item_id);
  const policyIdsForTech = (tid) => links.filter((l) => l.tech_item_id === tid).map((l) => l.policy_item_id);
  const countTech = (pid) => links.filter((l) => l.policy_item_id === pid).length;
  const countPolicy = (tid) => links.filter((l) => l.tech_item_id === tid).length;

  const toggleLink = async (pid, tid) => {
    const existing = linkMap[`${pid}|${tid}`];
    if (existing) await linkApi.remove(existing);
    else await linkApi.create({ policy_item_id: pid, tech_item_id: tid, note: '' });
    setLinks(await linkApi.all());
  };

  const switchMode = (m) => { setMode(m); setSelectedId(null); };

  // ── 왼쪽 목록 행 ──
  const MasterRow = ({ id, title, sub, count, accent }) => {
    const sel = selectedId === id;
    return (
      <button onClick={() => setSelectedId(sel ? null : id)}
        className={`group w-full flex items-center gap-2 text-left pl-3 pr-2.5 py-2 border-l-2 border-b border-b-slate-100 last:border-b-0 transition-colors ${
          sel ? `${accent.bar} ${accent.bg}` : 'border-l-transparent hover:bg-slate-50'
        }`}>
        <div className="min-w-0 flex-1">
          <span className="text-[13px] text-slate-700 truncate block">{title}</span>
          {sub && <span className="text-[10px] text-indigo-400/80 font-mono truncate block">{sub}</span>}
        </div>
        {count > 0 && <span className="flex items-center gap-0.5 text-[10px] font-bold text-slate-300 group-hover:text-slate-400 shrink-0"><Link2 size={10} /> {count}</span>}
        <ChevronRight size={13} className={`shrink-0 ${sel ? 'text-slate-400' : 'text-slate-200 group-hover:text-slate-300'}`} />
      </button>
    );
  };

  const renderMaster = () => {
    if (mode === 'policy') {
      const accent = { bar: 'border-l-blue-500', bg: 'bg-blue-50/70' };
      return categories.map((cat) => (
        <div key={cat.id} className="mb-1">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 py-1">{cat.name}</p>
          {cat.items.map((item) => <MasterRow key={item.id} id={item.id} title={item.name} count={countTech(item.id)} accent={accent} />)}
        </div>
      ));
    }
    const accent = { bar: 'border-l-purple-500', bg: 'bg-purple-50/70' };
    const proc = techItems.filter((t) => t.type === 'processing');
    const valid = techItems.filter((t) => t.type === 'validation');
    const block = (kind, items) => {
      const isProc = kind === 'processing';
      const Icon = isProc ? Wand2 : ShieldCheck;
      return (
        <div className="mb-1">
          <div className="flex items-center gap-1.5 px-3 py-1">
            <Icon size={11} className={isProc ? 'text-emerald-600' : 'text-purple-600'} />
            <span className={`text-[10px] font-bold uppercase tracking-wide ${isProc ? 'text-emerald-700' : 'text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
            <span className="text-[10px] font-bold text-slate-300">{items.length}</span>
          </div>
          {items.map((t) => <MasterRow key={t.id} id={t.id} title={t.name} sub={t.function_name ? `${t.function_name}()` : ''} count={countPolicy(t.id)} accent={accent} />)}
        </div>
      );
    };
    return <>{block('processing', proc)}{block('validation', valid)}</>;
  };

  // ── 오른쪽 디테일 ──
  const renderDetail = () => {
    if (!selectedId) {
      return (
        <div className="h-full flex flex-col items-center justify-center text-slate-300 py-16">
          <ArrowLeftRight size={20} className="mb-2" />
          <p className="text-[13px]">왼쪽에서 {mode === 'policy' ? '정책' : '기술'} 항목을 선택하세요</p>
          <p className="text-[11px] text-slate-300 mt-0.5">연결된 항목과 동작 설명이 여기에 표시됩니다</p>
        </div>
      );
    }

    // ── 정책 선택 ──
    if (mode === 'policy') {
      const p = policyItemById[selectedId]; if (!p) return null;
      const connSet = new Set(techIdsForPolicy(selectedId));
      const pool = editMode ? techItems : techItems.filter((t) => connSet.has(t.id));
      const proc = pool.filter((t) => t.type === 'processing');
      const valid = pool.filter((t) => t.type === 'validation');
      return (
        <>
          <DetailHeader kindLabel="정책 항목" kindCls="bg-blue-50 text-blue-600" title={p.name} desc={p.description} />
          <div className="px-4 py-4 space-y-5">
            {!editMode && (
              <p className="text-[12px] text-slate-500 -mt-1">이 정책은 아래 후처리·검증 함수로 처리·검사됩니다.</p>
            )}
            <ConnGroup kind="processing" items={proc} connSet={connSet} editMode={editMode} onToggle={(t) => toggleLink(p.id, t.id)} />
            <ConnGroup kind="validation" items={valid} connSet={connSet} editMode={editMode} onToggle={(t) => toggleLink(p.id, t.id)} />
          </div>
        </>
      );
    }

    // ── 기술 선택 ──
    const t = techById[selectedId]; if (!t) return null;
    const connSet = new Set(policyIdsForTech(selectedId));
    const pool = editMode ? policyItems : policyItems.filter((p) => connSet.has(p.id));
    const byCat = {};
    pool.forEach((p) => { (byCat[p._cat] = byCat[p._cat] || []).push(p); });
    return (
      <>
        <DetailHeader kindLabel="기술 항목" kindCls="bg-purple-50 text-purple-600" title={t.name} sub={t.function_name ? `${t.function_name}()` : ''} />
        <div className="px-4 py-4 space-y-5">
          <FunctionExplain item={t} open />
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-2">
              {editMode ? '이 함수를 적용할 정책 선택' : '이 함수가 적용되는 정책'}
            </p>
            {Object.keys(byCat).length === 0 ? (
              <p className="text-xs text-slate-400">연결된 정책 항목이 없습니다.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(byCat).map(([cat, items]) => (
                  <div key={cat}>
                    <p className="text-[10px] font-bold text-slate-400 mb-1">{cat}</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
                      {items.map((p) => (
                        <ToggleRow key={p.id} label={p.name} on={connSet.has(p.id)} editMode={editMode} onToggle={() => toggleLink(p.id, t.id)} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="p-6 lg:p-8">
      <div className="flex justify-between items-end mb-5 gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-800">정책 ↔ 기술 연결 찾기</h2>
          <p className="text-[13px] text-slate-400 mt-0.5">항목을 고르면 연결된 함수가 무엇을 어떻게 하는지 예시와 함께 보여줍니다.</p>
        </div>
        {canEditTech && (
          <Btn variant={editMode ? 'accent' : 'primary'} onClick={() => setEditMode((v) => !v)}>
            <Pencil size={14} /> {editMode ? '편집 종료' : '연결 편집'}
          </Btn>
        )}
      </div>

      {/* 방향 토글 */}
      <div className="inline-flex items-center p-0.5 bg-slate-100 rounded-lg mb-4">
        <button onClick={() => switchMode('policy')}
          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-bold transition-all ${mode === 'policy' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
          <FileText size={12} /> 정책 기준
        </button>
        <ArrowLeftRight size={12} className="text-slate-300 mx-1" />
        <button onClick={() => switchMode('tech')}
          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-bold transition-all ${mode === 'tech' ? 'bg-white text-purple-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
          <Code2 size={12} /> 기술 기준
        </button>
      </div>

      {editMode && (
        <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-indigo-50/70 border border-indigo-100 rounded-lg">
          <Info size={13} className="text-indigo-500 shrink-0" />
          <p className="text-[11px] text-indigo-700 font-medium">
            {selectedId ? '오른쪽 항목의 체크박스를 눌러 연결/해제하세요. (전체 후보가 보입니다)' : `왼쪽에서 ${mode === 'policy' ? '정책' : '기술'} 항목을 먼저 선택하세요.`}
          </p>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-400 py-12 text-center">불러오는 중...</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(260px,320px)_1fr] gap-4 items-start">
          <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden">
            <div className="px-3 py-2 border-b border-slate-100 flex items-center gap-1.5">
              {mode === 'policy' ? <FileText size={13} className="text-blue-500" /> : <Code2 size={13} className="text-purple-500" />}
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">{mode === 'policy' ? '정책 항목' : '후처리 · 검증 항목'}</span>
            </div>
            <div className="max-h-[68vh] overflow-y-auto py-1">{renderMaster()}</div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/70 overflow-hidden min-h-[50vh]">
            {renderDetail()}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 디테일 헤더 ──
function DetailHeader({ kindLabel, kindCls, title, sub, desc }) {
  return (
    <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/40">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${kindCls}`}>{kindLabel}</span>
        <h4 className="text-sm font-bold text-slate-800">{title}</h4>
        {sub && <span className="text-[11px] text-slate-400 font-mono">{sub}</span>}
      </div>
      {desc && <p className="text-[11px] text-slate-400 mt-1">{desc}</p>}
    </div>
  );
}

// ── 정책 선택 시: 연결된 후처리/검증 그룹 (각 함수 설명+예시) ──
function ConnGroup({ kind, items, connSet, editMode, onToggle }) {
  const isProc = kind === 'processing';
  const Icon = isProc ? Wand2 : ShieldCheck;
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={12} className={isProc ? 'text-emerald-600' : 'text-purple-600'} />
        <span className={`text-[11px] font-bold uppercase tracking-wide ${isProc ? 'text-emerald-700' : 'text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
        <span className="text-[10px] font-bold text-slate-300">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <p className="text-[11px] text-slate-300 pl-1">연결된 {isProc ? '후처리' : '검증'} 없음</p>
      ) : editMode ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
          {items.map((t) => (
            <ToggleRow key={t.id} label={t.name} sub={t.function_name ? `${t.function_name}()` : ''}
              on={connSet.has(t.id)} editMode onToggle={() => onToggle(t)} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((t) => <FunctionExplain key={t.id} item={t} />)}
        </div>
      )}
    </div>
  );
}

// ── 함수 설명 + 케이스 예시 카드 ──
function FunctionExplain({ item, open = false }) {
  const guide = getGuide(item);
  const isProc = item.type === 'processing';
  const summary = guide?.summary || item.desc || '설명이 등록되지 않았습니다.';
  const cases = guide?.cases || [];

  return (
    <div className="rounded-lg border border-slate-200/70 overflow-hidden">
      <div className={`flex items-center gap-2 px-3 py-2 ${isProc ? 'bg-emerald-50/50' : 'bg-purple-50/50'}`}>
        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${isProc ? 'bg-emerald-100 text-emerald-700' : 'bg-purple-100 text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
        <span className="text-[13px] font-bold text-slate-800">{item.name}</span>
        {item.function_name && <span className="text-[10px] text-indigo-400/80 font-mono">{item.function_name}()</span>}
      </div>
      <div className="px-3 py-2.5">
        <p className="text-[12px] text-slate-600 leading-relaxed">{summary}</p>
        {cases.length > 0 && (
          <div className="mt-2.5 space-y-1.5">
            {cases.map((c, i) => isProc
              ? <ProcCase key={i} c={c} />
              : <ValidCase key={i} c={c} />)}
          </div>
        )}
      </div>
    </div>
  );
}

// 후처리 예시: before → after
function ProcCase({ c }) {
  return (
    <div className="flex items-stretch gap-2 text-[11px]">
      {c.label && <span className="shrink-0 w-16 pt-1 text-[10px] font-bold text-slate-400">{c.label}</span>}
      <div className="flex-1 grid grid-cols-[1fr_auto_1fr] gap-1.5 items-center min-w-0">
        <div className="px-2 py-1 bg-slate-50 rounded border border-slate-150 font-mono text-slate-400 line-through whitespace-pre-wrap break-words">{nl(c.before)}</div>
        <ArrowRight size={12} className="text-emerald-500 shrink-0" />
        <div className="px-2 py-1 bg-emerald-50/60 rounded border border-emerald-100 font-mono text-slate-700 whitespace-pre-wrap break-words">{nl(c.after)}</div>
      </div>
    </div>
  );
}

// 검증 예시: input + 통과/재작업
function ValidCase({ c }) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      {c.label && <span className="shrink-0 w-16 text-[10px] font-bold text-slate-400">{c.label}</span>}
      <div className="flex-1 px-2 py-1 bg-slate-50 rounded border border-slate-150 font-mono text-slate-600 whitespace-pre-wrap break-words min-w-0">{nl(c.input)}</div>
      {c.fail
        ? <span className="shrink-0 inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700"><X size={10} /> 재작업</span>
        : <span className="shrink-0 inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700"><Check size={10} /> 통과</span>}
    </div>
  );
}

// ── 편집 모드 체크 토글 행 ──
function ToggleRow({ label, sub, on, editMode, onToggle }) {
  if (editMode) {
    return (
      <button onClick={onToggle}
        className={`w-full flex items-center gap-2 text-left px-2 py-1.5 rounded transition-colors ${on ? 'bg-indigo-50/70' : 'hover:bg-slate-50'}`}>
        <span className={`w-4 h-4 rounded flex items-center justify-center shrink-0 border ${on ? 'bg-indigo-600 border-indigo-600' : 'border-slate-300'}`}>
          {on && <Check size={11} className="text-white" />}
        </span>
        <span className="min-w-0">
          <span className={`text-[12px] truncate block ${on ? 'text-slate-700 font-medium' : 'text-slate-500'}`}>{label}</span>
          {sub && <span className="text-[10px] text-indigo-400/80 font-mono truncate block">{sub}</span>}
        </span>
      </button>
    );
  }
  return (
    <div className="flex items-center gap-2 px-2 py-1.5">
      <span className="w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
      <span className="min-w-0">
        <span className="text-[12px] text-slate-700 truncate block">{label}</span>
        {sub && <span className="text-[10px] text-indigo-400/80 font-mono truncate block">{sub}</span>}
      </span>
    </div>
  );
}