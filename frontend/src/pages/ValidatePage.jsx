import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  ShieldCheck, Upload, Loader2, CheckCircle2, XCircle, AlertTriangle,
  Copy, Check, RotateCcw, ChevronDown, Filter, Plus, Clock, AlignLeft, Code2, Info,
} from 'lucide-react';
import { broadcasterApi, techItemApi, validateApi } from '../api/client';
import { getGuide } from '../data/functionGuide';
import { Card, Btn } from '../components/ui';

const SAMPLE_SRT = `1
00:00:01,000 --> 00:00:01,400
- 안녕하세요

2
00:00:01,450 --> 00:00:03,000
이것은 기준 글자 수를 훌쩍 넘겨버리는 아주 긴 한 줄입니다
두 번째 줄
세 번째 줄

3
00:00:04,000 --> 00:00:06,000
글쎄요.....(웃음

4
00:00:05,000 --> 00:00:07,000
겹치는 자막입니다`;

// 검증 항목에 붙는 파라미터 — 함수 인자 이름 대신 사람 말로 보여준다.
// valid_type 처럼 내부 분기용인 건 화면에 의미가 없어 뺀다.
const PARAM_KO = {
  criterion: '기준',
  max_length: '최대 글자 수',
  max_lines: '최대 줄 수',
  max_lines_with_hyphen: '하이픈이면 최대 줄 수',
  min_duration_sec: '최소 길이(초)',
  gap_sec: '최소 간격(초)',
  allow_number_range: '숫자 범위 허용',
};

// 글자 수·줄 수 한도는 항목이 아니라 방송사 규격(validation_params)에서 온다.
// 항목 줄에 숫자가 안 보이면 "방송사 기준"이 몇인지 알 수 없어 채워 넣는다.
function effectiveParams(item, vp) {
  const p = { ...(item.params || {}) };
  if (item.function_name === 'validate_length_lines' && vp?.max_length != null) p.max_length = vp.max_length;
  if (item.function_name === 'validate_line_count' && vp?.max_lines != null) p.max_lines = vp.max_lines;
  return p;
}

function readableParams(params) {
  return Object.entries(params || {})
    .filter(([k]) => PARAM_KO[k] != null)
    // 불리언은 "숫자 범위 허용 true" 대신 예/아니오로 읽히게 한다
    .map(([k, v]) => (typeof v === 'boolean' ? `${PARAM_KO[k]} ${v ? '예' : '아니오'}` : `${PARAM_KO[k]} ${v}`));
}

// 이 검증이 무엇을 보는지 — 화면에 검증해 둔 설명(FUNCTION_GUIDE)을 우선 쓰고,
// 없으면 DB 에 들어 있는 항목 설명으로 떨어진다.
function explain(item) {
  const guide = getGuide(item);
  return guide?.summary || item?.desc || '';
}

// 규격 요약 칩에 쓰는 라벨
const PARAM_LABEL = {
  max_length: (v) => `한 줄 ${v}자`,
  max_lines: (v) => `${v}줄`,
  max_byte_length: (v) => `${v}바이트`,
  weight_etc: (v) => (v === 1 ? null : `기타 문자 ${v}자`),
  weight_kor: () => null,
};

// ── 요약 숫자 타일 ──────────────────────────────────────────────

