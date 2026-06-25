import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Play, ChevronDown, GripVertical, Code2,
  CheckCircle2, XCircle, AlertTriangle, Loader2, ArrowUp, ArrowDown,
  FileText, Trash2, RotateCcw, Copy, Check, MinusCircle, ArrowRight, Plus, Wand2, ShieldCheck
} from 'lucide-react';
import { broadcasterApi, mappingApi, techItemApi, testApi } from '../api/client';
import { Card, Btn, Pill, Modal } from '../components/ui';

const BC_PREFIX = { JTBC: 'jtbc', LGHV: 'lghv', SKBB: 'skbb', TVCS: 'tvcs', DLIV: 'dliv', TVNG: 'tvng' };

const SAMPLE_SRT = `1
00:00:01,000 --> 00:00:03,500
안녕하세요 여러분 반갑습니다

2
00:00:04,200 --> 00:00:06,800
오늘은 아주 특별한 날이에요 정말로 기대가 많이 됩니다

3
00:00:07,500 --> 00:00:09,000
짧은 자막

4
00:00:10,000 --> 00:00:13,500
이것은 매우 긴 자막입니다 글자수가 초과될 수도 있는 문장입니다
두 번째 줄도 있어요 꽤 길죠
세 번째 줄까지 있으면 오버플로우

5
00:00:14,000 --> 00:00:16,000
[웃음소리]

6
00:00:17,000 --> 00:00:20,000
마지막 자막이에요. 감사합니다!`;

// ── Code Viewer Modal ───────────────────────────────────────────

