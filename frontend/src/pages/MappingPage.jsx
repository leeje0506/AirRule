import { useState, useEffect } from 'react';
import { Check, Edit3, Save, GitBranch, CheckCircle2, FileText, AlertCircle } from 'lucide-react';
import { broadcasterApi, policyApi, techItemApi, mappingApi } from '../api/client';
import { Card, Btn, Pill, EmptyState } from '../components/ui';

export default function MappingPage() {
  const [broadcasters, setBroadcasters] = useState([]);
  const [selectedB, setSelectedB] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [allItems, setAllItems] = useState([]);
  const [mappedItems, setMappedItems] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);

  useEffect(() => {
    Promise.all([broadcasterApi.list(), policyApi.list(), techItemApi.list()])
      .then(([b, p, t]) => {
        setBroadcasters(b);
        setPolicies(p);
        setAllItems(t);
        if (b.length > 0) setSelectedB(b[0]);
      });
  }, []);

  useEffect(() => {
    if (selectedB) {
      mappingApi.get(selectedB.id).then((data) => {
        setMappedItems(data.items || []);
        setSelectedIds((data.items || []).map((i) => i.id));
      });
    }
  }, [selectedB]);

  const bPolicy = policies.find((p) => p.broadcaster_id === selectedB?.id);

  const toggleItem = (id) => {
    setSelectedIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const saveMapping = async () => {
    await mappingApi.update(selectedB.id, selectedIds);
    const data = await mappingApi.get(selectedB.id);
    setMappedItems(data.items || []);
    setEditMode(false);
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar */}
      <div className="w-72 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-xs font-black text-slate-800 uppercase tracking-widest">방송사 선택</h3>
          <p className="text-[11px] text-slate-400 mt-1">정책을 확인하려는 채널을 선택하세요.</p>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {broadcasters.map((b) => {
            const isActive = selectedB?.id === b.id;
            return (
              <button key={b.id} onClick={() => { setSelectedB(b); setEditMode(false); }}
                className={`w-full flex items-center justify-between p-3.5 rounded-xl border-2 transition-all ${
                  isActive ? 'border-indigo-600 bg-indigo-50/40 shadow-sm' : 'border-transparent bg-slate-50 hover:bg-white hover:border-slate-200'
                }`}>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-black text-[11px] shadow-sm" style={{ background: b.color }}>
                    {b.name[0]}
                  </div>
                  <div className="text-left">
                    <p className={`text-sm font-bold ${isActive ? 'text-indigo-900' : 'text-slate-700'}`}>{b.name}</p>
                  </div>
                </div>
                {isActive && <Check className="text-indigo-600" size={16} />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        <div className="p-8 border-b border-slate-100 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-white text-lg font-black shadow-lg" style={{ background: selectedB?.color || '#6366f1' }}>
              {selectedB?.name?.[0] || '?'}
            </div>
            <div>
              <h3 className="text-xl font-bold text-slate-800">{selectedB?.name || ''} 매핑 매트릭스</h3>
              <p className="text-sm text-slate-400">연결된 후처리/검증 항목 및 정책을 확인합니다.</p>
            </div>
          </div>
          <div className="flex gap-2">
            {editMode ? (
              <>
                <Btn variant="ghost" onClick={() => { setEditMode(false); setSelectedIds(mappedItems.map((i) => i.id)); }}>취소</Btn>
                <Btn variant="accent" onClick={saveMapping}><Save size={14} /> 저장</Btn>
              </>
            ) : (
              <Btn variant="primary" onClick={() => setEditMode(true)}><Edit3 size={14} /> 매핑 편집</Btn>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* Policy summary */}
          {bPolicy && (
            <Card>
              <div className="px-6 py-4 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={15} className="text-slate-400" />
                  <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">연결된 정책</span>
                </div>
                <Pill type={bPolicy.status} kind="status" />
              </div>
              <div className="p-6">
                <h4 className="text-sm font-bold text-slate-800 mb-1">{bPolicy.title}</h4>
                <p className="text-[11px] text-slate-400 font-mono">{bPolicy.version} · 마지막 수정 {bPolicy.updated_at?.slice(0, 10)}</p>
                {bPolicy.rules?.specs && (
                  <div className="mt-3 inline-block text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-lg border border-indigo-100">
                    규격: {bPolicy.rules.specs}
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Items */}
          <div>
            <h4 className="text-xs font-black text-slate-500 uppercase tracking-wide mb-4">
              {editMode ? '항목 선택 (체크하여 매핑)' : '매핑된 후처리/검증 항목'}
            </h4>

            {editMode ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {allItems.map((item) => {
                  const checked = selectedIds.includes(item.id);
                  return (
                    <div key={item.id} onClick={() => toggleItem(item.id)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${checked ? 'border-indigo-500 bg-indigo-50/30' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${checked ? 'bg-indigo-600 border-indigo-600' : 'border-slate-300'}`}>
                            {checked && <Check size={12} className="text-white" />}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-800">{item.name}</p>
                            <p className="text-[11px] text-slate-400 mt-0.5">{item.desc}</p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                            item.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                          }`}>
                            {item.type === 'processing' ? '후처리' : '검증'}
                          </span>
                          <Pill type={item.tag} kind="tag" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Card>
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-100 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                      <th className="px-5 py-3 w-20">분류</th>
                      <th className="px-5 py-3">항목명</th>
                      <th className="px-5 py-3">파라미터</th>
                      <th className="px-5 py-3 text-center">태그</th>
                      <th className="px-5 py-3 text-center">검증</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100/80">
                    {mappedItems.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-5 py-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                            item.type === 'processing' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                          }`}>
                            {item.type === 'processing' ? '후처리' : '검증'}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <p className="text-sm font-bold text-slate-800">{item.name}</p>
                          <p className="text-[10px] text-slate-400">{item.desc}</p>
                        </td>
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(item.params || {}).map(([k, v]) => (
                              <div key={k} className="flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                <span className="text-[9px] font-mono text-slate-400 uppercase">{k}</span>
                                <span className="text-[9px] font-mono font-bold text-indigo-600">{v}</span>
                              </div>
                            ))}
                          </div>
                        </td>
                        <td className="px-5 py-4 text-center"><Pill type={item.tag} kind="tag" /></td>
                        <td className="px-5 py-4 text-center">
                          <div className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-emerald-50 text-emerald-600 rounded-full border border-emerald-100 text-[9px] font-bold uppercase">
                            <CheckCircle2 size={11} /> OK
                          </div>
                        </td>
                      </tr>
                    ))}
                    {mappedItems.length === 0 && (
                      <tr><td colSpan={5}><EmptyState icon={GitBranch} text="매핑된 항목이 없습니다" /></td></tr>
                    )}
                  </tbody>
                </table>
              </Card>
            )}
          </div>

          {/* Notice */}
          <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-5 flex gap-4 items-start">
            <div className="bg-indigo-600 p-2.5 rounded-xl text-white shadow-lg shadow-indigo-200"><AlertCircle size={20} /></div>
            <div>
              <h4 className="font-bold text-indigo-900 text-sm">{selectedB?.name} 작업 시 주의사항</h4>
              <p className="text-xs text-indigo-700 leading-relaxed mt-1 opacity-80">
                매핑된 항목의 파라미터 기본값이 방송사 정책과 일치하는지 반드시 확인하세요. 특히 글자/줄 수 제한 검증기의 임계값 설정에 유의하시기 바랍니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
