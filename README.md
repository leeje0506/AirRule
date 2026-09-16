# AirRule - 방송 미디어 정책 관리 시스템

방송사별 자막/미디어 정책, 후처리/검증 항목을 관리하고 매핑하는 웹 애플리케이션입니다.

## 기술 스택

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Vite + React + Tailwind CSS v4
- **인증**: JWT (JSON Web Token)

## 프로젝트 구조

```
airrule/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 앱 엔트리 (startup 시 DB 생성 + seed)
│   │   ├── database.py       # SQLAlchemy engine, session
│   │   ├── models.py         # DB 모델 (User, Broadcaster, Policy, TechItem, Mapping, History)
│   │   ├── schemas.py        # Pydantic 스키마
│   │   ├── auth.py           # JWT 인증, 비밀번호 해싱, 권한 체크
│   │   ├── seed.py           # 초기 데이터 시드
│   │   ├── routes_auth.py
│   │   ├── routes_broadcasters.py
│   │   ├── routes_policies.py
│   │   ├── routes_tech_items.py
│   │   └── routes_mappings.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js     # Axios API 클라이언트
│   │   ├── context/AuthContext.jsx
│   │   ├── components/       # Sidebar, Header, ui (공용 컴포넌트), ruleCategories
│   │   ├── pages/            # Login, Policy, Library, Mapping, History, AppLayout
│   │   ├── App.jsx           # 라우터 설정
│   │   └── main.jsx
│   ├── vite.config.js        # Vite 설정 (Tailwind 플러그인 + API 프록시)
│   └── package.json
└── README.md
```

## 실행 방법

### 1. 백엔드

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

서버 시작 시 자동으로 SQLite DB 생성 및 시드 데이터가 삽입됩니다.

### 2. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:5173`에서 접속. API 요청은 Vite proxy를 통해 `localhost:8000`으로 전달됩니다.

## 테스트 계정

| 아이디 | 비밀번호  | 역할   | 권한                          |
|--------|-----------|--------|-------------------------------|
| admin  | admin123  | 관리자 | 전체 접근                     |
| dev1   | dev123    | 개발   | 후처리/검증 항목 수정 가능    |
| sub1   | sub123    | 자막   | 정책 추가/수정/삭제 가능      |

## 주요 기능

### 페이지 구성

1. **방송사 정책** (`/policies`)
   - 정책 목록 테이블 (펼쳐서 카테고리별 규칙 확인)
   - 정책 추가 / 수정 / 삭제
   - 수정 시 변경 메모 기록 → 수정내역 조회

2. **마스터 라이브러리** (`/library`)
   - 후처리/검증 항목 목록 (전체/후처리/검증 필터)
   - 항목 추가 / 수정
   - 파라미터 key-value 편집
   - 태그 관리: 진행 중 / 적용 / 예정

3. **매핑 매트릭스** (`/mapping`)
   - 방송사 선택 → 연결된 정책 + 후처리/검증 항목 확인
   - 매핑 편집 모드: 체크박스로 항목 선택/해제

4. **수정내역** (`/history`)
   - 정책 + 기술항목의 전체 변경 이력 타임라인

### 권한 시스템

- **개발 (dev)**: 후처리/검증 항목만 수정 가능
- **자막 (subtitle)**: 정책만 수정 가능
- **관리자 (admin)**: 전체 접근

## API 엔드포인트

