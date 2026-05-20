@echo off
REM Thorp 24/7 — inicializador para Windows Task Scheduler
REM
REM Caminhos relativos ao diretorio do script
cd /d "%~dp0"

REM Iniciar watchdog em background
start /b powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0thorp_247.ps1"
