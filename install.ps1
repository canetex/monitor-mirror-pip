# Instala Monitor Mirror PiP em %LOCALAPPDATA% (exe standalone com nome no Task Manager).
$ErrorActionPreference = "Stop"

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "MonitorMirror"
$DistExe = Join-Path $SourceDir "dist\MonitorMirrorPiP.exe"
$LocalExe = Join-Path $SourceDir "MonitorMirrorPiP.exe"

Write-Host "Instalando em $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Preferir exe ja buildado (release / dist)
$AppExeSrc = $null
if (Test-Path $DistExe) { $AppExeSrc = $DistExe }
elseif (Test-Path $LocalExe) { $AppExeSrc = $LocalExe }

if (-not $AppExeSrc) {
    Write-Host "Buildando MonitorMirrorPiP.exe (PyInstaller)..."
    $Python = (Get-Command python -ErrorAction Stop).Source
    $VenvDir = Join-Path $InstallDir ".venv-build"
    if (-not (Test-Path $VenvDir)) { & $Python -m venv $VenvDir }
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPython -m pip install -r (Join-Path $SourceDir "requirements.txt") pyinstaller --quiet
    Push-Location $SourceDir
    & $VenvPython -c "from mirror import make_tray_icon; make_tray_icon(256).save('monitor-mirror.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(256,256)])"
    & $VenvPython -m PyInstaller --noconfirm --clean --onefile --noconsole `
        --name MonitorMirrorPiP `
        --version-file (Join-Path $SourceDir "version_info.txt") `
        --icon (Join-Path $SourceDir "monitor-mirror.ico") `
        --hidden-import=pystray._win32 `
        --collect-all pystray `
        (Join-Path $SourceDir "mirror.py")
    Pop-Location
    $AppExeSrc = $DistExe
}

Copy-Item -Force $AppExeSrc (Join-Path $InstallDir "MonitorMirrorPiP.exe")
Copy-Item -Force (Join-Path $SourceDir "launch.vbs") (Join-Path $InstallDir "launch.vbs")
Copy-Item -Force (Join-Path $SourceDir "MonitorMirror.bat") (Join-Path $InstallDir "MonitorMirror.bat") -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $SourceDir "monitor-mirror.ico")) {
    Copy-Item -Force (Join-Path $SourceDir "monitor-mirror.ico") (Join-Path $InstallDir "monitor-mirror.ico")
}

$LaunchVbs = Join-Path $InstallDir "launch.vbs"
$Ico = Join-Path $InstallDir "monitor-mirror.ico"
$AppExe = Join-Path $InstallDir "MonitorMirrorPiP.exe"
$Wsh = New-Object -ComObject WScript.Shell

function Set-MirrorShortcut([string]$Path) {
    $Sc = $Wsh.CreateShortcut($Path)
    $Sc.TargetPath = $AppExe
    $Sc.WorkingDirectory = $InstallDir
    $Sc.WindowStyle = 7
    $Sc.Description = "Monitor Mirror PiP"
    if (Test-Path $Ico) { $Sc.IconLocation = "$Ico,0" }
    $Sc.Save()
}

Set-MirrorShortcut (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Monitor Mirror PiP.lnk")
Set-MirrorShortcut (Join-Path ([Environment]::GetFolderPath("Desktop")) "Monitor Mirror PiP.lnk")
Set-MirrorShortcut (Join-Path ([Environment]::GetFolderPath("Startup")) "Monitor Mirror PiP.lnk")

# Encerra instancia antiga e inicia a nova
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'MonitorMirrorPiP.exe' -or $_.CommandLine -like '*MonitorMirror*'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
Start-Process -FilePath $AppExe -WorkingDirectory $InstallDir

$vi = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($AppExe)
Write-Host "OK. Task Manager deve mostrar: $($vi.FileDescription)"
Write-Host "EXE: $AppExe"
