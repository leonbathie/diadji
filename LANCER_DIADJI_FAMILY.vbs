' ==============================================================================
' DIADJI FAMILY - LANCEUR SILENCIEUX SANS CONSOLE
' ==============================================================================
' Ce script démarre l'application DIADJI FAMILY via pythonw.exe (officiel Python
' Software Foundation / Microsoft), garantissant une ouverture instantanée
' sans fenêtre noire d'invite de commandes et 100% compatible Smart App Control.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
appPy = currentDir & "\app.py"

' Détection de pythonw.exe officiel
pywExe = "C:\Users\dell\AppData\Local\Python\pythoncore-3.15-64\pythonw.exe"

If Not fso.FileExists(pywExe) Then
    ' Recherche dans PATH
    On Error Resume Next
    pywExe = "pythonw.exe"
    On Error GoTo 0
End If

' Lancement invisible (0 = caché)
cmd = """" & pywExe & """ """ & appPy & """"
WshShell.CurrentDirectory = currentDir
WshShell.Run cmd, 0, False
