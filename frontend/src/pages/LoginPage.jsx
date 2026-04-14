import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/ui';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!username || !password) return;
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/mapping');
    } catch (err) {
      setError(err?.response?.data?.detail || '아이디 또는 비밀번호가 올바르지 않습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }}>
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-600/8 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md mx-4">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-600 rounded-2xl shadow-2xl shadow-indigo-500/30 mb-6">
            <Settings className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">AirRule</h1>
          <p className="text-slate-400 text-sm mt-2 font-medium">방송 미디어 정책 관리 시스템</p>
        </div>

        <Card className="p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2 block">아이디</label>
              <input
                type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                placeholder="Username" autoFocus
                className="w-full px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-medium"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2 block">비밀번호</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-medium"
                />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-100 px-4 py-3 rounded-xl text-xs font-medium">
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <button
              type="submit" disabled={!username || !password || loading}
              className="w-full py-3.5 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-40 disabled:pointer-events-none shadow-lg shadow-indigo-200/30 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              로그인
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-100">
            <p className="text-[10px] text-slate-400 font-medium text-center mb-3">테스트 계정</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { u: 'admin', p: 'admin123', label: '관리자' },
                { u: 'dev1', p: 'dev123', label: '개발' },
                { u: 'sub1', p: 'sub123', label: '자막' },
              ].map((acc) => (
                <button
                  key={acc.u}
                  onClick={() => { setUsername(acc.u); setPassword(acc.p); }}
                  className="text-[10px] font-bold text-slate-500 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg py-2 px-3 transition-colors"
                >
                  {acc.label}
                </button>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
