import { X } from 'lucide-react';

// ── Pill / Badge ────────────────────────────────────────────────

const TAG_STYLES = {
  in_progress: { bg: '#fef3c7', color: '#92400e', border: '#fde68a', label: '진행 중' },
  applied:     { bg: '#d1fae5', color: '#065f46', border: '#a7f3d0', label: '적용' },
  planned:     { bg: '#e0e7ff', color: '#3730a3', border: '#c7d2fe', label: '예정' },
};

const STATUS_STYLES = {
  active: { bg: '#dbeafe', color: '#1e40af', border: '#bfdbfe', label: 'Active' },
  review: { bg: '#fef3c7', color: '#92400e', border: '#fde68a', label: 'Review' },
  draft:  { bg: '#f1f5f9', color: '#475569', border: '#e2e8f0', label: 'Draft' },
};

export function Pill({ type, kind = 'tag' }) {
  const map = kind === 'status' ? STATUS_STYLES : TAG_STYLES;
  const s = map[type] || map.planned || map.draft;
  return (
    <span
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}
      className="text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wide whitespace-nowrap"
    >
      {s.label}
    </span>
  );
}

export { TAG_STYLES, STATUS_STYLES };

// ── Card ────────────────────────────────────────────────────────

export function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.04)] overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

// ── Button ──────────────────────────────────────────────────────

const BTN_VARIANTS = {
  primary: 'bg-slate-900 text-white hover:bg-slate-800 shadow-md',
  danger:  'bg-red-600 text-white hover:bg-red-700 shadow-md',
  ghost:   'text-slate-500 hover:text-slate-800 hover:bg-slate-100',
  accent:  'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200/50',
};

export function Btn({ children, onClick, variant = 'primary', disabled, small, className = '' }) {
  const size = small ? 'px-3 py-1.5 text-[11px]' : 'px-5 py-2.5 text-xs';
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 font-bold rounded-xl transition-all disabled:opacity-40 disabled:pointer-events-none ${size} ${BTN_VARIANTS[variant] || BTN_VARIANTS.primary} ${className}`}
    >
      {children}
    </button>
  );
}

// ── Modal ───────────────────────────────────────────────────────

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className={`relative bg-white rounded-3xl shadow-2xl ${wide ? 'max-w-3xl' : 'max-w-lg'} w-full max-h-[85vh] overflow-hidden flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-8 py-5 border-b border-slate-100">
          <h3 className="text-lg font-bold text-slate-800">{title}</h3>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-8 py-6">{children}</div>
      </div>
    </div>
  );
}

// ── Confirm Dialog ──────────────────────────────────────────────

export function ConfirmDialog({ open, onClose, onConfirm, title, message }) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-slate-600 mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <Btn variant="ghost" onClick={onClose}>취소</Btn>
        <Btn variant="danger" onClick={() => { onConfirm(); onClose(); }}>삭제</Btn>
      </div>
    </Modal>
  );
}

// ── Input ───────────────────────────────────────────────────────

export function Input({ label, value, onChange, placeholder, textarea, mono }) {
  const cls = `w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${mono ? 'font-mono text-xs' : ''}`;
  return (
    <label className="block mb-4">
      <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">{label}</span>
      {textarea ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`${cls} resize-none h-24`} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={cls} />
      )}
    </label>
  );
}

// ── Select ──────────────────────────────────────────────────────

export function Select({ label, value, onChange, options }) {
  return (
    <label className="block mb-4">
      <span className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 block">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}

// ── Empty State ─────────────────────────────────────────────────

export function EmptyState({ icon: Icon, text }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-300">
      <Icon size={48} strokeWidth={1} />
      <p className="mt-4 text-sm font-medium text-slate-400">{text}</p>
    </div>
  );
}