function Stat({ label, value, unit, tone = 'slate' }) {
  const tones = {
    slate: 'text-slate-800',
    red: 'text-red-600',
    emerald: 'text-emerald-600',
  };
  return (
    <div className="px-5 py-3">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-black leading-tight ${tones[tone]}`}>
        {value}
        {unit && <span className="text-[11px] font-bold text-slate-400 ml-1">{unit}</span>}
      </p>
    </div>
  );
}

// ── 검증 항목 칩 (클릭 = 필터) ──────────────────────────────────

function RuleChip({ rule, active, onClick, showFn }) {
  const failed = rule.status === 'fail';
  const broken = rule.status === 'error' || rule.status === 'skip';
  const base = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all';
  const style = active
    ? 'bg-slate-900 text-white border-slate-900'
    : failed
      ? 'bg-red-50 text-red-700 border-red-200 hover:border-red-400'
      : broken
        ? 'bg-amber-50 text-amber-700 border-amber-200'
        : 'bg-white text-slate-400 border-slate-200 hover:border-slate-300';
  return (
    <button onClick={onClick} disabled={broken} className={`${base} ${style}`}
      title={[explain(rule), rule.info, showFn ? `${rule.function_name}()` : null].filter(Boolean).join('\n')}>
      {failed ? <XCircle size={11} /> : broken ? <AlertTriangle size={11} /> : <CheckCircle2 size={11} />}
      <span className="max-w-[190px] truncate">{rule.name}</span>
      {failed && (
        <span className={`px-1.5 rounded-full text-[10px] ${active ? 'bg-white/20' : 'bg-red-200/70 text-red-800'}`}>
          {rule.error_count}
        </span>
      )}
    </button>
  );
}

// ── 자막 한 건 ──────────────────────────────────────────────────

function EntryRow({ entry, maxLength, filterRule, showFn }) {
  const errors = filterRule ? entry.errors.filter((e) => e.rule_id === filterRule) : entry.errors;
  const bad = errors.length > 0;
  // 어느 줄이 문제인지 — 길이 초과 오류는 line 번호를 들고 온다
  const badLines = new Set(errors.map((e) => e.line).filter(Boolean));

  return (
    <div className={`border-l-[3px] ${bad ? 'border-l-red-400 bg-red-50/30' : 'border-l-transparent'}`}>
      <div className="flex gap-4 px-5 py-3.5 border-b border-slate-100">
        {/* 번호 · 싱크 */}
        <div className="w-44 shrink-0">
          <div className="flex items-center gap-2">
            <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-black ${
              bad ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>{entry.index}</span>
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <Clock size={10} /> {entry.duration_sec}s
            </span>
          </div>
          <p className="text-[10px] font-mono text-indigo-500/80 mt-1.5 leading-tight">{entry.timecode}</p>
        </div>

        {/* 본문 — 줄별 글자 수 */}
        <div className="flex-1 min-w-0 space-y-1">
          {entry.lines.map((line, i) => {
            const over = maxLength != null && line.length > maxLength;
            return (
              <div key={i} className="flex items-start gap-2">
                <span className={`shrink-0 mt-0.5 text-[10px] font-mono font-bold w-12 text-right ${
                  over ? 'text-red-600' : badLines.has(i + 1) ? 'text-red-500' : 'text-slate-300'}`}>
                  {line.length}
                  {maxLength != null && <span className="text-slate-300 font-normal">/{maxLength}</span>}
                </span>
                <span className={`text-[13px] font-mono whitespace-pre-wrap break-all ${
                  over ? 'text-red-700 bg-red-100/60 rounded px-1' : 'text-slate-700'}`}>
                  {line.text || <span className="text-slate-300">(빈 줄)</span>}
                </span>
              </div>
            );
          })}
        </div>

        {/* 걸린 규칙 */}
        <div className="w-[300px] shrink-0 space-y-1">
          {errors.length === 0 ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600">
              <CheckCircle2 size={12} /> 통과
            </span>
          ) : errors.map((e, i) => (
            <div key={i} className="flex items-start gap-1.5 px-2.5 py-1.5 rounded-lg bg-white border border-red-100">
              <XCircle size={11} className="text-red-500 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-[11px] font-bold text-slate-700 leading-tight">{e.message}</p>
                <p className="text-[9px] text-slate-400 truncate mt-0.5">
                  {e.rule_name}
                  {showFn && e.function_name && <span className="font-mono text-slate-300 ml-1">{e.function_name}()</span>}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 검증 항목 선택 ──────────────────────────────────────────────

function CaseExamples({ item }) {
  const guide = getGuide(item);
  const cases = guide?.cases || [];
  if (cases.length === 0) {
    return <p className="text-[11px] text-slate-400 px-3 py-2">등록된 예시가 없습니다.</p>;
  }
  return (
    <div className="px-3 py-2 space-y-1">
      {cases.map((c, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded ${
            c.fail ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
            {c.fail ? '오류' : '정상'}
          </span>
          <span className="text-[11px] font-mono text-slate-600 truncate">{c.input}</span>
          {c.label && <span className="text-[10px] text-slate-300 ml-auto shrink-0">{c.label}</span>}
        </div>
      ))}
    </div>
  );
}

function ItemRow({ item, on, onToggle, showFn, vp }) {
  const [open, setOpen] = useState(false);
  const desc = explain(item);
  const params = readableParams(effectiveParams(item, vp));

  return (
    <div className={`rounded-lg border transition-colors ${
      on ? 'bg-indigo-50/50 border-indigo-200' : 'bg-white border-slate-200/70 hover:border-slate-300'}`}>
      <div className="flex items-start gap-2.5 px-3 py-2">
        <input type="checkbox" checked={on} onChange={onToggle} id={`chk-${item.id}`}
          className="w-3.5 h-3.5 rounded accent-indigo-600 shrink-0 mt-0.5 cursor-pointer" />
        <label htmlFor={`chk-${item.id}`} className="min-w-0 flex-1 cursor-pointer">
          <p className={`text-[12px] font-bold leading-snug ${on ? 'text-slate-800' : 'text-slate-400'}`}>
            {item.name}
          </p>
          {desc && (
            <p className={`text-[11px] leading-snug mt-0.5 ${on ? 'text-slate-500' : 'text-slate-400/70'} ${
              open ? '' : 'line-clamp-2'}`}>
              {desc}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-1 mt-1">
            {params.map((t) => (
              <span key={t} className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{t}</span>
            ))}
            {showFn && item.function_name && (
              <span className="text-[9px] font-mono text-indigo-400/80">{item.function_name}()</span>
            )}
          </div>
        </label>
        <button onClick={() => setOpen(!open)} title="예시 보기"
          className={`p-1 rounded shrink-0 transition-colors ${open ? 'text-indigo-600 bg-indigo-100' : 'text-slate-300 hover:text-indigo-500'}`}>
          <Info size={13} />
        </button>
      </div>
      {open && (
        <div className="border-t border-slate-100 bg-slate-50/60 rounded-b-lg">
          <CaseExamples item={item} />
        </div>
      )}
    </div>
  );
}

function ItemPicker({ items, selected, onToggle, extras, onAddExtra, showFn, vp }) {
  const [showExtras, setShowExtras] = useState(false);
  return (
    <div>
      <div className="space-y-1">
        {items.map((it) => (
          <ItemRow key={it.id} item={it} on={selected.includes(it.id)}
            onToggle={() => onToggle(it.id)} showFn={showFn} vp={vp} />
        ))}
      </div>

      {extras.length > 0 && (
        <div className="mt-2">
          <button onClick={() => setShowExtras(!showExtras)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-dashed border-slate-300 text-[11px] font-bold text-slate-500 hover:border-indigo-300 hover:text-indigo-600 transition-colors">
            <span className="inline-flex items-center gap-1.5"><Plus size={12} /> 다른 검증 항목 추가 ({extras.length})</span>
            <ChevronDown size={13} className={`transition-transform ${showExtras ? 'rotate-180' : ''}`} />
          </button>
          {showExtras && (
            <div className="mt-1.5 space-y-1">
              {extras.map((it) => (
                <div key={it.id} className="flex items-start gap-2 px-3 py-2 rounded-lg border border-slate-200/70 bg-white">
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold text-slate-600 leading-snug">{it.name}</p>
                    <p className="text-[10px] text-slate-400/80 leading-snug mt-0.5 line-clamp-2">{explain(it)}</p>
                    {showFn && it.function_name && (
                      <p className="text-[9px] font-mono text-slate-300 truncate mt-0.5">{it.function_name}()</p>
                    )}
                  </div>
                  <button onClick={() => onAddExtra(it)}
                    className="text-[10px] font-bold px-2 py-1 rounded-lg text-indigo-600 bg-indigo-50 hover:bg-indigo-100 shrink-0">
                    추가
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main ────────────────────────────────────────────────────────

export default function ValidatePage() {
  const [broadcasters, setBroadcasters] = useState([]);
  const [selectedB, setSelectedB] = useState('');
  const [defaultItems, setDefaultItems] = useState([]);
  const [addedItems, setAddedItems] = useState([]);   // 다른 방송사에서 끌어온 항목
  const [allValidation, setAllValidation] = useState([]);
  const [selected, setSelected] = useState([]);
  const [params, setParams] = useState(null);
  const [dedupedCount, setDedupedCount] = useState(0);

  const [srtText, setSrtText] = useState('');
  const [fileName, setFileName] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const [filterRule, setFilterRule] = useState(null);
  const [onlyErrors, setOnlyErrors] = useState(true);
  const [copied, setCopied] = useState(false);
  // 함수명은 이 화면 사용자에게 필요 없는 정보라 기본은 끈다 (선택은 기억한다)
  const [showFn, setShowFn] = useState(() => localStorage.getItem('airrule_validate_show_fn') === '1');
  const fileRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('airrule_validate_show_fn', showFn ? '1' : '0');
  }, [showFn]);

  useEffect(() => {
    Promise.all([broadcasterApi.list(), techItemApi.list()]).then(([b, t]) => {
      setBroadcasters(b);
      setAllValidation(t.filter((x) => x.type === 'validation'));
      if (b.length > 0) setSelectedB(b[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedB) return;
    validateApi.items(selectedB).then((d) => {
      setDefaultItems(d.items);
      setAddedItems([]);
      setSelected(d.items.map((i) => i.id));
      setParams(d.validation_params);
      setDedupedCount(d.deduped_count || 0);
      setResult(null);
      setFilterRule(null);
    });
  }, [selectedB]);

  const pickerItems = useMemo(() => [...defaultItems, ...addedItems], [defaultItems, addedItems]);

  // 이미 목록에 있는 함수+파라미터는 "추가" 후보에서 뺀다 (같은 검사 중복 방지)
  const extras = useMemo(() => {
    const key = (i) => `${i.function_name}|${JSON.stringify(i.params || {})}`;
    const have = new Set(pickerItems.map(key));
    const seen = new Set();
    return allValidation.filter((i) => {
      const k = key(i);
      if (have.has(k) || seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }, [allValidation, pickerItems]);

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  const addExtra = (item) => {
    setAddedItems((a) => (a.some((x) => x.id === item.id) ? a : [...a, item]));
    setSelected((s) => (s.includes(item.id) ? s : [...s, item.id]));
  };
  const resetItems = () => {
    setAddedItems([]);
    setSelected(defaultItems.map((i) => i.id));
  };

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setSrtText(String(reader.result || '').replace(/^﻿/, ''));
      setFileName(file.name);
    };
    reader.readAsText(file, 'utf-8');
    e.target.value = '';
  };

  const handleRun = async () => {
    if (!srtText.trim() || selected.length === 0) return;
    setRunning(true); setResult(null); setFilterRule(null);
    try {
      // selected 는 클릭 순서라, 화면 순서(pickerItems)대로 정렬해서 보낸다
      const ordered = pickerItems.filter((i) => selected.includes(i.id)).map((i) => i.id);
      const res = await validateApi.run(srtText, selectedB, ordered);
      setResult(res);
      setOnlyErrors(true);
    } catch (err) {
      alert(err?.response?.data?.detail || '검증 실행 실패');
    } finally {
      setRunning(false);
    }
  };

  // 실제 파이프라인이 영상 폴더에 남기는 오류 로그와 같은 모양
  const buildLog = useCallback(() => {
    if (!result) return '';
    const bc = broadcasters.find((b) => b.id === selectedB);
    const head = [
      `# ${bc?.name || ''} 자막 검증 결과${fileName ? ` — ${fileName}` : ''}`,
      `# 자막 ${result.srt_entry_count}개 / 검증 항목 ${result.ran_count}개 / 오류 ${result.error_count}건 (자막 ${result.error_entry_count}개)`,
      '',
    ];
    const body = result.entries.filter((e) => e.errors.length > 0).flatMap((e) => [
      `[#${e.index}] ${e.timecode}`,
      ...e.text.split('\n').map((l) => `    ${l}`),
      ...e.errors.map((x) => `    → ${x.message}  [${x.rule_name}]` + (showFn ? `  (${x.function_name})` : '')),
      '',
    ]);
    return [...head, ...body].join('\n');
  }, [result, broadcasters, selectedB, fileName, showFn]);

  const handleCopyLog = () => {
    navigator.clipboard.writeText(buildLog()).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 2000);
    });
  };

  const shownEntries = useMemo(() => {
    if (!result) return [];
    let list = result.entries;
    if (filterRule) list = list.filter((e) => e.errors.some((x) => x.rule_id === filterRule));
    else if (onlyErrors) list = list.filter((e) => e.errors.length > 0);
    return list;
  }, [result, filterRule, onlyErrors]);

  const specChips = useMemo(() => {
    const p = result?.validation_params || params;
    if (!p) return [];
    return Object.entries(p)
      .map(([k, v]) => PARAM_LABEL[k]?.(v))
      .filter(Boolean);
  }, [result, params]);

  return (
    <div className="p-6 lg:p-8 h-full">
      <div className="flex h-full overflow-hidden bg-white rounded-xl border border-slate-200/70 shadow-sm">

        {/* ── 좌: 입력 ── */}
        <div className="w-[400px] border-r border-slate-200/70 flex flex-col shrink-0 min-h-0">
          <div className="px-5 py-4 border-b border-slate-100 shrink-0">
            <h3 className="text-base font-bold text-slate-800">검증</h3>
            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              작업이 끝난 자막이 방송사 규격에 맞는지만 확인합니다. 텍스트는 바꾸지 않습니다.
            </p>
          </div>

          {/* 고정 — 방송사 · 자막 파일 */}
          <div className="px-5 py-4 space-y-4 shrink-0 border-b border-slate-100">
            {/* 방송사 */}
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide mb-2 block">방송사</label>
              <select value={selectedB} onChange={(e) => setSelectedB(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500">
                {broadcasters.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
              {specChips.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {specChips.map((c) => (
                    <span key={c} className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">{c}</span>
                  ))}
                </div>
              )}
            </div>

            {/* SRT */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">자막 파일</label>
                <div className="flex gap-1.5">
                  <button onClick={() => { setSrtText(SAMPLE_SRT); setFileName(''); }}
                    className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded-lg hover:bg-indigo-50">예시</button>
                  {srtText && (
                    <button onClick={() => { setSrtText(''); setFileName(''); }}
                      className="text-[10px] font-bold text-slate-400 hover:text-red-500 px-2 py-1 rounded-lg hover:bg-red-50">초기화</button>
                  )}
                </div>
              </div>

              <button onClick={() => fileRef.current?.click()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 mb-1.5 rounded-xl border-2 border-dashed border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/40 transition-colors">
                <Upload size={15} />
                <span className="text-xs font-bold">{fileName || 'SRT 파일 선택'}</span>
              </button>
              <input ref={fileRef} type="file" accept=".srt,.txt" onChange={handleFile} className="hidden" />

              <textarea value={srtText} onChange={(e) => { setSrtText(e.target.value); setFileName(''); }}
                placeholder={`또는 여기에 붙여넣기\n\n1\n00:00:01,000 --> 00:00:03,000\n자막 텍스트`}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-500 resize-none h-20 leading-relaxed" />
            </div>

          </div>

          {/* 검증 항목 — 목록이 길어지면 이 영역만 스크롤한다 */}
          <div className="flex-1 min-h-0 flex flex-col">
            <div className="px-5 pt-3 pb-2 shrink-0 space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                  검증 항목 ({selected.length}/{pickerItems.length})
                </label>
                <div className="flex gap-1">
                  <button onClick={() => setSelected(pickerItems.map((i) => i.id))}
                    className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-1.5 py-1 rounded-lg hover:bg-slate-100">전체</button>
                  <button onClick={() => setSelected([])}
                    className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-1.5 py-1 rounded-lg hover:bg-slate-100">해제</button>
                  <button onClick={resetItems}
                    className="text-[10px] font-bold text-slate-400 hover:text-slate-600 px-1.5 py-1 rounded-lg hover:bg-slate-100 inline-flex items-center gap-1">
                    <RotateCcw size={10} /> 기본값
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button onClick={() => setShowFn(!showFn)}
                  title="검증 항목과 오류에 실제 함수명을 함께 표시합니다"
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold border transition-colors ${
                    showFn
                      ? 'bg-indigo-50 text-indigo-600 border-indigo-200'
                      : 'bg-white text-slate-400 border-slate-200 hover:text-slate-600'}`}>
                  <Code2 size={11} /> 함수명 {showFn ? '표기' : '숨김'}
                </button>
                <span className="text-[9px] text-slate-300 inline-flex items-center gap-1">
                  <Info size={10} /> 아이콘을 누르면 예시를 볼 수 있습니다
                </span>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto px-5 pb-2">
              <ItemPicker items={pickerItems} selected={selected} onToggle={toggle}
                extras={extras} onAddExtra={addExtra} showFn={showFn} vp={params} />
            </div>
            {dedupedCount > 0 && (
              <p className="text-[9px] text-slate-300 px-5 pb-2 shrink-0 leading-snug">
                1차·2차에 중복 등록된 공통 검증 {dedupedCount}건은 결과가 같아 하나로 합쳤습니다.
              </p>
            )}
          </div>

          <div className="p-4 border-t border-slate-100 shrink-0">
            <button onClick={handleRun} disabled={!srtText.trim() || selected.length === 0 || running}
              className="w-full py-3 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-40 disabled:pointer-events-none shadow-sm shadow-indigo-200/60 flex items-center justify-center gap-2">
              {running ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
              {running ? '검증 중...' : '검증 실행'}
            </button>
          </div>
        </div>

        {/* ── 우: 결과 ── */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-slate-50/50 overflow-hidden">
          {!result && !running && (
            <div className="flex-1 min-h-0 flex flex-col items-center justify-center text-slate-300">
              <div className="w-20 h-20 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <ShieldCheck size={32} className="text-slate-300" />
              </div>
              <p className="text-sm font-medium text-slate-400">SRT를 올리고 검증을 실행하세요</p>
              <p className="text-xs text-slate-300 mt-1">후처리 없이, 규격에 어긋난 자막만 짚어 줍니다</p>
            </div>
          )}

          {running && (
            <div className="flex-1 min-h-0 flex flex-col items-center justify-center">
              <Loader2 size={40} className="text-indigo-500 animate-spin mb-4" />
              <p className="text-sm font-bold text-slate-600">검증 중...</p>
              <p className="text-xs text-slate-400 mt-1">{selected.length}개 항목</p>
            </div>
          )}

          {result?.error && !running && (
            <div className="p-8 shrink-0">
              <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
                <AlertTriangle size={16} /> {result.error}
              </div>
            </div>
          )}

          {result && !result.error && !running && (
            <>
              {/* 요약 */}
              <div className="bg-white border-b border-slate-200/70 shrink-0">
                <div className="flex items-stretch flex-wrap">
                  <div className={`flex items-center gap-3 px-6 py-4 shrink-0 ${result.passed ? 'bg-emerald-50/60' : 'bg-red-50/60'}`}>
                    {result.passed
                      ? <CheckCircle2 size={28} className="text-emerald-500" />
                      : <XCircle size={28} className="text-red-500" />}
                    <div>
                      <p className={`text-base font-black leading-tight ${result.passed ? 'text-emerald-700' : 'text-red-700'}`}>
                        {result.passed ? '규격 통과' : '재작업 필요'}
                      </p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                        {broadcasters.find((b) => b.id === selectedB)?.name}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center divide-x divide-slate-100">
                    <Stat label="자막" value={result.srt_entry_count} unit="개" />
                    <Stat label="검증 항목" value={result.ran_count} unit="개" />
                    <Stat label="오류" value={result.error_count} unit="건" tone={result.error_count ? 'red' : 'emerald'} />
                    <Stat label="오류 자막" value={result.error_entry_count} unit="개" tone={result.error_entry_count ? 'red' : 'emerald'} />
                  </div>
                  <div className="ml-auto flex items-center pr-5">
                    {result.error_count > 0 && (
                      <Btn small variant="ghost" onClick={handleCopyLog}>
                        {copied ? <Check size={12} /> : <Copy size={12} />}{copied ? '복사됨' : '오류 로그 복사'}
                      </Btn>
                    )}
                  </div>
                </div>

                {/* 항목별 결과 — 클릭하면 해당 오류만 */}
                <div className="px-5 py-2.5 border-t border-slate-100 flex items-start gap-2 flex-wrap max-h-[88px] overflow-y-auto">
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide mr-1 mt-1.5">
                    <Filter size={11} /> 항목별
                  </span>
                  <button onClick={() => setFilterRule(null)}
                    className={`px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all ${
                      filterRule === null ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'}`}>
                    전체
                  </button>
                  {result.rules.map((r) => (
                    <RuleChip key={r.id} rule={r} active={filterRule === r.id} showFn={showFn}
                      onClick={() => setFilterRule(filterRule === r.id ? null : r.id)} />
                  ))}
                </div>
              </div>

              {/* 자막 목록 */}
              <div className="px-5 py-2.5 bg-white/60 border-b border-slate-200/70 flex items-center gap-3 shrink-0">
                <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-slate-500">
                  <AlignLeft size={12} /> 자막 {shownEntries.length}개
                  {filterRule && <span className="text-slate-400 font-medium">· {result.rules.find((r) => r.id === filterRule)?.name}</span>}
                </span>
                {!filterRule && (
                  <label className="ml-auto flex items-center gap-2 text-[11px] font-bold text-slate-500 cursor-pointer">
                    <input type="checkbox" checked={onlyErrors} onChange={(e) => setOnlyErrors(e.target.checked)}
                      className="w-3.5 h-3.5 rounded accent-indigo-600" />
                    오류만 보기
                  </label>
                )}
              </div>

              <div className="flex-1 min-h-0 overflow-y-auto">
                {shownEntries.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-300">
                    <CheckCircle2 size={40} className="text-emerald-300 mb-3" />
                    <p className="text-sm font-medium text-slate-400">해당하는 자막이 없습니다</p>
                  </div>
                ) : (
                  <div className="bg-white">
                    {shownEntries.map((e) => (
                      <EntryRow key={e.index} entry={e} maxLength={result.validation_params?.max_length}
                        filterRule={filterRule} showFn={showFn} />
                    ))}
                  </div>
                )}

                {result.unmatched_errors?.length > 0 && (
                  <div className="p-5">
                    <Card className="p-4">
                      <p className="text-[11px] font-bold text-amber-700 mb-2">자막 번호를 찾지 못한 오류 {result.unmatched_errors.length}건</p>
                      {result.unmatched_errors.map((e, i) => (
                        <p key={i} className="text-[11px] text-slate-600">#{e.index} — {e.message}</p>
                      ))}
                    </Card>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
