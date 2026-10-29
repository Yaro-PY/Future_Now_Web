@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run: python -m venv .venv
  echo Then: .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
  exit /b 1
)
if not exist "static\react\index.html" (
  if not exist "frontend\node_modules\vite" (
    call npm ci --prefix frontend
    if errorlevel 1 exit /b 1
  )
  call npm run build --prefix frontend
  if errorlevel 1 exit /b 1
)
if not defined PORT set "PORT=8002"
echo Future Now React Website: http://127.0.0.1:%PORT%/
".venv\Scripts\python.exe" -B main.py
exit /b %errorlevel%
