import { useState, useEffect, useCallback } from 'react';
import {
  Play, Upload, ChevronDown, ChevronRight, GripVertical, Code2,
  CheckCircle2, XCircle, AlertTriangle, Loader2, ArrowUp, ArrowDown,
  FileText, Trash2, RotateCcw, Eye, X, Copy, Check
} from 'lucide-react';
import { broadcasterApi, mappingApi, techItemApi, testApi } from '../api/client';
import { Card, Btn, Pill, Modal, EmptyState } from '../components/ui';

// ── Sample SRT ──────────────────────────────────────────────────

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
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!item) return null;

  return (
    <Modal open={open} onClose={onClose} title={`${item.name} — 소스코드`} wide>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
            item.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
          }`}>
            {item.type === 'processing' ? '후처리' : '검증'}
          </span>
          <span className="text-xs text-slate-500">{item.desc}</span>
        </div>
        <Btn small variant="ghost" onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? '복사됨' : '복사'}
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
          <p className="text-xs text-slate-300 mt-1">라이브러리에서 코드를 등록해주세요.</p>
        </div>
      )}

      {/* Params */}
      {item.params && Object.keys(item.params).length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block mb-2">기본 파라미터</span>
          <div className="flex flex-wrap gap-2">
            {Object.entries(item.params).map(([k, v]) => (
              <div key={k} className="flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                <span className="text-[10px] font-mono text-slate-500">{k}:</span>
                <span className="text-[10px] font-mono font-bold text-indigo-600">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}

// ── Error Detail Row ────────────────────────────────────────────

function ErrorRow({ error, index }) {
  return (
    <div className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${
      error.severity === 'error'
        ? 'bg-red-50/50 border-red-100'
        : 'bg-amber-50/50 border-amber-100'
    }`}>
      <div className="mt-0.5">
        {error.severity === 'error'
          ? <XCircle size={14} className="text-red-500" />
          : <AlertTriangle size={14} className="text-amber-500" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
            error.severity === 'error' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
          }`}>
            {error.severity}
          </span>
          <span className="text-[10px] font-mono text-slate-400">#{error.index}</span>
          {error.timecode && <span className="text-[10px] font-mono text-slate-400">{error.timecode}</span>}
          {error.type && <span className="text-[10px] font-bold text-slate-500">{error.type}</span>}
        </div>
        <p className="text-xs text-slate-700 font-medium">{error.message}</p>
        {error.text && (
          <div className="mt-1.5 px-3 py-2 bg-white rounded-lg border border-slate-200 font-mono text-[11px] text-slate-600 whitespace-pre-wrap">
            {error.text}
          </div>
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

// ── Step Result Card ────────────────────────────────────────────

function StepResultCard({ step, onViewCode }) {
  const [expanded, setExpanded] = useState(step.status === 'fail');
  const result = step.result || {};
  const errors = result.errors || [];

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center gap-4 px-5 py-4 cursor-pointer transition-colors ${
          step.status === 'fail' ? 'bg-red-50/30' : step.status === 'pass' ? 'bg-emerald-50/20' : 'bg-slate-50/50'
        }`}
      >
        {/* Step number */}
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-black shrink-0 ${
          step.status === 'fail' ? 'bg-red-100 text-red-700' : step.status === 'pass' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'
        }`}>
          {step.step}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800">{step.item_name}</span>
            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${
              step.item_type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
            }`}>
              {step.item_type === 'processing' ? '후처리' : '검증'}
            </span>
          </div>
          {result.info && <p className="text-[11px] text-slate-400 mt-0.5">{result.info}</p>}
        </div>

        {/* Status + actions */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onViewCode(step.item_id); }}
            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            title="코드 보기"
          >
            <Code2 size={15} />
          </button>

          {/* Error count badge */}
          {result.error_count > 0 && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-200">
              {result.error_count} errors
            </span>
          )}

          {/* Status icon */}
          {step.status === 'pass' && <CheckCircle2 size={20} className="text-emerald-500" />}
          {step.status === 'fail' && <XCircle size={20} className="text-red-500" />}
          {step.status === 'error' && <AlertTriangle size={20} className="text-amber-500" />}

          <ChevronDown size={16} className={`text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-100">
          {/* Params used */}
          {step.params_used && Object.keys(step.params_used).length > 0 && (
            <div className="px-5 py-3 bg-slate-50/50 border-b border-slate-100">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">적용 파라미터</span>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {Object.entries(step.params_used).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-1 bg-white px-2 py-0.5 rounded border border-slate-200">
                    <span className="text-[9px] font-mono text-slate-400">{k}:</span>
                    <span className="text-[9px] font-mono font-bold text-indigo-600">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Errors list */}
          <div className="px-5 py-4">
            {errors.length > 0 ? (
              <div className="space-y-2">
                {errors.map((err, i) => (
                  <ErrorRow key={i} error={err} index={i} />
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 py-3 text-emerald-600 text-xs font-medium">
                <CheckCircle2 size={14} />
                오류 없음 — 모든 항목이 정상적으로 통과했습니다.
              </div>
            )}
          </div>

          {/* Summary bar */}
          <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex items-center gap-4 text-[10px] text-slate-500">
            <span>총 엔트리: <b className="text-slate-700">{result.total_entries}</b></span>
            <span>오류: <b className={result.error_count > 0 ? 'text-red-600' : 'text-emerald-600'}>{result.error_count}</b></span>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Pipeline Item (reorderable) ─────────────────────────────────

function PipelineItem({ item, index, total, onMoveUp, onMoveDown, onRemove, onViewCode }) {
  return (
    <div className="flex items-center gap-2 p-3 bg-white rounded-xl border border-slate-200 group hover:border-indigo-200 transition-colors">
      {/* Drag handle visual */}
      <div className="text-slate-300 cursor-grab">
        <GripVertical size={16} />
      </div>

      {/* Order number */}
      <div className="w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-black shrink-0">
        {index + 1}
      </div>

      {/* Item info */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-bold text-slate-800 truncate">{item.name}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full uppercase ${
            item.type === 'processing' ? 'bg-emerald-50 text-emerald-600' : 'bg-purple-50 text-purple-600'
          }`}>
            {item.type === 'processing' ? '후처리' : '검증'}
          </span>
          <Pill type={item.tag} kind="tag" />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => onViewCode(item)} className="p-1 text-slate-400 hover:text-indigo-600 rounded" title="코드 보기">
          <Code2 size={13} />
        </button>
        <button onClick={onMoveUp} disabled={index === 0} className="p-1 text-slate-400 hover:text-slate-600 rounded disabled:opacity-20" title="위로">
          <ArrowUp size={13} />
        </button>
        <button onClick={onMoveDown} disabled={index === total - 1} className="p-1 text-slate-400 hover:text-slate-600 rounded disabled:opacity-20" title="아래로">
          <ArrowDown size={13} />
        </button>
        <button onClick={onRemove} className="p-1 text-slate-400 hover:text-red-500 rounded" title="제거">
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

