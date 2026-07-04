$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = Join-Path $LogDir "local_sync_$Stamp.log"

Set-Location $ProjectRoot

"[$(Get-Date -Format o)] Starting GitHub report sync" | Out-File -FilePath $LogFile -Encoding utf8
"Repository: $ProjectRoot" | Out-File -FilePath $LogFile -Encoding utf8 -Append

git pull --rebase --autostash origin main 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
$ExitCode = $LASTEXITCODE

"[$(Get-Date -Format o)] Sync exit code: $ExitCode" | Out-File -FilePath $LogFile -Encoding utf8 -Append
exit $ExitCode
