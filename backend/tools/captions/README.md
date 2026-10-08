> 웹 화면 '프로그램 찾기'(backend/app/routes_captions.py)가 같은 흐름을 제공한다. 이 스크립트들은 대량 수집·통합본 분할용 CLI.

# MBC 다시보기 자막 수집

## 사용법

```bash
python3 backend/tools/captions/imbc_caption.py '<프로그램명 | bid | progCode>' docs/captions
```

- 프로그램명으로 바로 조회 가능. 이름이 안 맞으면 후보를 출력하고 멈추니 그땐 `progCode` 직접 입력
- `bid` 는 플레이어 주소의 `?bid=...` 값 (아무 회차나 하나면 됨)
- 저장 경로:
  - `docs/captions/{프로그램명}/vtt/{프로그램명}_{회차}.vtt`
  - `docs/captions/{프로그램명}/srt/{프로그램명}_{회차}.srt`
- 이미 받은 파일은 건너뛰므로 중단 후 재실행 가능
- `CaptionYN != "Y"` 인 회차는 `자막없음` 출력하고 스킵

## 통합본 분할 (검법남녀 시즌2)

이 프로그램만 다시보기 1편에 2회차가 묶여 있어서(`001-002`) 회차별로 쪼개야 한다.
MBC API 는 통합본 전체 길이만 주고 회차 경계는 안 주므로, **1부 영상 길이**를 직접 넣어야 한다.

```bash
# docs/captions/검법남녀 시즌2/boundaries.json 에 1부 길이 기입 후
python3 backend/tools/captions/imbc_caption.py --split 'docs/captions/검법남녀 시즌2'
```

```json
{ "001-002": "00:31:05.120", "003-004": "" }
```

- 값 = 1부 영상 길이. 비어 있으면 `경계 미입력` 출력하고 스킵
- 1부: 싱크·순번 그대로. 경계에 걸친 큐는 경계에서 끊음
- 2부: 모든 싱크에서 1부 길이를 빼고 순번을 1부터 재인덱싱
- 통합본 원본(`_001-002`)은 그대로 남김 — 지우면 재실행 시 다시 내려받음

## 대상 목록

| 프로그램 | progCode | 회차 | 상태 |
| --- | --- | --- | --- |
| 검법남녀 시즌2 | `1004574100000100000` | 17 | 완료 |
| 궁 | `1000143100000100000` | 24 | 완료 |
| 어쩌다 발견한 하루 | `1004739100000100000` | 17 | 완료 |
| 옷소매 붉은 끝동 | `1005299100000100000` | 19 | 완료 |
| 이토록 친밀한 배신자 | `1006580100000100000` | 11 | 완료 |
| 커피프린스 1호점 | `1000176100000100000` | 17 | 완료 |
| 킬미힐미 | `1003135100000100000` | 20 | 완료 |
| 열녀박씨 계약결혼뎐 | `1006218100000100000` | 13 | 완료 |
| 파스타 | `1002349100000100000` | 19 | 완료 |

## 메모

- 자막 CDN 은 인증·쿠키 없이 열림: `https://playvod.imbc.com/caption/{progCode}/caption_{ContentId}.vtt`
- 회차 목록 API: `https://playvod.imbc.com/api/ContentList_Templete?programId={progCode}&orderBy=d&selectYear=0&curPage=1&pageSize=100`
- 프로그램 검색 API: `https://cue.imbc.com/api/program.aspx?query={이름}&startNum=0` (`startNum` 0-베이스)
- 통합본 전체 길이는 `ContentList_Templete` / `ContentInfo` 의 `Duration` 필드 (회차 경계 정보는 없음)
- 변환 로직 점검: `python3 backend/tools/captions/imbc_caption.py --test`
- MBC 저작물이라 개인 용도 외 재배포 주의. `.vtt` 는 커밋하지 않음

# JTBC 다시보기 자막 수집

```bash
python3 backend/tools/captions/jtbc_caption.py '<프로그램명>' ['<프로그램명>' ...]   # 기본 저장: docs/JTBC
```

- 저장 경로: `docs/JTBC/{프로그램명}/vtt|srt/{프로그램명}_{회차}.vtt|srt` (SRT 변환은 `imbc_caption.vtt_to_srt` 재사용)
- 흐름: 드라마 검색(`POST tv.jtbc.co.kr/tv/program-list-more`, term=첫 단어) → 프로그램 페이지의 `/replay/pr…/pm…` → `{replay}/paginate?page=N` 회차 목록 → 회차 페이지의 `api.jtbc.co.kr/v1/vod/vo…` → `tracks[label=KR].file` VTT
- `[최종회]` 는 마지막 숫자 회차 + 1 로 저장. 서막·특집·몰아보기는 라벨 그대로 파일명에 들어감
- 19세 회차(부부의 세계, 우아한 친구들)는 회차 페이지가 로그인으로 리다이렉트됨 → 성인인증 계정으로 브라우저 로그인 후 쿠키를 저장소 루트 `.env` 또는 `backend/.env` 에 `JTBC_COOKIE=...` 로 넣고 실행 (`.env` 는 gitignore)

# TVING 자막 유무 확인

```bash
python3 backend/tools/captions/tving_caption.py '<프로그램명>' [...]   # 또는 -f 목록.txt (한 줄에 하나, '- ' 접두 무시, '시즌1 ~ 17' 펼침)
```

- 로그인 불필요. 검색 `gw.tving.com/bff/search/v2/content/total/search` → 회차 `api.tving.com/v2/media/frequency/program/{P코드}` → 회차별 `v2/media/content/info` 의 `ko_cc_yn`
- 제목이 정확히 일치하는 프로그램만 판정, 아니면 `[못 찾음]` + 후보 출력
- 2026-10-07 확인: 요청 목록 49개(영애씨 17시즌 포함) 전부 자막 없음. 대조군 포핸즈·날아올라라 나비는 전 회차 `Y`
