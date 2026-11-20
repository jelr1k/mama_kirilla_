Set WshShell = CreateObject("WScript.Shell")
Set objEnv = WshShell.Environment("PROCESS")
objEnv("ASSISTANT_NO_PAUSE") = "1"
strPath = WScript.ScriptFullName
strBat = Left(strPath, InStrRev(strPath, ".")) & "bat"
WshShell.Run Chr(34) & strBat & Chr(34), 0, False
Set WshShell = Nothing