| Method | Endpoint                          | 설명               | 권한      |
|--------|-----------------------------------|--------------------|-----------|
| POST   | /api/auth/login                   | 로그인             | 공개      |
| GET    | /api/auth/me                      | 현재 사용자 정보   | 인증      |
| GET    | /api/broadcasters                 | 방송사 목록        | 인증      |
| GET    | /api/policies                     | 정책 목록          | 인증      |
| POST   | /api/policies                     | 정책 추가          | subtitle  |
| PUT    | /api/policies/:id                 | 정책 수정          | subtitle  |
| DELETE | /api/policies/:id                 | 정책 삭제          | subtitle  |
| GET    | /api/policies/:id/history         | 정책 수정내역      | 인증      |
| GET    | /api/tech-items                   | 기술 항목 목록     | 인증      |
| POST   | /api/tech-items                   | 항목 추가          | dev       |
| PUT    | /api/tech-items/:id               | 항목 수정          | dev       |
| GET    | /api/tech-items/:id/history       | 항목 수정내역      | 인증      |
| GET    | /api/mappings/:broadcaster_id     | 매핑 조회          | 인증      |
| PUT    | /api/mappings/:broadcaster_id     | 매핑 수정          | 인증      |
| GET    | /api/history                      | 전체 수정내역      | 인증      |

## 배포 (Vercel)

DB 서버가 필요 없습니다. 화면에 뜨는 데이터는 전부 리포 안의 파일에서 파생됩니다.

| 데이터 | 원천 |
|---|---|
| 기술항목 · 실행 순서 · 방송사 | `backend/app/pipeline_config.py` (= mediaflow `config_subtitle.yml` 전사본) |
| 정책 매트릭스 | `backend/app/seed.py` 의 `POLICY_MATRIX` |
| 계정 | `backend/app/seed.py` |

서버가 뜰 때 메모리 SQLite에 이 내용을 채워 넣고, 내려가면 같이 사라집니다.
파일 쓰기가 불가능한 서버리스에서도 그대로 돕니다.

### 구성

리포 루트 `vercel.json` 이 Vercel Services 로 두 서비스를 정의한다.
`frontend/` 는 Vite 정적 빌드, `backend/` 는 FastAPI(`app.main:app`).
`/api/*` 는 backend, 나머지는 frontend 로 간다.
서비스는 **원본 경로를 그대로** 받으므로(`/api/auth/login` → `/api/auth/login`)
FastAPI 라우트 prefix 를 바꿀 필요가 없다.

> Services 는 권한이 필요한 기능이다. 계정에서 쓸 수 없으면 프론트/백엔드를
> 별도 Vercel 프로젝트 두 개로 나누고, 프론트에서 백엔드 도메인으로 rewrite 한다.

### 환경변수

| 이름 | 필수 | 설명 |
|---|---|---|
| `AIRRULE_SECRET_KEY` | **예** | JWT 서명 키. 없으면 프로세스마다 임의 키를 써서 재배포·재시작 때 로그인이 풀립니다 |
| `AIRRULE_DATABASE_URL` | 아니오 | 비워두면 메모리 SQLite. 영속 저장이 필요할 때만 지정 |
| `AIRRULE_READ_ONLY` | 아니오 | `auto`(기본) — 메모리 모드면 쓰기 차단 |
| `VITE_AIRRULE_READ_ONLY` | 아니오 | `false` 로 두면 프론트 편집 UI가 살아납니다 (영속 DB와 함께 쓸 것) |

`AIRRULE_SECRET_KEY` 값은 아래로 만든다.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

배포 브랜치가 `main` 이 아니면 Vercel 의 Production Branch 설정을 바꾸거나,
환경변수를 Preview 환경에도 등록해야 한다.

### 읽기 전용에 대하여

정책 셀 수정 · 기술항목 편집 · 연결 추가 · 매핑 저장은 현재 막혀 있습니다.
화면에서는 버튼이 감춰지고, 백엔드는 503을 돌려줍니다. 저장이 성공한 것처럼
보였다가 재시작 때 조용히 사라지는 상황을 막기 위한 것입니다.

규칙을 바꾸려면 mediaflow config를 고친 뒤 동기화하고 재배포합니다.

```bash
python backend/tools/sync_from_mediaflow.py /path/to/mediaflow
python backend/tools/verify_function_guide.py    # 화면 설명이 엔진과 맞는지 확인
```

편집이 필요해지면 `AIRRULE_DATABASE_URL` 에 Postgres를 주고
`VITE_AIRRULE_READ_ONLY=false` 로 두면 기존 편집 기능이 그대로 살아납니다.
