import { Hash, Clock, ArrowRightLeft, Music, Languages, Mic2, Trash2, Type, FileText } from 'lucide-react';

export const RULE_CATEGORIES = {
  specs:      { label: '기본 규격',     icon: Hash,           accent: '#64748b' },
  sync:       { label: '싱크 작업',     icon: Clock,          accent: '#2563eb' },
  overlap:    { label: '오버랩',        icon: ArrowRightLeft, accent: '#ea580c' },
  lyrics:     { label: '노래 가사',     icon: Music,          accent: '#db2777' },
  foreign:    { label: '외국어',        icon: Languages,      accent: '#4f46e5' },
  sound:      { label: '음향/효과음',   icon: Mic2,           accent: '#7c3aed' },
  oc_delete:  { label: '자막 삭제(OC)', icon: Trash2,         accent: '#dc2626' },
  speaker:    { label: '화자 구분',     icon: Type,           accent: '#059669' },
  punctuation:{ label: '구두점/기호',   icon: FileText,       accent: '#0891b2' },
};
