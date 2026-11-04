@echo off
setlocal
cd /d "%~dp0"
echo SmartNet - Internet en casa
if not exist ".venv\Scripts\python.exe" (
    py -3.12 --version >nul 2>&1
    if errorlevel 1 (
        echo Instala Python 3.12 de 64 bits desde python.org y vuelve a abrir este archivo.
        pause
        exit /b 1
    )
    py -3.12 -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto error
exit /b 0
:error
echo No se pudo iniciar SmartNet. Revisa el mensaje anterior.
pause
exit /b 1
