# 영양제 추천 시스템

MSA 기반 영양제 추천 및 분석 시스템

## 프로젝트 구조

```
.
├── backend/          # FastAPI 백엔드 서비스
├── db-sql/          # 데이터베이스 스키마 및 SQL
└── API-SPEC.md      # API 명세서
```

## 기술 스택

- **Backend**: Python, FastAPI
- **Database**: PostgreSQL
- **Architecture**: MSA (Microservice Architecture)

## 시작하기

### 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

자세한 내용은 [backend/README.md](./backend/README.md)를 참고하세요.

## API 문서

API 명세는 [API-SPEC.md](./API-SPEC.md)를 참고하세요.
