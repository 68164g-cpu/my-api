# Full Stack 로컬 테스트 (Vercel + Railway + FastAPI + Supabase)

```
day_2/
├─ my_api/      FastAPI (→ Railway)   main.py, requirements.txt, Procfile, schema.sql, .env
├─ frontend/    정적 페이지 (→ Vercel) index.html
└─ vjeju/       파이썬 가상환경
```

## 0. 한 번만: Supabase에 테이블 만들기
Supabase 대시보드 → SQL Editor → `my_api/schema.sql` 내용을 붙여넣고 Run.

## 1. .env 확인 (my_api/.env)
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
FRONT_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## 2. 백엔드 실행 (터미널 1)
```powershell
cd C:\vebe-advanced\day_2
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\vjeju\Scripts\Activate.ps1
pip install -r my_api\requirements.txt
cd my_api
uvicorn main:app --reload --port 8000
```
확인: http://localhost:8000/health , http://localhost:8000/health/db , http://localhost:8000/docs

## 3. 프론트 실행 (터미널 2)
```powershell
cd C:\vebe-advanced\day_2\frontend
python -m http.server 3000
```
브라우저: http://localhost:3000 → 상단이 초록색이면 성공. 메모 추가/삭제 동작 확인.

## 4. 배포
- Railway: Root Directory = `my_api`, Variables에 SUPABASE_URL / SUPABASE_SECRET_KEY / FRONT_ORIGINS(Vercel 주소) 입력
- Vercel: Root Directory = `frontend`, 배포 후 `index.html`의 `RAILWAY_URL`을 Railway 주소로 교체
