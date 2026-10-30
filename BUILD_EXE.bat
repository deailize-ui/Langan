@echo off
cd /d "%~dp0"
echo LANGAN EXPLORER DESKTOP - WINDOWS BUILD
where py >nul 2>nul
if errorlevel 1 (echo Install Python 3.11 64-bit from python.org and enable Add Python to PATH.& pause & exit /b 1)
if not exist models\SmolLM2-360M-Instruct-Q5_0.gguf (echo Run DOWNLOAD_MODEL.bat first.& pause & exit /b 1)
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (echo Package installation failed. See error above.& pause & exit /b 1)
pyinstaller --noconfirm --clean --onefile --windowed --name LanganExplorer --collect-all llama_cpp --add-data "models;models" langan_desktop.py
if errorlevel 1 (echo Build failed. See error above.& pause & exit /b 1)
echo BUILD COMPLETE: dist\LanganExplorer.exe
pause
