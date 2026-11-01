@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo          CAI DAT SANH TRUYEN
echo ========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Khong tim thay Python Launcher. Hay cai Python 3.11 x64 va danh dau Add Python to PATH.
  pause
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 (
  echo Khong tao duoc moi truong Python 3.11. Kiem tra lai Python.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Cai dat that bai. Hay chup loi o cua so nay gui lai de sua.
  pause
  exit /b 1
)
echo.
echo Cai dat co ban hoan tat. Bam RUN.bat de mo ung dung.
pause
