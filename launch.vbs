Set sh = CreateObject("WScript.Shell")
installDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\MonitorMirror")
venvDir = installDir & "\.venv"
site = venvDir & "\Lib\site-packages"
exe = installDir & "\MonitorMirrorPiP.exe"
script = installDir & "\mirror.py"

sh.Environment("Process")("VIRTUAL_ENV") = venvDir
sh.Environment("Process")("PYTHONPATH") = site
sh.Environment("Process")("PYTHONNOUSERSITE") = "1"
sh.CurrentDirectory = installDir
sh.Run """" & exe & """ """ & script & """", 0, False
