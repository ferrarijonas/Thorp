<#
.SYNOPSIS
    Launcher Thorp — inicia o bot (que ja cuida do MT5 internamente).
    Task Scheduler reinicia se algo morrer. Nao ha watchdog complexo.
#>
param([string]$TerminalId = "xp")

$BotScript = Join-Path $PSScriptRoot "run_bot.py"
$LogDir = Join-Path $PSScriptRoot "..\state\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "launcher.log"
$Line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Launcher iniciando bot $TerminalId..."
Add-Content -Path $LogFile -Value $Line

$p = Start-Process -FilePath "python" -ArgumentList "-u `"$BotScript`" --terminal $TerminalId" -WindowStyle Hidden -PassThru
Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Bot iniciado (PID $($p.Id))"
$p.WaitForExit()
Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Bot morreu (exit $($p.ExitCode)). Task Scheduler reinicia."
