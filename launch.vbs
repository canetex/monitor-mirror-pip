Set sh = CreateObject("WScript.Shell")
installDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\MonitorMirror")
exe = installDir & "\MonitorMirrorPiP.exe"
sh.CurrentDirectory = installDir
sh.Run """" & exe & """", 0, False
