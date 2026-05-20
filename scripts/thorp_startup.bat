@echo off
REM Thorp 24/7 — inicializador para Windows Task Scheduler
REM Colocar no Agendador de Tarefas: "Executar no logon do usuario"
REM
REM Caminhos relativos ao diretorio do script
cd /d "%~dp0"

REM Iniciar watchdog em janela escondida
start /min powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0thorp_247.ps1"
