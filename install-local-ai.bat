@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Hay chay install.bat truoc.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements-local-ai.txt
if errorlevel 1 (
  echo Cai bo thu vien Hachimi that bai. Kiem tra Python 3.11 x64 va ket noi Internet.
  pause
  exit /b 1
)
echo Da cai xong thu vien. Mo ung dung va bam DICH BANG HACHIMI de tai mo hinh lan dau.
pause
