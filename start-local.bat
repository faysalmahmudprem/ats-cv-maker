@echo off
cd /d D:\ats-cv-maker\backend
start "ats-backend" /min D:\ats-cv-maker\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
cd /d D:\ats-cv-maker\frontend
start "ats-frontend" /min cmd /c "npm run dev -- --host 127.0.0.1 --port 5173"
