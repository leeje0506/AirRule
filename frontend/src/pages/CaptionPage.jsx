import { useRef, useState } from 'react';
import { Search, Loader2, Download, CheckCircle2, XCircle, HelpCircle, AlertTriangle } from 'lucide-react';
import { captionApi } from '../api/client';
import { makeZip, saveBlob } from '../utils/zip';
import { detectFormat, vttToSrt } from '../utils/vtt';
import { Card, Btn } from '../components/ui';

const SITES = [
  { id: 'kbs', label: 'KBS', extract: true },
  { id: 'mbc', label: 'MBC', extract: true },
  { id: 'sbs', label: 'SBS', extract: true },
  { id: 'jtbc', label: 'JTBC', extract: true },
  { id: 'tvchosun', label: 'TV조선', extract: true },
  { id: 'channela', label: '채널A', extract: true },
  { id: 'mbn', label: 'MBN', extract: true },
  { id: 'tving', label: 'TVING', extract: true },
  { id: 'wavve', label: '웨이브', extract: false },
  { id: 'coupang', label: '쿠팡플레이', extract: false },
];
const SITE_LABEL = Object.fromEntries(SITES.map((s) => [s.id, s.label]));

const errMsg = (e) => e?.response?.data?.detail || e?.message || '알 수 없는 오류';
const safe = (s) => String(s).replace(/[/\\:*?"<>|]/g, '_').trim();
const fileName = (title, ep, ext) =>
  `${safe(title)}_${ep.num != null ? String(ep.num).padStart(3, '0') : safe(ep.label)}.${ext}`;
const UP = (f) => (f ? f.toUpperCase() : '-');
const Badge19 = ({ text = '19' }) => (
  <span className="ml-2 align-middle text-[10px] font-black text-white bg-red-500 rounded-full px-1.5 py-0.5">{text}</span>
);

// 자막 받기: 직접 받기 되는 사이트(CDN 이 CORS 허용)는 브라우저가 바로 받아 버셀 함수 0회.
// 안 되는 사이트(MBN)나 직접 받기 실패분만 서버 경유 — 10화씩 묶어 호출 수를 줄인다.
async function fetchCaptions(source, eps, direct, onDone) {
  const got = new Map(); // key -> { text, ext } | { error }
  const queue = direct ? eps.filter((e) => e.url) : [];
  const viaServer = direct ? eps.filter((e) => !e.url) : [...eps];
  const worker = async () => {
    for (let ep = queue.shift(); ep; ep = queue.shift()) {
      try {
        const res = await fetch(ep.url);
        if (!res.ok) throw new Error(res.status);
        const text = await res.text();
        got.set(ep.key, { text, ext: detectFormat(text, ep.url) });
        onDone();
      } catch {
        viaServer.push(ep); // CORS·네트워크 실패 → 서버 경유
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(6, queue.length) }, worker));
  for (let k = 0; k < viaServer.length; k += 10) {
    const chunk = viaServer.slice(k, k + 10);
    try {
      for (const f of await captionApi.files(source, chunk.map((e) => e.key))) {
        got.set(f.key, f.error ? { error: f.error } : { text: f.text, ext: f.ext });
        onDone();
      }
    } catch (e) {
      chunk.forEach((ep) => { got.set(ep.key, { error: errMsg(e) }); onDone(); });
    }
  }
  return got;
}

// 주소로 받기 — F12 등에서 찾은 자막 파일 주소를 브라우저가 직접 받아 원본/SRT 로 저장.
// 기본은 서버를 거치지 않는다. 브라우저 직접 받기를 막은 경우만 서버가 대신 받는데,
// 지원 사이트의 자막 호스트만 허용(임의 주소 대리 요청은 남용 위험).
function UrlDownload() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState(null); // { ok, lines: [] }

  async function run(fmt) {
    const urls = text.split(/\s+/).filter((u) => /^https?:\/\//.test(u));
    if (!urls.length) { setMsg({ ok: false, lines: ['자막 파일 주소를 넣어 주세요 (http 로 시작, 여러 개면 줄바꿈)'] }); return; }
    setBusy(fmt); setMsg(null);
    const files = [];
    const failed = [];
    const got = new Array(urls.length); // i -> { text, ext } | { error }
    const viaServer = [];
    await Promise.all(urls.map(async (u, i) => {
      try {
        const res = await fetch(u);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = await res.text();
        got[i] = { text: body, ext: detectFormat(body, u) };
      } catch (e) {
        if (e instanceof TypeError) viaServer.push(i); // CORS 로 막힘 → 서버 경유(지원 사이트 자막 주소만)
        else got[i] = { error: e.message };
      }
    }));
    for (let k = 0; k < viaServer.length; k += 10) {
      const chunk = viaServer.slice(k, k + 10);
      try {
        const res = await captionApi.fetchUrls(chunk.map((i) => urls[i]));
        res.forEach((f, j) => { got[chunk[j]] = f.error ? { error: f.error } : { text: f.text, ext: f.ext }; });
      } catch (e) {
        chunk.forEach((i) => { got[i] = { error: errMsg(e) }; });
      }
    }
    got.forEach((r, i) => {
      if (r.error) { failed.push(`${i + 1}번 주소 — ${r.error}`); return; }
      let { text: body, ext } = r;
      if (fmt === 'srt' && ext === 'vtt') [body, ext] = [vttToSrt(body), 'srt'];
      else if (fmt === 'srt' && ext !== 'srt') { failed.push(`${i + 1}번 주소 — ${UP(ext)} 형식은 SRT 변환을 지원하지 않습니다`); return; }
      const base = decodeURIComponent(new URL(urls[i]).pathname.split('/').pop() || '').replace(/\.\w+$/, '') || `자막_${i + 1}`;
      files.push({ name: `${safe(base)}.${ext}`, text: body, i });
    });
    setBusy('');
    files.sort((a, b) => a.i - b.i);
    const seen = {};
    for (const f of files) { // 같은 파일 이름 겹치면 _2, _3
      seen[f.name] = (seen[f.name] || 0) + 1;
      if (seen[f.name] > 1) f.name = f.name.replace(/(\.\w+)$/, `_${seen[f.name]}$1`);
    }
    if (files.length === 1) saveBlob(new Blob([files[0].text], { type: 'text/plain' }), files[0].name);
    else if (files.length) saveBlob(makeZip(files), `자막_주소받기_${fmt === 'srt' ? 'SRT' : '원본'}.zip`);
    setMsg({ ok: !failed.length, lines: [`받음 ${files.length}/${urls.length}`, ...failed] });
  }

  return (
    <details className="group">
      <summary className="cursor-pointer text-xs font-bold text-slate-500 hover:text-slate-700 select-none">
        주소로 받기 — F12 에서 찾은 자막 파일 주소로 직접 받기
      </summary>
      <div className="mt-3 space-y-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder={'https://…/subtitle_….vtt\n여러 개면 한 줄에 하나씩'}
          className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
        <div className="flex items-center gap-2 flex-wrap">
          {[['original', '원본으로 받기'], ['srt', 'SRT로 받기']].map(([f, label]) => (
            <Btn key={f} onClick={() => run(f)} disabled={!!busy} variant={f === 'srt' ? 'accent' : 'primary'} small>
              {busy === f ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />} {label}
            </Btn>
          ))}
          <span className="text-[11px] text-slate-400">브라우저가 바로 받고, 막힌 경우만 서버가 대신 받습니다(지원 사이트 자막 주소만).</span>
        </div>
        {msg && (
          <div className={`text-xs rounded-xl px-4 py-2.5 space-y-0.5 ${msg.ok ? 'bg-slate-50 text-slate-600' : 'bg-red-50 text-red-600'}`}>
            {msg.lines.map((l) => <p key={l}>{l}</p>)}
          </div>
        )}
      </div>
    </details>
  );
}

export default function CaptionPage() {
  const [source, setSource] = useState('all');
  const [q, setQ] = useState('');
  const [results, setResults] = useState(null); // [{ source, id, title, exact }]
  const [siteErrors, setSiteErrors] = useState([]);
  const [program, setProgram] = useState(null);
  const [data, setData] = useState(null); // { episodes, downloadable }
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(null); // { done, total, failed: [] }
  const [picked, setPicked] = useState(new Set()); // 체크한 회차 key — 비어 있으면 전체
  const epCache = useRef(new Map()); // 같은 프로그램 다시 고르면 서버 안 부름

  const reset = () => {
    setResults(null); setSiteErrors([]); setProgram(null); setData(null);
    setError(''); setProgress(null); setPicked(new Set());
  };

  async function pick(p) {
    setProgram(p); setData(null); setProgress(null); setError(''); setPicked(new Set()); setBusy('episodes');
    try {
      const k = `${p.source}:${p.id}`;
      if (!epCache.current.has(k)) epCache.current.set(k, await captionApi.episodes(p.source, p.id));
      setData(epCache.current.get(k));
    } catch (e) {
      setError(`회차 목록을 못 가져왔습니다 — ${errMsg(e)}`);
    } finally {
      setBusy('');
    }
  }

  async function search() {
    if (!q.trim()) { setError('프로그램명을 입력하세요'); return; }
    reset(); setBusy('search');
    let found = [];
    try {
      // 통합 검색도 서버 한 번 — 서버가 사이트별로 동시에 찾고, 실패한 사이트는 errors 로 따로 준다
      const { results, errors } = await captionApi.search(source, q);
      found = results;
      setResults(results);
      setSiteErrors(errors.map((e) => `${SITE_LABEL[e.source]} 검색 실패 — ${e.detail}`));
    } catch (e) {
      setError(`검색 실패 — ${errMsg(e)}`);
    }
    setBusy('');
    const exact = found.filter((r) => r.exact);
    if (exact.length === 1) await pick(exact[0]);
  }

  async function download(eps, fmt) {
    let done = 0;
    setProgress({ done: 0, total: eps.length, failed: [] });
    setBusy(`download-${fmt}`);
    const got = await fetchCaptions(program.source, eps, data.direct, () => {
      done += 1;
      setProgress((p) => ({ ...p, done }));
    });
    setBusy('');
    const files = [];
    const failed = [];
    for (const ep of eps) {
      const r = got.get(ep.key) || { error: '받지 못함' };
      let { text, ext } = r;
      if (!r.error && fmt === 'srt' && ext === 'vtt') [text, ext] = [vttToSrt(text), 'srt'];
      if (r.error) failed.push(`${ep.label}: ${r.error}`);
      else if (fmt === 'srt' && ext !== 'srt') failed.push(`${ep.label}: ${UP(ext)} 형식은 SRT 변환을 지원하지 않습니다`);
      else files.push({ name: fileName(program.title, ep, ext), text });
    }
    setProgress({ done: eps.length, total: eps.length, failed });
    if (!files.length) { setError('받은 자막이 없습니다'); return; }
    files.sort((a, b) => a.name.localeCompare(b.name));
    if (files.length === 1) saveBlob(new Blob([files[0].text], { type: 'text/plain' }), files[0].name);
    else saveBlob(makeZip(files), `${safe(program.title)}_자막_${fmt === 'srt' ? 'SRT' : '원본'}.zip`);
  }

  const hasExact = (site) => (results || []).some((r) => r.source === site && r.exact);
  const eps = data?.episodes || [];
  const capCount = eps.filter((e) => e.caption).length;
  const unknown = eps.filter((e) => e.caption == null).length;
  const adult = eps.some((e) => e.note?.startsWith('19세'));
  const withCap = eps.filter((e) => e.caption && (e.url || e.key)); // 실제로 받을 수 있는 회차
  const lastCap = eps.filter((e) => e.caption).reduce((m, e) => (e.num != null && e.num > (m ?? -1) ? e.num : m), null);
  const chosen = withCap.filter((e) => picked.has(e.key));
  const target = chosen.length ? chosen : withCap;
  const toggle = (key) => setPicked((s) => { const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n; });
  const allPicked = withCap.length > 0 && chosen.length === withCap.length;
  const origFormats = [...new Set(withCap.map((e) => e.format).filter(Boolean))];
  // 다운로드 버튼: 원본 형식(SRT 아닌 것)은 그대로, SRT 는 항상 (원본이 VTT 면 변환)
  const FORMATS = [
    ...origFormats.filter((f) => f !== 'srt').map((f) => ({ fmt: 'original', label: UP(f) })),
    { fmt: 'srt', label: 'SRT' },
  ];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-black text-slate-800">프로그램 찾기</h2>
        <p className="text-sm text-slate-500 mt-1">방송사 다시보기에서 프로그램을 찾아 회차별 자막 유무·원본 형식을 보고, 원본(VTT) 또는 SRT 로 내려받습니다.</p>
      </div>

      <Card className="p-6 space-y-4">
        <div className="flex gap-2">
          <select
            value={source}
            onChange={(e) => { setSource(e.target.value); reset(); }}
            className="px-3 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="all">전체 사이트 (통합 검색)</option>
            <optgroup label="자막 추출 가능">
              {SITES.filter((x) => x.extract).map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
            </optgroup>
            <optgroup label="자막 유무만 확인">
              {SITES.filter((x) => !x.extract).map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
            </optgroup>
          </select>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !busy && search()}
            placeholder="프로그램명 (예: 궁, 부부의 세계)"
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
          <Btn onClick={search} disabled={!!busy} variant="accent">
            {busy === 'search' ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} 찾기
          </Btn>
        </div>
        {[error, ...siteErrors].filter(Boolean).map((m) => (
          <p key={m} className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-xl px-4 py-2.5">
            <AlertTriangle size={14} /> {m}
          </p>
        ))}
        <UrlDownload />
      </Card>

      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 items-start">
          {/* 결과가 많아도 페이지를 내리지 않게 — 목록은 자기 영역에서만 스크롤, 상세는 옆에 */}
          <Card className="p-4 lg:sticky lg:top-4 max-h-[calc(100vh-330px)] overflow-y-auto space-y-4">
            {results.length === 0 && <p className="text-sm text-slate-500 p-2">'{q}' 로 찾은 프로그램이 없습니다.</p>}
            {/* 딱 맞는 프로그램(✓)이 있는 사이트를 위로 — 나머지는 원래 순서 */}
            {[...SITES].sort((x, y) => hasExact(y.id) - hasExact(x.id)).map((site) => {
              const list = results.filter((r) => r.source === site.id);
              if (!list.length) return null;
              return (
                <div key={site.id}>
                  <p className="text-[11px] font-bold text-slate-400 mb-1.5 px-2">
                    {site.label} · {list.length}건{!site.extract && ' · 유무만'}
                  </p>
                  {list.map((r) => {
                    const on = program?.source === r.source && program?.id === r.id;
                    return (
                      <button
                        key={r.id}
                        onClick={() => pick(r)}
                        disabled={!!busy}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors disabled:opacity-60 ${
                          on ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        {r.title}{r.exact && <span className={on ? 'text-emerald-300' : 'text-emerald-500'}> ✓</span>}
                      </button>
                    );
                  })}
                </div>
              );
            })}
            {source === 'all' && results.length > 0 && (
              <p className="text-[11px] text-slate-400 px-2">
                결과 없음: {SITES.filter((x) => !results.some((r) => r.source === x.id)).map((x) => x.label).join(', ') || '-'}
              </p>
            )}
          </Card>
          <div className="min-w-0">
          {program ? (
        <Card className="p-6 space-y-4">
          {busy === 'episodes' ? (
            <p className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 size={14} className="animate-spin" /> {SITE_LABEL[program.source]} · {program.title} 회차·자막 확인 중… (일부 사이트는 회차마다 확인해서 회차가 많으면 수십 초)
            </p>
          ) : data && (
            <>
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 rounded-md px-2 py-0.5 mr-2 align-middle">{SITE_LABEL[program.source]}</span>
                    {program.title}
                    {adult && <Badge19 text="19세 회차 포함" />}
                  </h3>
                  <p className="text-sm text-slate-600 mt-1">
                    총 {eps.length}화 · 자막 있음 <b>{capCount}화</b>
                    {data.downloadable && capCount !== withCap.length && <> (받기 가능 <b>{withCap.length}화</b>)</>}
                    {unknown > 0 && <> · 확인 불가 <b>{unknown}화</b></>}
                    {lastCap != null && <> · 자막 있는 마지막 회차 <b>{lastCap}화</b></>}
                    {origFormats.length > 0 && <> · 원본 형식 <b>{origFormats.map(UP).join(', ')}</b></>}
                  </p>
                </div>
                {data.downloadable ? (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-slate-500">
                      {chosen.length ? `선택한 ${chosen.length}화` : `전체 ${withCap.length}화`}
                    </span>
                    {chosen.length > 0 && (
                      <Btn onClick={() => setPicked(new Set())} variant="ghost" small>선택 해제</Btn>
                    )}
                    {FORMATS.map((f) => (
                      <Btn
                        key={f.fmt}
                        onClick={() => download(target, f.fmt)}
                        disabled={!!busy || !withCap.length}
                        variant={f.fmt === 'srt' ? 'accent' : 'primary'}
                      >
                        {busy === `download-${f.fmt}` ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                        {f.label}로 다운로드
                      </Btn>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 bg-slate-100 rounded-xl px-3 py-2">
                    이 사이트는 자막 유무만 확인됩니다 (자막 파일은 로그인·DRM 영역이라 추출 안 함)
                  </p>
                )}
              </div>
              {data.limited && (
                <p className="flex items-center gap-2 text-xs text-slate-600 bg-slate-100 rounded-xl px-4 py-2.5">
                  <AlertTriangle size={14} /> 회차가 많아 최근 {data.limited}건까지만 표시합니다.
                </p>
              )}
              {adult && (
                <p className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded-xl px-4 py-2.5">
                  <AlertTriangle size={14} /> 19세 회차는 로그인이 필요해 자막 유무를 확인할 수 없습니다 (? 표시). 필요하면 JTBC 사이트에서 직접 확인하세요.
                </p>
              )}
              {data.downloadable && !withCap.length && <p className="text-sm text-slate-500">추출할 수 있는 자막이 없습니다.</p>}
              {progress && (
                <div className="text-xs text-slate-600 bg-slate-50 rounded-xl px-4 py-2.5 space-y-1">
                  <p>추출 {progress.done}/{progress.total}{progress.done === progress.total && ' — 완료'}</p>
                  {progress.failed.map((f) => <p key={f} className="text-red-600">실패 · {f}</p>)}
                </div>
              )}
              <div className="max-h-[420px] overflow-y-auto border border-slate-100 rounded-xl">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-[11px] text-slate-400 sticky top-0">
                    <tr>
                      {data.downloadable && (
                        <th className="w-10 pl-4">
                          <input
                            type="checkbox"
                            checked={allPicked}
                            disabled={!withCap.length}
                            onChange={() => setPicked(allPicked ? new Set() : new Set(withCap.map((e) => e.key)))}
                            title="자막 있는 회차 전체 선택"
                          />
                        </th>
                      )}
                      <th className="text-left px-4 py-2">회차</th>
                      <th className="w-16">자막</th>
                      <th className="w-20">원본 형식</th>
                      <th className="w-28">받기</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eps.map((e, idx) => (
                      <tr key={`${e.key}-${idx}`} className={`border-t border-slate-100 ${picked.has(e.key) ? 'bg-indigo-50/60' : ''}`}>
                        {data.downloadable && (
                          <td className="pl-4">
                            {e.caption && (e.url || e.key) && <input type="checkbox" checked={picked.has(e.key)} onChange={() => toggle(e.key)} />}
                          </td>
                        )}
                        <td className="px-4 py-2 text-slate-700">
                          {e.label}
                          {e.note?.startsWith('19세') && <Badge19 />}
                        </td>
                        <td className="text-center">
                          {e.caption === true && <CheckCircle2 size={15} className="inline text-emerald-500" />}
                          {e.caption === false && <XCircle size={15} className="inline text-slate-300" />}
                          {e.caption == null && <HelpCircle size={15} className="inline text-amber-400" title="확인 실패" />}
                        </td>
                        <td className="text-center text-xs text-slate-500">{e.caption ? UP(e.format) : ''}</td>
                        <td className="text-center space-x-2">
                          {e.note && <span className="text-[11px] text-slate-400">{e.note.replace(/^19세 — /, '')}</span>}
                          {data.downloadable && e.caption && (e.url || e.key) && [
                            ...(e.format && e.format !== 'srt' ? [{ fmt: 'original', label: UP(e.format) }] : []),
                            { fmt: 'srt', label: 'SRT' },
                          ].map((f) => (
                            <button
                              key={f.fmt}
                              onClick={() => download([e], f.fmt)}
                              disabled={!!busy}
                              className="text-xs text-indigo-600 hover:underline disabled:opacity-40"
                            >
                              {f.label}
                            </button>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>
      ) : (
            <Card className="p-10 text-center text-sm text-slate-400">왼쪽 검색 결과에서 프로그램을 고르세요</Card>
          )}
          </div>
        </div>
      )}
    </div>
  );
}