// ── SRT Preview Table ───────────────────────────────────────────

function SrtPreview({ entries }) {
  if (!entries || entries.length === 0) return null;
  return (
    <Card className="mt-6">
      <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-100 flex items-center gap-2">
        <FileText size={14} className="text-slate-400" />
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">파싱된 SRT ({entries.length}개 엔트리)</span>
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
  // Data
  const [broadcasters, setBroadcasters] = useState([]);
  const [selectedB, setSelectedB] = useState('');
  const [allItems, setAllItems] = useState([]);
  const [mappedItems, setMappedItems] = useState([]);

  // Pipeline
  const [pipeline, setPipeline] = useState([]); // ordered item IDs
  const [srtText, setSrtText] = useState('');

  // Results
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  // Code viewer
  const [codeViewItem, setCodeViewItem] = useState(null);

  // Load broadcasters and all items
  useEffect(() => {
    Promise.all([broadcasterApi.list(), techItemApi.list()]).then(([b, t]) => {
      setBroadcasters(b);
      setAllItems(t);
      if (b.length > 0) {
        setSelectedB(b[0].id);
      }
    });
  }, []);

  // When broadcaster changes, load mapped items and reset pipeline
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

  // Pipeline reorder
  const moveUp = (idx) => {
    if (idx === 0) return;
    setPipeline((prev) => {
      const next = [...prev];
      [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
      return next;
    });
  };
  const moveDown = (idx) => {
    setPipeline((prev) => {
      if (idx >= prev.length - 1) return prev;
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  };
  const removeFromPipeline = (idx) => {
    setPipeline((prev) => prev.filter((_, i) => i !== idx));
  };
  const addToPipeline = (itemId) => {
    if (!pipeline.includes(itemId)) {
      setPipeline((prev) => [...prev, itemId]);
    }
  };

  // Run test
  const handleRun = async () => {
    if (!srtText.trim() || pipeline.length === 0) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await testApi.run(srtText, selectedB, pipeline);
      setResult(res);
    } catch (err) {
      alert(err?.response?.data?.detail || '테스트 실행 실패');
    } finally {
      setRunning(false);
    }
  };

  // View code
  const handleViewCode = (itemOrId) => {
    const item = typeof itemOrId === 'string' ? getItem(itemOrId) : itemOrId;
    if (item) setCodeViewItem(item);
  };

  const availableToAdd = mappedItems.filter((i) => !pipeline.includes(i.id));
  const selectedBroadcaster = broadcasters.find((b) => b.id === selectedB);

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left Panel: Config ── */}
      <div className="w-[420px] bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-lg font-bold text-slate-800">테스트 파이프라인</h3>
          <p className="text-xs text-slate-400 mt-1">SRT 자막을 입력하고 후처리/검증 순서를 지정하여 테스트합니다.</p>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Broadcaster select */}
          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide mb-2 block">방송사</label>
            <select
              value={selectedB}
              onChange={(e) => setSelectedB(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {broadcasters.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          {/* SRT Input */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">SRT 입력</label>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setSrtText(SAMPLE_SRT)}
                  className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors"
                >
                  예시 불러오기
                </button>
                {srtText && (
                  <button
                    onClick={() => setSrtText('')}
                    className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    초기화
                  </button>
                )}
              </div>
            </div>
            <textarea
              value={srtText}
              onChange={(e) => setSrtText(e.target.value)}
              placeholder={`1\n00:00:01,000 --> 00:00:03,000\n자막 텍스트를 입력하세요...`}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500 resize-none h-40 leading-relaxed"
            />
          </div>

          {/* Pipeline Order */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                실행 순서 ({pipeline.length}개)
              </label>
              {pipeline.length > 0 && (
                <button
                  onClick={() => setPipeline(mappedItems.map((i) => i.id))}
                  className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors flex items-center gap-1"
                >
                  <RotateCcw size={10} /> 리셋
                </button>
              )}
            </div>

            {pipeline.length === 0 ? (
              <div className="text-center py-6 text-slate-300 text-xs">
                매핑된 항목이 없습니다
              </div>
            ) : (
              <div className="space-y-1.5">
                {pipeline.map((id, idx) => {
                  const item = getItem(id);
                  if (!item) return null;
                  return (
                    <PipelineItem
                      key={id}
                      item={item}
                      index={idx}
                      total={pipeline.length}
                      onMoveUp={() => moveUp(idx)}
                      onMoveDown={() => moveDown(idx)}
                      onRemove={() => removeFromPipeline(idx)}
                      onViewCode={handleViewCode}
                    />
                  );
                })}
              </div>
            )}

            {/* Add more items */}
            {availableToAdd.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide block mb-2">추가 가능</span>
                <div className="flex flex-wrap gap-1.5">
                  {availableToAdd.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => addToPipeline(item.id)}
                      className="text-[10px] font-medium text-slate-600 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-indigo-200 transition-colors"
                    >
                      + {item.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Run button */}
        <div className="p-5 border-t border-slate-100">
          <button
            onClick={handleRun}
            disabled={!srtText.trim() || pipeline.length === 0 || running}
            className="w-full py-3.5 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-40 disabled:pointer-events-none shadow-lg shadow-indigo-200/50 flex items-center justify-center gap-2"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {running ? '실행 중...' : '파이프라인 실행'}
          </button>
        </div>
      </div>

      {/* ── Right Panel: Results ── */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-50/50">
        <div className="p-8 border-b border-slate-200 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-slate-800">테스트 결과</h3>
              <p className="text-sm text-slate-400 mt-0.5">각 단계별 실행 결과와 오류 상세를 확인합니다.</p>
            </div>
            {result && (
              <div className="flex items-center gap-3">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold ${
                  result.all_passed
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {result.all_passed ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  {result.all_passed ? 'ALL PASS' : `${result.total_errors} ERRORS`}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-8">
          {!result && !running && (
            <div className="flex flex-col items-center justify-center h-full text-slate-300">
              <div className="w-20 h-20 rounded-3xl bg-slate-100 flex items-center justify-center mb-4">
                <Play size={32} className="text-slate-300 ml-1" />
              </div>
              <p className="text-sm font-medium text-slate-400">SRT를 입력하고 파이프라인을 실행하세요</p>
              <p className="text-xs text-slate-300 mt-1">결과가 여기에 표시됩니다</p>
            </div>
          )}

          {running && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
              <p className="text-sm font-bold text-slate-600">파이프라인 실행 중...</p>
              <p className="text-xs text-slate-400 mt-1">{pipeline.length}개 단계 처리 중</p>
            </div>
          )}

          {result && !running && (
            <div className="space-y-4">
              {/* Summary bar */}
              <div className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-6 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">엔트리</span>
                    <span className="font-bold text-slate-800">{result.srt_entry_count}개</span>
                  </div>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">단계</span>
                    <span className="font-bold text-slate-800">{result.pipeline_length}개</span>
                  </div>
                  <div className="h-4 w-px bg-slate-200" />
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">통과</span>
                    <span className="font-bold text-emerald-600">
                      {result.steps.filter((s) => s.status === 'pass').length}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">실패</span>
                    <span className="font-bold text-red-600">
                      {result.steps.filter((s) => s.status === 'fail').length}
                    </span>
                  </div>
                </div>

                {/* Pipeline flow visualization */}
                <div className="ml-auto flex items-center gap-1">
                  {result.steps.map((s, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className={`w-3 h-3 rounded-full ${
                        s.status === 'pass' ? 'bg-emerald-500' : s.status === 'fail' ? 'bg-red-500' : 'bg-amber-500'
                      }`} title={s.item_name} />
                      {i < result.steps.length - 1 && <div className="w-3 h-px bg-slate-300" />}
                    </div>
                  ))}
                </div>
              </div>

              {/* Step results */}
              {result.steps.map((step) => (
                <StepResultCard
                  key={step.step}
                  step={step}
                  onViewCode={handleViewCode}
                />
              ))}

              {/* Parsed SRT preview */}
              <SrtPreview entries={result.entries} />
            </div>
          )}
        </div>
      </div>

      {/* Code Viewer Modal */}
      <CodeViewerModal open={!!codeViewItem} onClose={() => setCodeViewItem(null)} item={codeViewItem} />
    </div>
  );
}
