// 함수별 설명 + 케이스 예시 카탈로그 (function_name 기준)
// 엔진(backend/app/engine/rules.py = mediaflow 원본)의 실제 동작을 사람이 읽기 좋게 정리한 것.
// 후처리(processing): { before, after } / 검증(validation): { input, fail(true=재작업) }
//
// 화면에서는 techItem.function_name 으로 이 카탈로그를 찾고,
// 없으면 techItem.desc 로 폴백한다.
//
// 여기 적힌 예시는 backend/tools/verify_function_guide.py 로 실제 엔진에 돌려 검증한다.
// 줄바꿈은 화면에 보이도록 문자 그대로 \n 으로 적는다.

export const FUNCTION_GUIDE = {
  // ───────── 1차 공통 후처리 ─────────
  postprocess_remove_delete_tag: {
    summary: '편집자가 남긴 삭제 마커를 처리합니다. {\\ㅅ}는 괄호 안이면 괄호 그룹만, 괄호 밖이면 자막 자체를 삭제하고, {\\}는 뒤에 이어지는 마침표·말줄임표까지 함께 지웁니다.',
    cases: [
      { label: '괄호 안', before: '(해설{\\ㅅ}) 안녕', after: ' 안녕' },
      { label: '마커 + 뒤 부호', before: '안녕.{\\}...', after: '안녕.' },
    ],
  },
  postprocess_strip_whitespace: {
    summary: '자막 앞뒤의 불필요한 공백을 제거합니다.',
    cases: [
      { label: '앞뒤 공백', before: '  안녕하세요  ', after: '안녕하세요' },
    ],
  },
  postprocess_trim_speaker_spaces: {
    summary: '소괄호·대괄호 안쪽의 불필요한 공백을 제거합니다.',
    cases: [
      { label: '괄호 안 공백', before: '( 웃음 )', after: '(웃음)' },
    ],
  },
  postprocess_add_speaker_space: {
    summary: '닫는 괄호 ) 바로 뒤에 글자가 붙어 있으면 한 칸 띄웁니다. 뒤가 공백·[·( 이면 띄우지 않습니다.',
    cases: [
      { label: '화자 뒤', before: '(영희)안녕하세요', after: '(영희) 안녕하세요' },
    ],
  },
  postprocess_normalize_spaces: {
    summary: '문장 중간에 두 칸 이상 연속된 공백을 한 칸으로 정리합니다. 줄바꿈은 보존합니다.',
    cases: [
      { label: '연속 공백', before: '오늘은   특별한    날', after: '오늘은 특별한 날' },
    ],
  },
  postprocess_add_space_after_special_punctuation: {
    summary: '말줄임표(...)·물음표·느낌표·물결(~) 뒤에 바로 글자가 붙어 있으면 한 칸 띄웁니다. 줄 맨 앞은 제외하고, 숫자 뒤 ~ 는 범위 표현이라 건드리지 않습니다.',
    cases: [
      { label: '물음표 뒤', before: '정말?그래요', after: '정말? 그래요' },
      { label: '말줄임표 뒤', before: '음...그러니까', after: '음... 그러니까' },
      { label: '숫자 범위', before: '1~9월', after: '1~9월' },
    ],
  },
  postprocess_remove_wrong_punctuation: {
    summary: '문장 맨 앞에 잘못 붙은 기호(. ... ? ! ~)와 맨 끝의 불필요한 쉼표를 제거합니다. 마침표 2개(..)는 위치와 무관하게 유지합니다.',
    cases: [
      { label: '앞 기호', before: '?무슨 말이야', after: '무슨 말이야' },
      { label: '끝 쉼표', before: '그러니까,', after: '그러니까' },
    ],
  },
  postprocess_normalize_ellipsis: {
    summary: '마침표 2개는 1개로, 4개는 3개로 정리합니다. 3개는 그대로 두고, 5개 이상은 후처리하지 않고 검증에서 재작업으로 넘깁니다.',
    cases: [
      { label: '점 2개', before: '글쎄..', after: '글쎄.' },
      { label: '점 4개', before: '음....', after: '음...' },
      { label: '점 5개 이상', before: '아니.....', after: '아니.....' },
    ],
  },
  postprocess_normalize_repeats: {
    summary: '! ? , ~ 가 반복되면 하나로 줄입니다. 마침표는 말줄임표 보존을 위해 대상이 아닙니다.',
    cases: [
      { label: '느낌표 반복', before: '대박!!!', after: '대박!' },
      { label: '말줄임표', before: '아니...', after: '아니...' },
    ],
  },
  postprocess_normalize_wrong_mixed_punctuations: {
    summary: "잘못 입력된 기호를 표준 기호로 바꿉니다. ’‘ → ', ． · → . 이고 큰따옴표는 삭제합니다. 곘→겠, 꼐→께 오탈자도 함께 보정합니다.",
    cases: [
      { label: '곡선 따옴표', before: '그건 ‘진짜’예요', after: "그건 '진짜'예요" },
      { label: '큰따옴표 삭제', before: '그가 "왔다"', after: '그가 왔다' },
      { label: '오탈자', before: '가곘습니다', after: '가겠습니다' },
    ],
  },
  postprocess_fix_position_tag: {
    summary: '위치 태그의 입력 실수를 {\\an8}로 보정합니다. 양쪽 중괄호가 없거나 닫는 중괄호가 빠지면 일반 텍스트일 수 있어 보정하지 않습니다.',
    cases: [
      { label: '한글 오타', before: '{\\무8}자막', after: '{\\an8}자막' },
      { label: '대문자', before: '{\\AN8}자막', after: '{\\an8}자막' },
      { label: '중괄호 없음', before: 'an8 데이터', after: 'an8 데이터' },
    ],
  },
  postprocess_fix_yae_yee: {
    summary: "중성 ㅒ/ㅖ 에 종성 ㅆ 이 붙은 오타를 ㅐ/ㅔ 로 교정합니다. 중성이 이미 ㅐ면 바꾸지 않고, 분해형(NFD) 한글은 조합형(NFC)으로 정규화합니다.",
    cases: [
      { label: 'ㅒ+ㅆ', before: '걨다', after: '갰다' },
      { label: 'ㅖ+ㅆ', before: '곘다', after: '겠다' },
      { label: '이미 ㅐ', before: '갰다', after: '갰다' },
    ],
  },
  postprocess_normalize_mix_characters: {
    summary: '서로 다른 문장부호가 섞여 연달아 나오면 마지막 부호만 남깁니다. 다만 마침표가 2개 이상 섞이면 말줄임표(...)로 정리합니다.',
    cases: [
      { label: '혼합 기호', before: '진짜?!', after: '진짜!' },
      { label: '마침표 섞임', before: '아니..!', after: '아니...' },
    ],
  },
  postprocess_normalize_comma_space: {
    summary: '쉼표 앞 공백은 지우고 뒤는 한 칸으로 맞춥니다. 뒤에 숫자가 정확히 세 자리일 때만 천 단위로 보고 붙입니다.',
    cases: [
      { label: '쉼표 띄우기', before: '네,그리고', after: '네, 그리고' },
      { label: '천 단위', before: '2, 400억', after: '2,400억' },
      { label: '숫자 나열', before: '1, 2345', after: '1, 2345' },
    ],
  },
  postprocess_normalize_period_space: {
    summary: '마침표 앞 공백은 지우고, 뒤에 글자가 이어질 때만 한 칸 띄웁니다. 문장 끝과 닫는 괄호 앞에는 띄우지 않고, 숫자 사이 마침표는 앞뒤 공백을 지웁니다.',
    cases: [
      { label: '뒤에 글자', before: '안녕.세요', after: '안녕. 세요' },
      { label: '숫자 사이', before: '6. 25', after: '6.25' },
      { label: '문장 끝', before: '안녕하세요.', after: '안녕하세요.' },
    ],
  },
  postprocess_sync_overlap: {
    summary: '앞 자막의 끝 시간과 뒤 자막의 시작 시간이 정확히 맞닿으면 앞 자막을 10ms 당겨 떼어 놓습니다. 실제로 겹치는(오버랩) 구간은 건드리지 않습니다.',
    cases: [
      { label: '경계 맞닿음', before: '…03,000 / 03,000…', after: '…02,990 / 03,000…' },
    ],
  },
  postprocess_reset_subtitles_from_list: {
    summary: '자막을 시작 시간 순으로 정렬하고 인덱스(번호)를 1부터 다시 매깁니다.',
    cases: [
      { label: '인덱스 재부여', before: '3, 1, 2번 섞임', after: '1, 2, 3번 정렬' },
    ],
  },

  // ───────── 공통 검증 ─────────
  validate_pair_characters: {
    summary: '괄호·따옴표·음표(♪)의 짝이 맞는지 검사합니다. 짝이 안 맞으면 재작업입니다.',
    cases: [
      { label: '짝 맞음', input: '(웃음) 안녕', fail: false },
      { label: '괄호 안 닫힘', input: '(웃음 안녕', fail: true },
      { label: '음표 홀수', input: '♪ 노래', fail: true },
    ],
  },
  validate_special_characters_allow_music_note: {
    summary: '허용되지 않는 특수문자가 있는지 검사합니다. 음표(♪)는 허용하고 슬래시(/)는 불허합니다.',
    cases: [
      { label: '음표 OK', input: '♪ 라라라 ♪', fail: false },
      { label: '슬래시', input: '입력/출력', fail: true },
    ],
  },
  validate_special_characters: {
    summary: '한글·영문·숫자·기본 문장부호 외의 문자를 검출합니다. 음표도 허용하지 않습니다.',
    cases: [
      { label: '정상', input: '안녕하세요!', fail: false },
      { label: '음표', input: '♪ 라라라 ♪', fail: true },
    ],
  },
  validate_empty_content: {
    summary: '내용이 비어 있는 자막을 검출합니다.',
    cases: [
      { label: '내용 있음', input: '안녕하세요', fail: false },
      { label: '공백만', input: '   ', fail: true },
    ],
  },
  validate_ellipsis_count: {
    summary: '마침표가 5개 이상 연속되면 검출합니다. 2~4개는 후처리가 정리하므로 대상이 아닙니다.',
    cases: [
      { label: '말줄임표 OK', input: '글쎄...', fail: false },
      { label: '점 5개', input: '글쎄.....', fail: true },
    ],
  },
  validate_sync_negative_or_zero: {
    summary: '시작 시간이 종료 시간과 같거나 늦은(길이 0 이하) 자막을 검출합니다.',
    cases: [
      { label: '정상', input: '01,000 → 03,000', fail: false },
      { label: '역전', input: '03,000 → 03,000', fail: true },
    ],
  },
  validate_length_lines: {
    summary: '한 줄의 글자 수가 방송사 기준을 넘는지 줄별로 검사합니다. TVING은 영문·기호를 0.5자로 계산합니다.',
    cases: [
      { label: '기준 이내', input: '짧은 한 줄 자막', fail: false },
      { label: '글자수 초과', input: '이것은 기준 글자수를 넘어가는 매우 긴 한 줄입니다', fail: true },
    ],
  },
  validate_line_count: {
    summary: '자막의 줄 수가 방송사 기준을 넘는지 검사합니다.',
    cases: [
      { label: '2줄 이내', input: '첫째 줄\\n둘째 줄', fail: false },
      { label: '3줄', input: '첫째 줄\\n둘째 줄\\n셋째 줄', fail: true },
    ],
  },
  validate_line_count_allow_hyphen: {
    summary: 'KBS 규칙: 기본 1줄이지만 모든 줄이 - 로 시작하면 2줄까지 허용합니다. 일부 줄만 하이픈이면 오류입니다.',
    cases: [
      { label: '모두 하이픈', input: '-안녕하세요\\n-반갑습니다', fail: false },
      { label: '하이픈 없음', input: '안녕하세요\\n반갑습니다', fail: true },
      { label: '일부만 하이픈', input: '-안녕하세요\\n반갑습니다', fail: true },
    ],
  },

  // ───────── 2차 후처리 ─────────
  postprocess_over_length_lines: {
    summary: '한 줄이 기준 글자 수를 넘으면 공백(어절) 단위로 앞에서부터 채우며 줄을 나눕니다(greedy). 스타일 태그는 글자 수에서 제외합니다.',
    cases: [
      { label: '긴 줄 분리', before: '아주 길어서 한 줄에 안 들어가는 문장입니다', after: '아주 길어서 한 줄에 안 들어가는\\n문장입니다' },
    ],
  },
  postprocess_over_length_lines_middle: {
    summary: 'TVCS 규칙: 기준 글자 수를 넘으면 중앙에 가장 가까운 공백에서 나눕니다. 나눈 줄도 넘치면 반복하고, 공백이 없으면 나누지 않습니다.',
    cases: [
      { label: '중앙 분할', before: '아주 길어서 한 줄에 안 들어가는 문장입니다', after: '아주 길어서 한 줄에\\n안 들어가는 문장입니다' },
    ],
  },
  postprocess_remove_not_pair_characters: {
    summary: '짝이 맞지 않는 괄호·따옴표·기호를 제거합니다.',
    cases: [
      { label: '안 닫힌 괄호', before: '(웃음 안녕', after: '웃음 안녕' },
    ],
  },
  postprocess_remove_other_characters: {
    summary: 'JTBC 규칙: * ♪ ♫ [] () <> ^ 를 일괄 제거합니다.',
    cases: [
      { label: '기호 제거', before: '*안녕* [웃음] <효과음>', after: '안녕 웃음 효과음' },
    ],
  },
  postprocess_remove_all_star: {
    summary: 'TVCS 규칙: STT 병합 마커인 별표(*)를 위치와 무관하게 전부 제거합니다. 앞뒤 문장은 그대로 둡니다.',
    cases: [
      { label: '별표 제거', before: '안녕*하세요', after: '안녕하세요' },
    ],
  },
  postprocess_remove_star_and_angle_for_lghv: {
    summary: 'LGHV 규칙: 별표(*)와 꺾쇠(<>)를 제거합니다.',
    cases: [
      { label: '별표/꺾쇠', before: '*안녕* <효과음>', after: '안녕 효과음' },
    ],
  },
  postprocess_remove_star_and_angle_for_skbb: {
    summary: 'SKBB 규칙: 큰따옴표·음표·소괄호·별표·꺾쇠를 일괄 제거합니다.',
    cases: [
      { label: '기호 제거', before: '(웃음) ♪노래♪ <효과음>', after: '웃음 노래 효과음' },
    ],
  },
  postprocess_remove_not_pair_paren_quotes_for_lghv: {
    summary: 'LGHV 규칙: 짝이 맞지 않는 괄호·따옴표만 제거합니다. 짝이 맞으면 그대로 둡니다.',
    cases: [
      { label: '안 닫힌 괄호', before: '(웃음 안녕', after: '웃음 안녕' },
      { label: '짝 맞음', before: '(웃음) 안녕', after: '(웃음) 안녕' },
    ],
  },
  postprocess_remove_not_pair_paren_quotes_for_skbb: {
    summary: "SKBB 규칙: 짝이 맞지 않는 작은따옴표(')와 꺾쇠(<>)만 제거합니다.",
    cases: [
      { label: '안 닫힌 꺾쇠', before: '<효과음 안녕', after: '효과음 안녕' },
    ],
  },
  postprocess_normalize_music_to_double_note_for_lghv: {
    summary: 'LGHV 표준인 겹음표(♫)로 음표를 통일합니다.',
    cases: [{ label: '음표 통일', before: '♪ 노래 ♬', after: '♫ 노래 ♫' }],
  },
  postprocess_normalize_music_to_single_note_for_tvng: {
    summary: 'TVING 표준인 홑음표(♪)로 음표를 통일합니다.',
    cases: [{ label: '음표 통일', before: '♫ 노래 ♬', after: '♪ 노래 ♪' }],
  },
  postprocess_keep_bracket_music_note_and_remove_others_for_lghv: {
    summary: 'LGHV 규칙: 대괄호 안 [♫ …] 의 음표만 남기고 그 밖의 음표는 제거합니다.',
    cases: [{ label: '대괄호 밖 제거', before: '[♫ 노래] ♫ 대사', after: '[♫ 노래]  대사' }],
  },
  postprocess_normalize_asterisk_for_skbb: {
    summary: 'SKBB 모자이크 표기를 정리합니다. 별표가 2개 이상이면 **로 통일하고, 1개면 별도 토큰으로 치환합니다.',
    cases: [{ label: '모자이크', before: '***', after: '**' }],
  },
  postprocess_remove_first_hypn: {
    summary: '파일의 첫 자막(1번)에서만 맨 앞 하이픈(-)을 제거합니다.',
    cases: [
      { label: '첫 자막 하이픈', before: '-안녕하세요', after: '안녕하세요' },
    ],
  },
  postprocess_remove_space_after_hypn: {
    summary: '줄 맨 앞 "- " 의 하이픈 뒤 공백을 제거합니다.',
    cases: [
      { label: '하이픈 뒤', before: '- 안녕', after: '-안녕' },
    ],
  },
  postprocess_mark_overlapped_multi_speaker: {
    summary: '시간이 겹치는 자막을 하나로 합치고 화자 구분자를 붙입니다. 3개 이상 겹치면 가장 많이 겹치는 2개만 합치고, 파일의 첫 자막에는 구분자를 붙이지 않습니다. 대괄호 태그만인 자막은 병합에서 제외합니다.',
    cases: [
      { label: '오버랩 병합', before: '안녕 / (겹침) 반가워', after: '안녕\\n- 반가워' },
    ],
  },
  postprocess_apply_overlap_hyphen_for_all_speech: {
    summary: 'TVING 규칙: 오버랩 그룹에 발화가 2개 이상이면 그룹 안의 모든 발화에 "- "를 붙입니다. 음향 자막에는 붙이지 않고, 이미 "- "로 시작하면 중복으로 넣지 않습니다.',
    cases: [
      { label: '전체 발화 부착', before: '안녕 / (겹침) 반가워', after: '- 안녕 / - 반가워' },
    ],
  },
  postprocess_add_period_between_lines: {
    summary: '한 자막 안에서 다음 줄이 - 나 ( 로 시작하면 앞 줄 끝에 마침표를 붙입니다. 앞 줄이 이미 종결부호나 닫는 괄호로 끝나면 건너뜁니다.',
    cases: [
      { label: '줄 사이', before: '밥 먹었어\\n- 응 먹었어', after: '밥 먹었어.\\n- 응 먹었어' },
    ],
  },
  postprocess_add_period_between_subs: {
    summary: '다음 자막이 - 나 ( 로 시작하면 앞 자막 끝에 마침표를 붙여 문장을 끊습니다. 마침표 때문에 글자 수를 넘기면 줄 수 여유가 있을 때만 줄을 나눕니다.',
    cases: [
      { label: '화자 전환', before: '밥 먹었어 → (영희) 응', after: '밥 먹었어. → (영희) 응' },
    ],
  },
  postprocess_adjust_subtitle_gaps: {
    summary: 'DLIV 규칙: 자막 사이 간격이 0.083초(24fps 2프레임)보다 좁으면 앞 자막의 끝 시간을 당겨 간격을 확보합니다. 오버랩 구간은 건드리지 않습니다.',
    cases: [
      { label: '간격 확보', before: '앞 …02,000 / 뒤 02,000…', after: '앞 …01,917 / 뒤 02,000…' },
    ],
  },
  postprocess_adjust_short_sync: {
    summary: 'DLIV 규칙: 1초보다 짧은 자막을 늘립니다. 다음 자막과의 간격이 우선이라 간격을 지킬 수 있는 지점까지만 늘어나므로 1초 미만으로 남을 수 있고, 그건 검증이 받아냅니다.',
    cases: [
      { label: '짧은 자막', before: '길이 0.4초', after: '길이 1.0초 (여유가 있을 때)' },
    ],
  },

  // ───────── 2차 방송사 검증 ─────────
  validate_overlapped_over_lines: {
    summary: '시간이 겹치는 자막의 줄 수가 기준을 넘으면 검출합니다.',
    cases: [
      { label: '1줄+1줄 OK', input: '안녕 / 반가워', fail: false },
      { label: '2줄 오버랩', input: '안녕\\n잘가 / 반가워', fail: true },
    ],
  },
  validate_sync_overlapped: {
    summary: 'SKBB·TVCS 규칙: 앞 자막 끝이 뒤 자막 시작보다 늦어 시간이 겹치면 검출합니다. 오버랩 자체를 허용하지 않습니다.',
    cases: [
      { label: '안 겹침', input: '…03,000 / 03,500…', fail: false },
      { label: '겹침', input: '…03,500 / 03,000…', fail: true },
    ],
  },
  validate_sync_short_duration: {
    summary: 'DLIV 규칙: 자막 길이가 1초 미만이면 검출합니다.',
    cases: [
      { label: '1초 이상', input: '길이 1.5초', fail: false },
      { label: '1초 미만', input: '길이 0.5초', fail: true },
    ],
  },
  validate_sync_gap: {
    summary: 'DLIV 규칙: 자막 사이 간격이 0.083초 미만이면 검출합니다. 후처리가 간격을 보장하므로 정상 흐름에서는 걸리지 않는 안전망이고, 오버랩 구간은 대상이 아닙니다.',
    cases: [
      { label: '간격 충분', input: '앞 …02,000 / 뒤 02,100…', fail: false },
      { label: '간격 0초', input: '앞 …02,000 / 뒤 02,000…', fail: true },
    ],
  },
  validate_hyphen_no_space_after_for_skbb: {
    summary: 'SKBB·DLIV 규칙: 줄 맨 앞 하이픈(-) 뒤에 공백이 오면 검출합니다. 이 방송사들의 표기는 공백 없는 -대사 형태입니다.',
    cases: [
      { label: '공백 없음 OK', input: '-안녕', fail: false },
      { label: '공백 있음', input: '- 안녕', fail: true },
    ],
  },
  validate_mosaic_count_for_skbb: {
    summary: 'SKBB 규칙: 연속된 별표(*) 그룹의 길이가 기준(2개)과 다르면 검출합니다.',
    cases: [
      { label: '2개 OK', input: '**', fail: false },
      { label: '1개', input: '*', fail: true },
      { label: '3개', input: '***', fail: true },
    ],
  },
  validate_comma_space: {
    summary: 'TVING 규칙: 쉼표 앞뒤가 모두 공백 없이 붙어 있으면 검출합니다. 한쪽이라도 공백이나 줄바꿈이 있으면 정상이고, 숫자 사이 쉼표와 문장 끝 쉼표도 정상입니다.',
    cases: [
      { label: '띄움 OK', input: '네, 그리고', fail: false },
      { label: '숫자 사이 OK', input: '1,000원', fail: false },
      { label: '양쪽 붙음', input: '네,그리고', fail: true },
    ],
  },
  validate_overlapped_only_text_for_lghv: {
    summary: 'LGHV 규칙: 오버랩된 1줄+1줄 중 한쪽이라도 대괄호 태그만으로 되어 있으면 검출합니다.',
    cases: [
      { label: '대사+대사 OK', input: '안녕 / 반가워', fail: false },
      { label: '태그 겹침', input: '[웃음] / 반가워', fail: true },
    ],
  },
  validate_overlapped_accumulated_lines: {
    summary: 'DLIV 규칙: 연속으로 겹치는 그룹의 누적 줄 수가 3줄을 넘으면 그룹 전체를 검출합니다. 2개 이상 겹칠 때만 발동합니다.',
    cases: [
      { label: '3줄 이내 OK', input: '겹침 누적 2줄', fail: false },
      { label: '누적 초과', input: '겹침 누적 4줄', fail: true },
    ],
  },

  // ───────── 최종 납품 ─────────
  postprocess_remove_last_punctuation: {
    summary: '납품 직전 단일 마침표를 제거합니다. 말줄임표(...)와 숫자 사이·영문 약어의 마침표는 보존합니다.',
    cases: [
      { label: '마침표 제거', before: '감사합니다.', after: '감사합니다' },
      { label: '소수점 보존', before: '1.5초입니다.', after: '1.5초입니다' },
      { label: '말줄임표 보존', before: '글쎄...', after: '글쎄...' },
    ],
  },
  postprocess_add_banner_subtitle: {
    summary: '납품 시 맨 앞에 장애인방송 제작지원 배너 자막을 삽입합니다. 노출 구간은 방송사별로 다릅니다(JTBC·KBS 0:00~0:05 / TVCS 0:00~0:07). KBS는 배너가 첫 자막과 겹치지 않도록 첫 자막 0.1초 앞에서 끊습니다.',
    cases: [
      { label: '배너 삽입', before: '(첫 자막)', after: '[배너] 장애인방송 VOD 제작지원…\\n(첫 자막)' },
    ],
  },
};

export function getGuide(item) {
  if (!item) return null;
  return FUNCTION_GUIDE[item.function_name] || null;
}
