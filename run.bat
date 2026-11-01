@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Chua cai dat. Hay chay install.bat truoc.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python main.py
if errorlevel 1 (
  echo Ung dung dung do loi. Hay chup noi dung loi va gui lai.
  pause
)
