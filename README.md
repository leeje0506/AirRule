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
