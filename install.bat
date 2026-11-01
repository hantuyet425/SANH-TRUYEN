@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo          CAI DAT SANH TRUYEN
echo ========================================
where pymanager >nul 2>nul
if not errorlevel 1 (
  echo Su dung Python Install Manager de tao moi truong Python 3.11...
  pymanager exec -V:3.11 -m venv .venv
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Khong tim thay Python Install Manager hoac Python Launcher.
    echo Hay cai Python Install Manager va runtime 3.11 truoc.
    pause
    exit /b 1
  )
  py -3.11 -m venv .venv
)
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
