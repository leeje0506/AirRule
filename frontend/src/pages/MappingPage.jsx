import { useState, useEffect, useMemo } from 'react';
import { GitBranch, Link2, FileText, Code2, Pencil, X, Info, Wand2, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { policyApi, techItemApi, linkApi } from '../api/client';
import { Card, Btn } from '../components/ui';

export default function MappingPage() {
  const { canEditTech } = useAuth();
  const [categories, setCategories] = useState([]);
  const [techItems, setTechItems] = useState([]);
  const [links, setLinks] = useState([]);
  const [selected, setSelected] = useState(null); // { side:'policy'|'tech', id }
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

  const connectedTechSet = useMemo(
    () => (selected?.side === 'policy' ? new Set(techIdsForPolicy(selected.id)) : new Set()),
    [selected, links]
  );
  const connectedPolicySet = useMemo(
    () => (selected?.side === 'tech' ? new Set(policyIdsForTech(selected.id)) : new Set()),
    [selected, links]
  );

  const toggleLink = async (pid, tid) => {
    const existing = linkMap[`${pid}|${tid}`];
    if (existing) await linkApi.remove(existing);
    else await linkApi.create({ policy_item_id: pid, tech_item_id: tid, note: '' });
    setLinks(await linkApi.all());
  };

  const clickPolicy = async (pid) => {
    if (editMode && selected?.side === 'tech') { await toggleLink(pid, selected.id); return; }
    setSelected((s) => (s?.side === 'policy' && s.id === pid ? null : { side: 'policy', id: pid }));
  };
  const clickTech = async (tid) => {
    if (editMode && selected?.side === 'policy') { await toggleLink(selected.id, tid); return; }
    setSelected((s) => (s?.side === 'tech' && s.id === tid ? null : { side: 'tech', id: tid }));
  };

  // 보기 모드에서 상대편은 "연결된 것만". 편집 모드에서는 전체 노출(추가하려고).
  const techFilterToConnected = selected?.side === 'policy' && !editMode;
  const policyFilterToConnected = selected?.side === 'tech' && !editMode;

  const typeBadge = (t) => (
    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${
      t === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
    }`}>{t === 'processing' ? '후처리' : '검증'}</span>
  );

  // ── 기술 항목 한 줄 ──
  const TechRow = ({ t }) => {
    const isSel = selected?.side === 'tech' && selected.id === t.id;
    const isConn = selected?.side === 'policy' && connectedTechSet.has(t.id);
    const n = countPolicy(t.id);
    return (
      <button onClick={() => clickTech(t.id)}
        className={`w-full flex items-center justify-between text-left px-3 py-2 rounded-lg border transition-all ${
          isSel ? 'border-purple-500 bg-purple-50' : isConn ? 'border-indigo-300 bg-indigo-50/40' : 'border-slate-150 bg-white hover:bg-slate-50'
        }`}>
        <div className="min-w-0">
          <span className="text-[13px] font-medium text-slate-700 truncate block">{t.name}</span>
          {t.function_name && <span className="text-[10px] text-indigo-400 font-mono truncate block">{t.function_name}()</span>}
        </div>
        {n > 0 && <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 shrink-0 ml-2"><Link2 size={11} /> {n}</span>}
      </button>
    );
  };

  // ── 기술 패널: 후처리/검증 분리 ──
  const TechGroup = ({ kind, items }) => {
    const isProc = kind === 'processing';
    const Icon = isProc ? Wand2 : ShieldCheck;
    return (
      <div className="mb-3">
        <div className="flex items-center gap-1.5 px-1 mb-1.5">
          <Icon size={12} className={isProc ? 'text-emerald-600' : 'text-purple-600'} />
          <span className={`text-[10px] font-bold uppercase tracking-wide ${isProc ? 'text-emerald-700' : 'text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
          <span className="text-[10px] font-bold text-slate-400">{items.length}</span>
        </div>
        {items.length === 0 ? (
          <p className="text-[11px] text-slate-300 px-1 py-1">해당 없음</p>
        ) : (
          <div className="space-y-1">{items.map((t) => <TechRow key={t.id} t={t} />)}</div>
        )}
      </div>
    );
  };

  const visibleTech = techFilterToConnected ? techItems.filter((t) => connectedTechSet.has(t.id)) : techItems;
  const techProc = visibleTech.filter((t) => t.type === 'processing');
  const techValid = visibleTech.filter((t) => t.type === 'validation');

  // ── 정책 패널 ──
  const PolicyRow = ({ item }) => {
    const isSel = selected?.side === 'policy' && selected.id === item.id;
    const isConn = selected?.side === 'tech' && connectedPolicySet.has(item.id);
    const n = countTech(item.id);
    return (
      <button onClick={() => clickPolicy(item.id)}
        className={`w-full flex items-center justify-between text-left px-3 py-2 rounded-lg border transition-all ${
          isSel ? 'border-blue-500 bg-blue-50' : isConn ? 'border-indigo-300 bg-indigo-50/40' : 'border-slate-150 bg-white hover:bg-slate-50'
        }`}>
        <span className="text-[13px] font-medium text-slate-700">{item.name}</span>
        {n > 0 && <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 shrink-0"><Link2 size={11} /> {n}</span>}
      </button>
    );
  };

  const visibleCategories = useMemo(() => {
    if (!policyFilterToConnected) return categories;
    return categories
      .map((c) => ({ ...c, items: c.items.filter((i) => connectedPolicySet.has(i.id)) }))
      .filter((c) => c.items.length > 0);
  }, [categories, policyFilterToConnected, connectedPolicySet]);

  // ── 상세: 선택 항목의 연결 상대 ──
  const detail = useMemo(() => {
    if (!selected) return null;
    if (selected.side === 'policy') {
      const p = policyItemById[selected.id]; if (!p) return null;
      const techs = techIdsForPolicy(selected.id).map((id) => techById[id]).filter(Boolean);
      return { kind: 'policy', title: p.name, sub: p._cat, desc: p.description,
        proc: techs.filter((t) => t.type === 'processing'), valid: techs.filter((t) => t.type === 'validation') };
    }
    const t = techById[selected.id]; if (!t) return null;
    const pols = policyIdsForTech(selected.id).map((id) => policyItemById[id]).filter(Boolean);
    const byCat = {};
    pols.forEach((p) => { (byCat[p._cat] = byCat[p._cat] || []).push(p); });
    return { kind: 'tech', title: t.name, sub: t.function_name ? `${t.function_name}()` : '', desc: t.desc, type: t.type, byCat };
  }, [selected, links, techById, policyItemById]);

  return (
    <div className="p-8 lg:p-10">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">정책 ↔ 기술 연결 찾기</h2>
          <p className="text-sm text-slate-400 mt-1">한쪽 항목을 누르면 반대쪽에 연결된 항목만 모아서 보여줍니다.</p>
        </div>
        {canEditTech && (
          <Btn variant={editMode ? 'accent' : 'primary'} onClick={() => setEditMode((v) => !v)}>
            <Pencil size={14} /> {editMode ? '편집 종료' : '연결 편집'}
          </Btn>
        )}
      </div>

      {editMode && (
        <div className="mb-4 flex items-center gap-2 px-4 py-2.5 bg-indigo-50 border border-indigo-100 rounded-xl">
          <Info size={14} className="text-indigo-500 shrink-0" />
          <p className="text-xs text-indigo-700 font-medium">
            {selected ? `${selected.side === 'policy' ? '정책' : '기술'} 항목 선택됨 — 반대쪽 항목을 눌러 연결/해제` : '한쪽 항목을 먼저 선택하세요. (편집 모드에서는 전체 항목이 보입니다)'}
          </p>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-400 py-12 text-center">불러오는 중...</p>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* 정책 항목 */}
            <Card>
              <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={14} className="text-blue-500" />
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">정책 항목</span>
                </div>
                {policyFilterToConnected && <span className="text-[10px] font-bold text-indigo-500">연결된 항목만</span>}
              </div>
              <div className="max-h-[60vh] overflow-y-auto p-3 space-y-4">
                {visibleCategories.length === 0 ? (
                  <p className="text-xs text-slate-300 text-center py-6">연결된 정책 항목이 없습니다</p>
                ) : visibleCategories.map((cat) => (
                  <div key={cat.id}>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 mb-1.5">{cat.name}</p>
                    <div className="space-y-1">{cat.items.map((item) => <PolicyRow key={item.id} item={item} />)}</div>
                  </div>
                ))}
              </div>
            </Card>

            {/* 기술 항목 (후처리/검증 분리) */}
            <Card>
              <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 size={14} className="text-purple-500" />
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">후처리 · 검증 항목</span>
                </div>
                {techFilterToConnected && <span className="text-[10px] font-bold text-indigo-500">연결된 항목만</span>}
              </div>
              <div className="max-h-[60vh] overflow-y-auto p-3">
                {visibleTech.length === 0 ? (
                  <p className="text-xs text-slate-300 text-center py-6">연결된 기술 항목이 없습니다</p>
                ) : (
                  <>
                    <TechGroup kind="processing" items={techProc} />
                    <TechGroup kind="validation" items={techValid} />
                  </>
                )}
              </div>
            </Card>
          </div>

          {/* 상세 */}
          {detail ? (
            <Card className="mt-4">
              <div className="px-6 py-4 border-b border-slate-100">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                    detail.kind === 'policy' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                  }`}>{detail.kind === 'policy' ? '정책 항목' : '기술 항목'}</span>
                  <h4 className="text-sm font-bold text-slate-800">{detail.title}</h4>
                  {detail.sub && <span className="text-[11px] text-slate-400 font-mono">{detail.sub}</span>}
                </div>
                {detail.desc && <p className="text-[11px] text-slate-400 mt-1">{detail.desc}</p>}
              </div>

              <div className="p-6 space-y-5">
                {detail.kind === 'policy' ? (
                  <>
                    <DetailGroup kind="processing" items={detail.proc} editMode={editMode}
                      onUnlink={(t) => toggleLink(selected.id, t.id)} typeBadge={typeBadge} />
                    <DetailGroup kind="validation" items={detail.valid} editMode={editMode}
                      onUnlink={(t) => toggleLink(selected.id, t.id)} typeBadge={typeBadge} />
                  </>
                ) : (
                  <div>
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-3">연결된 정책 항목</p>
                    {Object.keys(detail.byCat).length === 0 ? (
                      <p className="text-xs text-slate-400">연결된 항목이 없습니다.{canEditTech ? " '연결 편집'에서 추가할 수 있어요." : ''}</p>
                    ) : (
                      <div className="space-y-3">
                        {Object.entries(detail.byCat).map(([cat, items]) => (
                          <div key={cat}>
                            <p className="text-[10px] font-bold text-slate-400 mb-1.5">{cat}</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {items.map((p) => (
                                <div key={p.id} className="flex items-center justify-between gap-2 px-3 py-2 bg-slate-50 rounded-lg border border-slate-100">
                                  <span className="text-[12px] font-medium text-slate-700">{p.name}</span>
                                  {editMode && <button onClick={() => toggleLink(p.id, selected.id)} className="p-1 text-slate-300 hover:text-red-500 rounded shrink-0" title="연결 해제"><X size={13} /></button>}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <div className="mt-4 flex items-center justify-center gap-2 py-8 text-slate-300 border-2 border-dashed border-slate-200 rounded-2xl">
              <GitBranch size={18} />
              <p className="text-sm">정책 항목이나 기술 항목을 눌러 연결을 확인하세요</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── 상세 내 후처리/검증 그룹 ──
function DetailGroup({ kind, items, editMode, onUnlink, typeBadge }) {
  const isProc = kind === 'processing';
  const Icon = isProc ? Wand2 : ShieldCheck;
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={13} className={isProc ? 'text-emerald-600' : 'text-purple-600'} />
        <span className={`text-[11px] font-bold uppercase tracking-wide ${isProc ? 'text-emerald-700' : 'text-purple-700'}`}>{isProc ? '후처리' : '검증'}</span>
        <span className="text-[10px] font-bold text-slate-400">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-[11px] text-slate-300 pl-1">연결된 {isProc ? '후처리' : '검증'} 없음</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {items.map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-2 px-3 py-2 bg-slate-50 rounded-lg border border-slate-100">
              <div className="min-w-0">
                <span className="text-[12px] font-medium text-slate-700 truncate block">{t.name}</span>
                {t.function_name && <span className="text-[10px] text-indigo-400 font-mono truncate block">{t.function_name}()</span>}
              </div>
              {editMode && <button onClick={() => onUnlink(t)} className="p-1 text-slate-300 hover:text-red-500 rounded shrink-0" title="연결 해제"><X size={13} /></button>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}