function CodeViewerModal({ open, onClose, item }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(item?.source_code || '').then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 2000);
    });
  };
  if (!item) return null;
  return (
    <Modal open={open} onClose={onClose} title={`${item.name} — 소스코드`} wide>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
            item.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
          }`}>{item.type === 'processing' ? '후처리' : '검증'}</span>
          {item.function_name && <span className="text-[11px] font-mono text-indigo-500">{item.function_name}()</span>}
          <span className="text-xs text-slate-500">{item.desc}</span>
        </div>
        <Btn small variant="ghost" onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />}{copied ? '복사됨' : '복사'}
        </Btn>
      </div>
      {item.source_code ? (
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
            <code className="text-slate-300 font-mono whitespace-pre">{item.source_code}</code>
          </pre>
        </div>
      ) : (
        <div className="bg-slate-50 rounded-xl p-10 text-center">
          <Code2 size={40} className="text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-400">등록된 소스코드가 없습니다.</p>
        </div>
      )}
    </Modal>
  );
}

// ── Error / Change rows ─────────────────────────────────────────

function ErrorRow({ error }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-xl border bg-red-50/50 border-red-100">
      <XCircle size={14} className="text-red-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700 uppercase">재작업</span>
          <span className="text-[10px] font-mono text-slate-400">#{error.index}</span>
          {error.timecode && <span className="text-[10px] font-mono text-slate-400">{error.timecode}</span>}
          {error.type && <span className="text-[10px] font-bold text-slate-500">{error.type}</span>}
        </div>
        <p className="text-xs text-slate-700 font-medium">{error.message}</p>
        {error.text && (
          <div className="mt-1.5 px-3 py-2 bg-white rounded-lg border border-slate-200 font-mono text-[11px] text-slate-600 whitespace-pre-wrap">{error.text}</div>
        )}
        {error.char_count != null && (
          <div className="mt-1 flex items-center gap-3 text-[10px] text-slate-400">
            <span>글자 수: <b className="text-red-600">{error.char_count}</b></span>
            <span>제한: <b className="text-slate-600">{error.limit}</b></span>
          </div>
        )}
      </div>
    </div>
  );
}

function ChangeRow({ change }) {
  return (
    <div className="px-4 py-3 rounded-xl border bg-emerald-50/40 border-emerald-100">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] font-mono text-slate-400">#{change.index}</span>
        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 uppercase">변경됨</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-2 items-center">
        <div className="px-3 py-2 bg-white rounded-lg border border-slate-200 font-mono text-[11px] text-slate-400 line-through whitespace-pre-wrap">{change.before}</div>
        <ArrowRight size={14} className="text-emerald-500 mx-auto hidden md:block" />
        <div className="px-3 py-2 bg-white rounded-lg border border-emerald-200 font-mono text-[11px] text-slate-700 whitespace-pre-wrap">{change.after}</div>
      </div>
    </div>
  );
}

// ── Step Result Card ────────────────────────────────────────────

function StepResultCard({ step, onViewCode }) {
  const [expanded, setExpanded] = useState(step.status === 'fail');
  const result = step.result || {};
  const errors = result.errors || [];
  const changes = result.changes || [];
  const isProc = step.item_type === 'processing';

  const headBg = step.status === 'fail' ? 'bg-red-50/30'
    : step.status === 'error' ? 'bg-amber-50/30'
    : step.status === 'skip' ? 'bg-slate-50/50'
    : 'bg-emerald-50/20';

  return (
    <Card className="overflow-hidden">
      <div onClick={() => setExpanded(!expanded)} className={`flex items-center gap-4 px-5 py-4 cursor-pointer transition-colors ${headBg}`}>
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-black shrink-0 ${
          step.status === 'fail' ? 'bg-red-100 text-red-700'
          : step.status === 'error' ? 'bg-amber-100 text-amber-700'
          : step.status === 'skip' ? 'bg-slate-200 text-slate-500'
          : 'bg-emerald-100 text-emerald-700'}`}>
          {step.step}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-slate-800">{step.item_name}</span>
            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${
              isProc ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
            }`}>{isProc ? '후처리' : '검증'}</span>
          </div>
          {result.info && <p className="text-[11px] text-slate-400 mt-0.5">{result.info}</p>}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button onClick={(e) => { e.stopPropagation(); onViewCode(step.item_id); }}
            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="코드 보기">
            <Code2 size={15} />
          </button>
          {!isProc && result.error_count > 0 && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-200">재작업 {result.error_count}건</span>
          )}
          {isProc && changes.length > 0 && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">{changes.length}건 변경</span>
          )}
          {step.status === 'pass' && <CheckCircle2 size={20} className="text-emerald-500" />}
          {step.status === 'fail' && <XCircle size={20} className="text-red-500" />}
          {step.status === 'error' && <AlertTriangle size={20} className="text-amber-500" />}
          {step.status === 'skip' && <MinusCircle size={20} className="text-slate-300" />}
          <ChevronDown size={16} className={`text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100">
          {step.params_used && Object.keys(step.params_used).length > 0 && (
            <div className="px-5 py-3 bg-slate-50/50 border-b border-slate-100">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">적용 파라미터</span>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {Object.entries(step.params_used).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-1 bg-white px-2 py-0.5 rounded border border-slate-200">
                    <span className="text-[9px] font-mono text-slate-400">{k}:</span>
                    <span className="text-[9px] font-mono font-bold text-indigo-600">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="px-5 py-4">
            {step.status === 'skip' ? (
              <div className="flex items-center gap-2 py-2 text-slate-400 text-xs font-medium"><MinusCircle size={14} /> {result.info || '건너뜀'}</div>
            ) : isProc ? (
              changes.length > 0
                ? <div className="space-y-2">{changes.map((c, i) => <ChangeRow key={i} change={c} />)}</div>
                : <div className="flex items-center gap-2 py-2 text-slate-400 text-xs font-medium"><CheckCircle2 size={14} className="text-emerald-500" /> 변경된 자막이 없습니다.</div>
            ) : (
              errors.length > 0
                ? <div className="space-y-2">{errors.map((err, i) => <ErrorRow key={i} error={err} />)}</div>
                : <div className="flex items-center gap-2 py-2 text-emerald-600 text-xs font-medium"><CheckCircle2 size={14} /> 통과 — 재작업 대상 없음.</div>
            )}
          </div>
          <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex items-center gap-4 text-[10px] text-slate-500">
            <span>총 엔트리: <b className="text-slate-700">{result.total_entries}</b></span>
            {isProc
              ? <span>변경: <b className="text-emerald-600">{changes.length}</b></span>
              : <span>재작업: <b className={result.error_count > 0 ? 'text-red-600' : 'text-emerald-600'}>{result.error_count}</b></span>}
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Available item row ──────────────────────────────────────────

function AvailableRow({ item, added, onAdd, onViewCode }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-150 bg-white hover:border-indigo-200 transition-colors">
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-bold text-slate-700 truncate">{item.name}</p>
        {item.function_name && <p className="text-[10px] text-indigo-400 font-mono truncate">{item.function_name}()</p>}
      </div>
      <button onClick={() => onViewCode(item)} className="p-1 text-slate-300 hover:text-slate-600 rounded shrink-0" title="코드 보기"><Code2 size={13} /></button>
      <button onClick={() => onAdd(item.id)} disabled={added}
        className={`text-[10px] font-bold px-2 py-1 rounded-lg shrink-0 transition-colors ${added ? 'text-slate-300 bg-slate-50 cursor-default' : 'text-indigo-600 bg-indigo-50 hover:bg-indigo-100'}`}>
        {added ? '추가됨' : <span className="inline-flex items-center gap-0.5"><Plus size={11} /> 추가</span>}
      </button>
    </div>
  );
}

// ── Pipeline (실행 순서) item ───────────────────────────────────

function PipelineItem({ item, index, total, onMoveUp, onMoveDown, onRemove, onViewCode }) {
  return (
    <div className="flex items-center gap-2 p-2.5 bg-white rounded-xl border border-slate-200 group hover:border-indigo-200 transition-colors">
      <div className="text-slate-300"><GripVertical size={14} /></div>
      <div className="w-5 h-5 rounded-md bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-black shrink-0">{index + 1}</div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-bold text-slate-800 truncate">{item.name}</p>
        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full uppercase ${item.type === 'processing' ? 'bg-emerald-50 text-emerald-600' : 'bg-purple-50 text-purple-600'}`}>
          {item.type === 'processing' ? '후처리' : '검증'}
        </span>
      </div>
      <div className="flex items-center gap-0.5">
        <button onClick={() => onViewCode(item)} className="p-1 text-slate-300 hover:text-indigo-600 rounded" title="코드 보기"><Code2 size={13} /></button>
        <button onClick={onMoveUp} disabled={index === 0} className="p-1 text-slate-400 hover:text-slate-600 rounded disabled:opacity-20" title="위로"><ArrowUp size={13} /></button>
        <button onClick={onMoveDown} disabled={index === total - 1} className="p-1 text-slate-400 hover:text-slate-600 rounded disabled:opacity-20" title="아래로"><ArrowDown size={13} /></button>
        <button onClick={onRemove} className="p-1 text-slate-400 hover:text-red-500 rounded" title="제거"><Trash2 size={13} /></button>
      </div>
    </div>
  );
}

// ── SRT Preview ─────────────────────────────────────────────────

function SrtPreview({ title, entries }) {
  if (!entries || entries.length === 0) return null;
  return (
    <Card className="mt-6">
      <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-100 flex items-center gap-2">
        <FileText size={14} className="text-slate-400" />
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">{title} ({entries.length}개)</span>
      </div>
      <div className="max-h-60 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
              <th className="px-4 py-2 w-10">#</th>
              <th className="px-4 py-2 w-52">타임코드</th>
              <th className="px-4 py-2">텍스트</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100/60">
            {entries.map((e) => (
              <tr key={e.index} className="hover:bg-slate-50/50">
                <td className="px-4 py-2 text-[10px] font-mono text-slate-400">{e.index}</td>
                <td className="px-4 py-2 text-[10px] font-mono text-indigo-600">{e.timecode}</td>
                <td className="px-4 py-2 text-xs text-slate-700 whitespace-pre-wrap font-mono">{e.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ── Main Test Page ──────────────────────────────────────────────

export default function TestPage() {
  const [broadcasters, setBroadcasters] = useState([]);
  const [selectedB, setSelectedB] = useState('');
  const [allItems, setAllItems] = useState([]);
  const [mappedItems, setMappedItems] = useState([]);
  const [pipeline, setPipeline] = useState([]);
  const [srtText, setSrtText] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [codeViewItem, setCodeViewItem] = useState(null);
  const [availTab, setAvailTab] = useState('processing'); // processing | validation

  useEffect(() => {
    Promise.all([broadcasterApi.list(), techItemApi.list()]).then(([b, t]) => {
      setBroadcasters(b);
      setAllItems(t.map((x, i) => ({ ...x, _idx: i })));
      if (b.length > 0) setSelectedB(b[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedB) return;
    mappingApi.get(selectedB).then((data) => {
      const items = data.items || [];
      setMappedItems(items);
      setPipeline(items.map((i) => i.id));
      setResult(null);
    });
  }, [selectedB]);

  const getItem = useCallback((id) => allItems.find((i) => i.id === id), [allItems]);

  const curPrefix = useMemo(() => {
    const bc = broadcasters.find((b) => b.id === selectedB);
    return bc ? BC_PREFIX[bc.code] : null;
  }, [broadcasters, selectedB]);

  // 사용 가능 목록: 이 방송사 전용(0) → 공통(1) → 다른 방송사(2)
  const rankOf = useCallback((item) => {
    if (item.scope === 'specific') {
      return item.id.split('_')[1] === curPrefix ? 0 : 2;
    }
    return 1;
  }, [curPrefix]);

  const available = useMemo(() => {
    return allItems
      .filter((i) => i.type === availTab)
      .slice()
      .sort((a, b) => {
        const ra = rankOf(a), rb = rankOf(b);
        return ra !== rb ? ra - rb : (a._idx - b._idx);
      });
  }, [allItems, availTab, rankOf]);

  const moveUp = (idx) => { if (idx === 0) return; setPipeline((p) => { const n = [...p]; [n[idx - 1], n[idx]] = [n[idx], n[idx - 1]]; return n; }); };
  const moveDown = (idx) => setPipeline((p) => { if (idx >= p.length - 1) return p; const n = [...p]; [n[idx], n[idx + 1]] = [n[idx + 1], n[idx]]; return n; });
  const removeFromPipeline = (idx) => setPipeline((p) => p.filter((_, i) => i !== idx));
  const addToPipeline = (id) => setPipeline((p) => (p.includes(id) ? p : [...p, id]));

  const handleRun = async () => {
    if (!srtText.trim() || pipeline.length === 0) return;
    setRunning(true); setResult(null);
    try {
      setResult(await testApi.run(srtText, selectedB, pipeline));
    } catch (err) {
      alert(err?.response?.data?.detail || '테스트 실행 실패');
    } finally {
      setRunning(false);
    }
  };

  const handleViewCode = (itemOrId) => {
    const item = typeof itemOrId === 'string' ? getItem(itemOrId) : itemOrId;
    if (item) setCodeViewItem(item);
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: config */}
      <div className="w-[480px] bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-5 border-b border-slate-100">
          <h3 className="text-lg font-bold text-slate-800">테스트 파이프라인</h3>
          <p className="text-xs text-slate-400 mt-1">요청 전 미리 돌려보세요. 후처리는 텍스트가 바뀌고, 검증은 걸리면 재작업 대상으로 표시됩니다.</p>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* 방송사 + SRT */}
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide mb-2 block">방송사</label>
            <select value={selectedB} onChange={(e) => setSelectedB(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500">
              {broadcasters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">SRT 입력</label>
              <div className="flex gap-1.5">
                <button onClick={() => setSrtText(SAMPLE_SRT)} className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors">예시 불러오기</button>
                {srtText && <button onClick={() => setSrtText('')} className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors">초기화</button>}
              </div>
            </div>
            <textarea value={srtText} onChange={(e) => setSrtText(e.target.value)}
              placeholder={`1\n00:00:01,000 --> 00:00:03,000\n자막 텍스트를 입력하세요...`}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500 resize-none h-32 leading-relaxed" />
          </div>

          {/* 사용 가능 목록 */}
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide mb-2 block">사용 가능 함수</label>
            <div className="flex gap-1 mb-2">
              <button onClick={() => setAvailTab('processing')}
                className={`flex-1 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-colors ${availTab === 'processing' ? 'bg-emerald-600 text-white' : 'bg-slate-50 text-slate-500 border border-slate-200'}`}>
                <Wand2 size={12} /> 후처리
              </button>
              <button onClick={() => setAvailTab('validation')}
                className={`flex-1 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-colors ${availTab === 'validation' ? 'bg-purple-600 text-white' : 'bg-slate-50 text-slate-500 border border-slate-200'}`}>
                <ShieldCheck size={12} /> 검증
              </button>
            </div>
            <div className="space-y-1 max-h-56 overflow-y-auto pr-0.5">
              {available.map((item) => (
                <AvailableRow key={item.id} item={item} added={pipeline.includes(item.id)} onAdd={addToPipeline} onViewCode={handleViewCode} />
              ))}
            </div>
            <p className="text-[9px] text-slate-300 mt-1.5">정렬: 이 방송사 전용 → 공통 → 다른 방송사</p>
          </div>

          {/* 실행 순서 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">실행 순서 ({pipeline.length}개)</label>
              <div className="flex gap-1.5">
                {pipeline.length > 0 && <button onClick={() => setPipeline([])} className="text-[10px] font-bold text-slate-400 hover:text-red-500 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors">비우기</button>}
                <button onClick={() => setPipeline(mappedItems.map((i) => i.id))} className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors flex items-center gap-1">
                  <RotateCcw size={10} /> 기본값
                </button>
              </div>
            </div>
            {pipeline.length === 0 ? (
              <div className="text-center py-6 text-slate-300 text-xs border-2 border-dashed border-slate-200 rounded-xl">
                위 목록에서 함수를 추가하세요
              </div>
            ) : (
              <div className="space-y-1.5">
                {pipeline.map((id, idx) => {
                  const item = getItem(id);
                  if (!item) return null;
                  return <PipelineItem key={id} item={item} index={idx} total={pipeline.length}
                    onMoveUp={() => moveUp(idx)} onMoveDown={() => moveDown(idx)} onRemove={() => removeFromPipeline(idx)} onViewCode={handleViewCode} />;
                })}
              </div>
            )}
          </div>
        </div>

        <div className="p-5 border-t border-slate-100">
          <button onClick={handleRun} disabled={!srtText.trim() || pipeline.length === 0 || running}
            className="w-full py-3.5 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-40 disabled:pointer-events-none shadow-lg shadow-indigo-200/50 flex items-center justify-center gap-2">
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {running ? '실행 중...' : '파이프라인 실행'}
          </button>
        </div>
      </div>

      {/* Right: results */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-50/50">
        <div className="p-8 border-b border-slate-200 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-slate-800">테스트 결과</h3>
              <p className="text-sm text-slate-400 mt-0.5">각 단계별 처리 결과와 재작업 대상을 확인합니다.</p>
            </div>
            {result && !result.error && (
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold ${
                result.all_passed ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
              }`}>
                {result.all_passed ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                {result.all_passed ? '납품 가능' : `재작업 ${result.total_errors}건`}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          {!result && !running && (
            <div className="flex flex-col items-center justify-center h-full text-slate-300">
              <div className="w-20 h-20 rounded-3xl bg-slate-100 flex items-center justify-center mb-4"><Play size={32} className="text-slate-300 ml-1" /></div>
              <p className="text-sm font-medium text-slate-400">SRT를 입력하고 파이프라인을 실행하세요</p>
            </div>
          )}
          {running && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
              <p className="text-sm font-bold text-slate-600">파이프라인 실행 중...</p>
              <p className="text-xs text-slate-400 mt-1">{pipeline.length}개 단계 처리 중</p>
            </div>
          )}
          {result && !running && result.error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
              <AlertTriangle size={16} /> {result.error}
            </div>
          )}
          {result && !running && !result.error && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-6 text-xs">
                  <div className="flex items-center gap-2"><span className="text-slate-400">엔트리</span><span className="font-bold text-slate-800">{result.srt_entry_count}개</span></div>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="flex items-center gap-2"><span className="text-slate-400">단계</span><span className="font-bold text-slate-800">{result.pipeline_length}개</span></div>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="flex items-center gap-2"><span className="text-slate-400">통과</span><span className="font-bold text-emerald-600">{result.steps.filter((s) => s.status === 'pass').length}</span></div>
                  <div className="flex items-center gap-2"><span className="text-slate-400">재작업</span><span className="font-bold text-red-600">{result.steps.filter((s) => s.status === 'fail').length}</span></div>
                </div>
                <div className="ml-auto flex items-center gap-1">
                  {result.steps.map((s, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className={`w-3 h-3 rounded-full ${s.status === 'pass' ? 'bg-emerald-500' : s.status === 'fail' ? 'bg-red-500' : s.status === 'skip' ? 'bg-slate-300' : 'bg-amber-500'}`} title={s.item_name} />
                      {i < result.steps.length - 1 && <div className="w-3 h-px bg-slate-300" />}
                    </div>
                  ))}
                </div>
              </div>

              {result.steps.map((step) => <StepResultCard key={step.step} step={step} onViewCode={handleViewCode} />)}

              <SrtPreview title="최종 결과 SRT" entries={result.final_entries} />
              <SrtPreview title="원본 파싱 SRT" entries={result.entries} />
            </div>
          )}
        </div>
      </div>

      <CodeViewerModal open={!!codeViewItem} onClose={() => setCodeViewItem(null)} item={codeViewItem} />
    </div>
  );
}