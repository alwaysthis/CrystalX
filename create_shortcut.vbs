Option Explicit
Dim shell, fso, root, link
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set link = shell.CreateShortcut(fso.BuildPath(root, "CrystalX.lnk"))
link.TargetPath = shell.ExpandEnvironmentStrings("%WINDIR%\System32\wscript.exe")
link.Arguments = Chr(34) & fso.BuildPath(root, "launch.vbs") & Chr(34)
link.WorkingDirectory = root
link.IconLocation = fso.BuildPath(root, "assets\crystalx.ico") & ",0"
link.Save
