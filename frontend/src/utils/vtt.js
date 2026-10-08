// 자막 원본 형식 판별 + WebVTT → SRT 변환 (서버 backend/app/routes_captions.py 의 vtt_to_srt 와 같은 규칙).
// 변환을 브라우저에서 해야 자막 파일을 사이트에서 직접 받고 버셀 함수를 안 거친다.

export function detectFormat(text, url = '') {
  const head = text.replace(/^\uFEFF/, '').slice(0, 200);
  if (head.startsWith('WEBVTT')) return 'vtt';
  if (/^\d+\r?\n\d{2}:\d{2}:\d{2},\d{3} -->/.test(head)) return 'srt';
  const ext = new URL(url, 'http://x').pathname.split('.').pop();
  return ext && ext.length <= 4 ? ext.toLowerCase() : 'txt';
}

const sec = (ts) => {
  const bits = ts.trim().replace(',', '.').split(':').map(Number);
  return bits.length === 3 ? bits[0] * 3600 + bits[1] * 60 + bits[2] : bits[0] * 60 + bits[1];
};

const fmt = (t) => {
  const ms = Math.round(Math.max(t, 0) * 1000);
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
};

// VTT 전용 태그·헤더·큐 설정은 버리고 i/b/u 는 유지, 순번은 1부터
export function vttToSrt(text) {
  const out = [];
  const blocks = text.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim().split(/\n{2,}/);
  for (const block of blocks) {
    const lines = block.split('\n');
    if (/^(WEBVTT|NOTE|STYLE|REGION)/.test(lines[0])) continue;
    const i = lines.findIndex((l) => l.includes('-->'));
    if (i < 0) continue;
    const [start, rest] = lines[i].split('-->');
    const end = rest.trim().split(/\s+/)[0];
    const body = lines.slice(i + 1).map((l) => l.replace(/<(?!\/?[ibu]>)[^>]*>/g, '').trimEnd()).filter((l) => l.trim());
    if (end && body.length) out.push(`${out.length + 1}\n${fmt(sec(start))} --> ${fmt(sec(end))}\n${body.join('\n')}`);
  }
  return out.join('\n\n') + '\n';
}
