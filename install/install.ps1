# BryteMama Creator Kit installer for Windows.
# Sets up the video tools and adds the kit to installed assistants. Safe to run again: every step skips itself when done.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
#
# Uses only free tools: ffmpeg (video), whisper.cpp (transcription), Python. Everything the kit adds lives in
# ~\.bryte-kit, so it never changes other tools' setups. Keep this file ASCII (Windows PowerShell 5.1).
param(
  [string]$KitZip = 'https://github.com/LiveBryte/bryte-creator-kit/archive/refs/heads/main.zip',
  [ValidateSet('Auto', 'Codex', 'Claude')][string]$Assistant = 'Auto'
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$Home2 = Join-Path $HOME '.bryte-kit'
$KitDir = Join-Path $Home2 'kit'
$WhisperBin = Join-Path $Home2 'whisper\bin'
$ModelDir = Join-Path $Home2 'models'
$Model = 'ggml-large-v3-turbo-q5_0.bin'
$WhisperZip = 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.2/whisper-bin-x64.zip'
$ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$Model"

function Say([string]$m)  { Write-Host $m }
function Ok([string]$m)   { Write-Host "  READY  $m" }
function Fail([string]$m) { Write-Host "STOPPED: $m"; exit 1 }
function Has([string]$n)  { [bool](Get-Command $n -ErrorAction SilentlyContinue) }

# Programs installed during this run only show up on PATH in new windows. Re-read the saved PATH so this run
# can use them right away.
function Refresh-Path {
  $saved = @([Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User')) -join ';'
  $env:Path = (($env:Path + ';' + $saved) -split ';' | Where-Object { $_ } | Select-Object -Unique) -join ';'
}

# Installs one app with winget. "Already installed" counts as success.
$WingetAlreadyThere = @(-1978335189, -1978335135)
function Get-App([string]$id, [string]$label) {
  if (-not (Has 'winget')) { Fail 'To install the missing tools, install or update App Installer from the Microsoft Store, then run setup again.' }
  Say "  installing $label (Windows may ask to allow changes: click Yes)"
  & winget install --id $id --exact --silent --accept-package-agreements --accept-source-agreements | Out-Null
  $code = $LASTEXITCODE
  if ($code -ne 0 -and $WingetAlreadyThere -notcontains $code) { Fail "Couldn't install $label. Run the installer again." }
  Refresh-Path
}

New-Item -ItemType Directory -Force $Home2, $ModelDir | Out-Null
Refresh-Path

# 1. The kit itself --------------------------------------------------------------
Say '1. The BryteMama kit'
$here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (Test-Path (Join-Path $here '.claude-plugin\marketplace.json')) {
  if ((Resolve-Path $here).Path -ne $KitDir) {
    New-Item -ItemType Directory -Path $KitDir -Force -ErrorAction Stop | Out-Null
    foreach ($entry in @('skills', 'install', '.claude-plugin', '.codex-plugin')) {
      $source = Join-Path $here $entry
      if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $KitDir -Recurse -Force -ErrorAction Stop
      }
    }
  }
} else {
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ('bryte-' + [guid]::NewGuid())
  New-Item -ItemType Directory -Force $tmp | Out-Null
  & curl.exe -fsSL -o "$tmp\kit.zip" $KitZip
  if ($LASTEXITCODE -ne 0) { Fail "Couldn't download the kit. Check the internet connection and run the installer again." }
  Expand-Archive "$tmp\kit.zip" "$tmp\x" -Force
  $src = Get-ChildItem "$tmp\x" -Directory | Select-Object -First 1
  Remove-Item $KitDir -Recurse -Force -ErrorAction SilentlyContinue
  Move-Item $src.FullName $KitDir
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
Ok "kit in $KitDir"

# 3. ffmpeg ------------------------------------------------------------------------
Say '2. Video tools (ffmpeg)'
if (-not ((Has 'ffmpeg') -and (Has 'ffprobe'))) { Get-App 'Gyan.FFmpeg' 'the video tools' }
if (-not (Has 'ffmpeg')) {
  $hit = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hit) { $env:Path = "$($hit.DirectoryName);$env:Path" }
}
if (-not (Has 'ffmpeg')) { Fail "ffmpeg didn't finish installing. Run the installer again." }
Ok 'ffmpeg'

# 4. Python (a real one, not the Microsoft Store placeholder) --------------------
Say '3. Python'
function Find-Python {
  $cands = @()
  if (Has 'py') { $cands += (& py -3 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -First 1) }
  $onPath = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue
  if ($onPath) { $cands += $onPath.Source }
  $cands += (Get-ChildItem @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python3*\python.exe'), (Join-Path $env:ProgramFiles 'Python3*\python.exe')) -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
  foreach ($c in $cands) {
    if ($c -and (Test-Path $c) -and ($c -notmatch 'WindowsApps')) {
      & $c -c 'import sys; sys.exit(sys.version_info < (3, 8))' *> $null
      if ($LASTEXITCODE -eq 0) { return $c }
    }
  }
  return $null
}
$Py = Find-Python
if (-not $Py) { Get-App 'Python.Python.3.12' 'Python'; $Py = Find-Python }
if (-not $Py) { Fail "Python didn't finish installing. Run the installer again." }
[IO.File]::WriteAllText((Join-Path $Home2 'python-path.txt'), $Py)
Ok "Python ($Py)"

# 5. Whisper (transcription) -------------------------------------------------------
Say '4. Transcription (Whisper)'
$whisper = $null
if (Has 'whisper-cli') { $whisper = (Get-Command whisper-cli).Source }
foreach ($p in @((Join-Path $WhisperBin 'whisper-cli.exe'), (Join-Path $env:LOCALAPPDATA 'whisper.cpp\bin\whisper-cli.exe'))) {
  if (-not $whisper -and (Test-Path $p)) { $whisper = $p }
}
if (-not $whisper) {
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ('whisper-' + [guid]::NewGuid())
  New-Item -ItemType Directory -Force $tmp | Out-Null
  & curl.exe -fsSL -o "$tmp\w.zip" $WhisperZip
  if ($LASTEXITCODE -ne 0) { Fail "Couldn't download Whisper. Run the installer again." }
  Expand-Archive "$tmp\w.zip" "$tmp\x" -Force
  $cli = Get-ChildItem "$tmp\x" -Recurse -Filter 'whisper-cli.exe' | Select-Object -First 1
  if (-not $cli) { Fail "The Whisper download was incomplete. Run the installer again." }
  New-Item -ItemType Directory -Force $WhisperBin | Out-Null
  Copy-Item (Join-Path $cli.DirectoryName '*') $WhisperBin -Recurse -Force
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  $whisper = Join-Path $WhisperBin 'whisper-cli.exe'
}
Ok 'Whisper'

# 6. Transcription model: the biggest download (about 550 MB) ---------------
Say '5. Transcription model (about 550 MB, the slow part)'
$haveModel = (Test-Path (Join-Path $ModelDir $Model)) -or (Test-Path (Join-Path $env:LOCALAPPDATA "whisper.cpp\models\$Model"))
if (-not $haveModel) {
  $part = Join-Path $ModelDir "$Model.part"
  & curl.exe -fL -C - -o $part $ModelUrl
  if ($LASTEXITCODE -ne 0) { Fail "The model download stopped partway. Run the installer again; it picks up where it left off." }
  Move-Item $part (Join-Path $ModelDir $Model) -Force
}
Ok 'transcription model'

# 7. Final check -----------------------------------------------------------------
Say '6. Final check'
$script = Join-Path $KitDir 'skills\bryte-video\scripts\bryte_edit.py'
& $Py -I $script check
if ($LASTEXITCODE -ne 0) { Fail 'Something is still missing. Run the installer again.' }

Say '7. Adding the kit to your assistants'
if ($Assistant -ne 'Codex' -and -not (Has 'claude')) {
  $roots = @((Join-Path $HOME '.local\bin'), (Join-Path $env:APPDATA 'npm'), (Join-Path $env:LOCALAPPDATA 'Claude-Data'),
             (Join-Path $env:APPDATA 'Claude\claude-code'), (Join-Path $env:LOCALAPPDATA 'AnthropicClaude'))
  foreach ($r in $roots) {
    if (Test-Path $r) {
      $hit = Get-ChildItem $r -Recurse -Include 'claude.exe', 'claude.cmd' -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch 'WindowsApps' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($hit) { $env:Path = "$($hit.DirectoryName);$env:Path"; break }
    }
  }
}
$setupCodex = $Assistant -eq 'Codex' -or ($Assistant -eq 'Auto' -and (
  $env:CODEX_THREAD_ID -or (Has 'codex') -or (Get-AppxPackage -Name 'OpenAI.Codex' -ErrorAction SilentlyContinue)))
$setupClaude = $Assistant -ne 'Codex' -and (Has 'claude')
if (-not $setupCodex -and -not $setupClaude) {
  Fail "Install Codex or Claude on this computer, then run setup again."
}
if ($setupCodex) {
  $skills = Join-Path $HOME '.agents\skills'
  $link = Join-Path $skills 'bryte-video'
  $target = Join-Path $KitDir 'skills\bryte-video'
  New-Item -ItemType Directory -Force $skills -ErrorAction Stop | Out-Null
  $existing = Get-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue
  if (-not $existing) {
    New-Item -ItemType Junction -Path $link -Target $target -ErrorAction Stop | Out-Null
  } elseif ($existing.LinkType -notin @('Junction', 'SymbolicLink') -or $existing.Target -ne $target) {
    Fail "Codex already has a BryteMama skill in a different location."
  }
  Ok 'kit added to Codex'
}
if ($setupClaude) {
  $markets = & claude plugin marketplace list 2>$null | Out-String
  if ($markets -match 'bryte-creator-kit') {
    & claude plugin marketplace remove bryte-creator-kit *> $null
  }
  & claude plugin marketplace add $KitDir
  if ($LASTEXITCODE -ne 0) { Fail "Couldn't add the kit to Claude. Run the installer again." }
  $plugins = & claude plugin list 2>$null | Out-String
  if ($plugins -match 'bryte-video@bryte-creator-kit') {
    & claude plugin update 'bryte-video@bryte-creator-kit' --scope user
  } else {
    & claude plugin install 'bryte-video@bryte-creator-kit' --scope user
  }
  if ($LASTEXITCODE -ne 0) { Fail "Couldn't turn the kit on in Claude. Run the installer again." }
  Ok 'kit added to Claude'
}

Say ''
Say 'DONE. Restart your assistant, start a new chat and type: check my kit'
