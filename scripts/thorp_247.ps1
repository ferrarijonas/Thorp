<#
.SYNOPSIS
    Watchdog Thorp 24/7 — mantém terminal MT5 + bot Python rodando.
.DESCRIPTION
    Le state/bot_config.json, inicia/restaura o terminal MT5 de cada entrada,
    dispara o bot Python correspondente, e monitora ambos em loop.
    Se algum cair, reinicia automaticamente.
#>

param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\state\bot_config.json"),
    [string]$StateDir = (Join-Path $PSScriptRoot "..\state")
)

# --- Single instance lock ---
$LockFile = Join-Path $StateDir "watchdog.lock"
if (Test-Path $LockFile) {
    $existingPid = Get-Content $LockFile -Raw
    if ($existingPid) {
        $alive = Get-Process -Id ([int]$existingPid.Trim()) -ErrorAction SilentlyContinue
        if ($alive) {
            Write-Host "Watchdog ja rodando (PID $($alive.Id))"
            exit 0
        }
        Write-Host "Lock stale (PID $($existingPid.Trim()) morto). Removendo..."
    }
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
}
[System.IO.File]::WriteAllText($LockFile, [string]$pid)
Write-Host "Lock criado (PID $pid)"

$LogDir = Join-Path $StateDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "watchdog.log"

function Write-Log {
    param([string]$Message)
    $Line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

function Get-BotPid {
    param([string]$TerminalId)
    $PidFile = Join-Path $StateDir "bot_$TerminalId.pid"
    if (-not (Test-Path $PidFile)) { return 0 }
    $botPid = Get-Content $PidFile -Raw
    if (-not $botPid) { return 0 }
    return [int]$botPid.Trim()
}

function Is-ProcessAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    return ($null -ne $proc) -and (-not $proc.HasExited)
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
    $botPid = Get-BotPid -TerminalId $TerminalId
    if (Is-ProcessAlive -ProcessId $botPid) {
        Write-Log "[$TerminalId] Bot ja rodando (PID $botPid)"
        return
    }

    $BotScript = (Join-Path $PSScriptRoot "run_bot.py")
    $PythonArgs = "-u `"$BotScript`" --terminal $TerminalId"
    Write-Log "[$TerminalId] Bot parado. Iniciando: python $PythonArgs"

    $process = Start-Process -FilePath "python" -ArgumentList $PythonArgs -WindowStyle Hidden -PassThru
    Start-Sleep 5

    $newPid = Get-BotPid -TerminalId $TerminalId
    if ($newPid -gt 0 -and (Is-ProcessAlive -ProcessId $newPid)) {
        Write-Log "[$TerminalId] Bot iniciado (PID $newPid)"
    } else {
        Write-Log "[$TerminalId] ERRO: Bot nao responde. PID file=$newPid"
    }
}

function Test-Mt5Running {
    param([string]$ExePath)
    $proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -eq $ExePath
    }
    return $null -ne $proc
}

# --- Loop principal ---
Write-Log "=== Thorp Watchdog iniciado ==="

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

if (-not $config.terminais -or $config.terminais.Count -eq 0) {
    Write-Log "Nenhum terminal configurado em $ConfigPath"
    $LockStream.Close()
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    exit 1
}

foreach ($t in $config.terminais) {
    $nomes = $t.strategies | ForEach-Object { $_.name }
    Write-Log "Terminal configurado: $($t.id) | $($t.symbol) | estrategias: $($nomes -join ', ')"
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

        if (-not (Is-ProcessAlive -ProcessId (Get-BotPid -TerminalId $id))) {
            Write-Log "[$id] Bot offline. Aguardando terminal pronto..."
            Start-Sleep 10
            Start-BotIfNeeded -TerminalId $id
        }
    }
    Start-Sleep 15
}
