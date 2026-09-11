Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath & "\Catering_Present\jayraldines_catering"
WshShell.Run "venv\Scripts\pythonw.exe main.py", 0, False
