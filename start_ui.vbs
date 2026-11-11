Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.ScriptFullName
strBat = Left(strPath, InStrRev(strPath, ".")) & "bat"
WshShell.Run Chr(34) & strBat & Chr(34), 0, False
Set WshShell = Nothing
