<#
.SYNOPSIS
    Watchdog Thorp 24/7 — mantém terminal MT5 + bot Python rodando.
.DESCRIPTION
    Lê state/bot_config.json, inicia/restaura o terminal MT5 de cada entrada,
    dispara o bot Python correspondente, e monitora ambos em loop.
    Se algum cair, reinicia automaticamente.
#>

param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\state\bot_config.json")
)

$LogDir = Join-Path $PSScriptRoot "..\state\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "watchdog.log"

function Write-Log {
    param([string]$Message)
    $Line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

function Get-RunningBot {
    param([string]$TerminalId)
    $bots = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $cmd = ($_ | Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue).CommandLine
        $cmd -and $cmd -match "run_bot\.py.*--terminal $TerminalId"
    }
    return $bots
}

function Start-Mt5IfNeeded {
    param([string]$ExePath, [string]$TerminalId)
    $running = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $ExePath
    }
    if (-not $running) {
        Write-Log "[$TerminalId] MT5 parado. Iniciando (minimizado): $ExePath"
        Start-Process -FilePath $ExePath -ArgumentList "/minimized"
        Start-Sleep 15
        $running = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Where-Object {
            $_.Path -eq $ExePath
        }
        if ($running) {
            Write-Log "[$TerminalId] MT5 iniciado (PID $($running.Id))"
        } else {
            Write-Log "[$TerminalId] ERRO: MT5 nao iniciou"
        }
    } else {
        Write-Log "[$TerminalId] MT5 ja rodando (PID $($running.Id))"
    }
}

function Start-BotIfNeeded {
    param([string]$TerminalId)
    $bots = Get-RunningBot -TerminalId $TerminalId
    if (-not $bots) {
        $BotScript = Join-Path $PSScriptRoot "run_bot.py"
        $PythonArgs = "-u `"$BotScript`" --terminal $TerminalId"
        Write-Log "[$TerminalId] Bot parado. Iniciando: python $PythonArgs"
        $job = Start-Process -FilePath "python" -ArgumentList "-u", "`"$BotScript`"", "--terminal", $TerminalId `
            -WindowStyle Hidden -PassThru
        Start-Sleep 3
        if (-not $job.HasExited) {
            Write-Log "[$TerminalId] Bot iniciado (PID $($job.Id))"
        } else {
            Write-Log "[$TerminalId] ERRO: Bot morreu imediatamente"
        }
    } else {
        Write-Log "[$TerminalId] Bot ja rodando (PID $($bots[0].Id))"
    }
}

function Test-Mt5Running {
    param([string]$ExePath)
    $proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $ExePath
    }
    return $null -ne $proc
}

function Test-BotRunning {
    param([string]$TerminalId)
    return $null -ne (Get-RunningBot -TerminalId $TerminalId)
}

# --- Loop principal ---
Write-Log "=== Thorp Watchdog iniciado ==="

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

if (-not $config.terminais -or $config.terminais.Count -eq 0) {
    Write-Log "Nenhum terminal configurado em $ConfigPath"
    exit 1
}

foreach ($t in $config.terminais) {
    Write-Log "Terminal configurado: $($t.id) | $($t.symbol) | estrategias: $($t.strategies -join ', ')"
}

while ($true) {
    foreach ($t in $config.terminais) {
        $id = $t.id
        $exe = $t.exe

        if (-not (Test-Mt5Running -ExePath $exe)) {
            Write-Log "[$id] MT5 offline. Reiniciando terminal..."
            Start-Mt5IfNeeded -ExePath $exe -TerminalId $id
            Start-Sleep 10
        }

        if (-not (Test-BotRunning -TerminalId $id)) {
            Write-Log "[$id] Bot offline. Aguardando terminal pronto..."
            Start-Sleep 10
            Start-BotIfNeeded -TerminalId $id
        }
    }
    Start-Sleep 15
}
