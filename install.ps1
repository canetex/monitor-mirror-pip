# Instala Monitor Mirror PiP em %LOCALAPPDATA% e cria atalhos (Desktop/Start/Startup).
$ErrorActionPreference = "Stop"

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "MonitorMirror"
$Python = (Get-Command python -ErrorAction Stop).Source
$PythonW = Join-Path (Split-Path $Python) "pythonw.exe"
if (-not (Test-Path $PythonW)) { throw "pythonw.exe nao encontrado" }

Write-Host "Instalando em $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Force (Join-Path $SourceDir "mirror.py") (Join-Path $InstallDir "mirror.py")
Copy-Item -Force (Join-Path $SourceDir "requirements.txt") (Join-Path $InstallDir "requirements.txt")
Copy-Item -Force (Join-Path $SourceDir "launch.vbs") (Join-Path $InstallDir "launch.vbs")
Copy-Item -Force (Join-Path $SourceDir "MonitorMirror.bat") (Join-Path $InstallDir "MonitorMirror.bat")

$VenvDir = Join-Path $InstallDir ".venv"
if (-not (Test-Path $VenvDir)) {
    & $Python -m venv $VenvDir
}
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $InstallDir "requirements.txt") --quiet

# Executavel com nome visivel no Task Manager (copia do pythonw)
$AppExe = Join-Path $InstallDir "MonitorMirrorPiP.exe"
Copy-Item -Force $PythonW $AppExe

# Icone
Push-Location $InstallDir
& $VenvPython -c @"
from pathlib import Path
from mirror import make_tray_icon
icon = make_tray_icon(256)
path = Path(r'$InstallDir') / 'monitor-mirror.ico'
icon.save(path, format='ICO', sizes=[(16,16),(32,32),(48,48),(256,256)])
print(path)
"@
Pop-Location

$LaunchVbs = Join-Path $InstallDir "launch.vbs"
$Ico = Join-Path $InstallDir "monitor-mirror.ico"
$Wsh = New-Object -ComObject WScript.Shell

function Set-MirrorShortcut([string]$Path) {
    $Sc = $Wsh.CreateShortcut($Path)
    $Sc.TargetPath = "wscript.exe"
    $Sc.Arguments = "`"$LaunchVbs`""
    $Sc.WorkingDirectory = $InstallDir
    $Sc.WindowStyle = 7
    $Sc.Description = "Monitor Mirror PiP"
    if (Test-Path $Ico) { $Sc.IconLocation = "$Ico,0" }
    $Sc.Save()
}

$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Monitor Mirror PiP.lnk"
$Desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "Monitor Mirror PiP.lnk"
$Startup = Join-Path ([Environment]::GetFolderPath("Startup")) "Monitor Mirror PiP.lnk"
Set-MirrorShortcut $StartMenu
Set-MirrorShortcut $Desktop
Set-MirrorShortcut $Startup

Write-Host "OK: atalhos Desktop / Menu Iniciar / Startup."
Write-Host "Iniciando app..."
& wscript.exe $LaunchVbs
Write-Host "No Task Manager procure: MonitorMirrorPiP.exe"
