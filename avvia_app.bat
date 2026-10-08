@echo off
title AI Short Generator 1.0
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%PYTHONPATH%

echo ===================================================
echo     AI SHORT GENERATOR 1.0 - Desktop GUI
echo ===================================================
echo Avvio interfaccia nativa DirectX/OpenGL a 60 FPS...
echo.

py -3.12 app/main.py
if errorlevel 1 (
    echo.
    echo Tentativo di avvio con python standard di sistema...
    python app/main.py
    if errorlevel 1 (
        echo.
        echo [ERRORE] Impossibile avviare l'applicazione.
        pause
    )
)
