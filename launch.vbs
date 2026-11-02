Option Explicit
Dim shell, fso, root, pythonw, command, result
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = fso.BuildPath(root, ".venv\Scripts\pythonw.exe")
If Not fso.FileExists(pythonw) Then
    MsgBox "Python environment missing. Follow README.md to install .venv first.", 16, "crystalX"
    WScript.Quit 1
End If
shell.CurrentDirectory = root
shell.Environment("PROCESS")("PYTHONPATH") = fso.BuildPath(root, "src")
command = Chr(34) & pythonw & Chr(34) & " -m crystalx"
result = shell.Run(command, 0, True)
If result <> 0 Then
    MsgBox "Startup failed. Check logs/crystalx.log and Python dependencies in README.md.", 16, "crystalX"
End If
