$ErrorActionPreference = "SilentlyContinue"
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AppDir) { $AppDir = (Get-Location).Path }

$IconPath = Join-Path $AppDir "diadji_icon.ico"
$AppPy = Join-Path $AppDir "app.py"
$VbsLauncher = Join-Path $AppDir "LANCER_DIADJI_FAMILY.vbs"
$BatLauncher = Join-Path $AppDir "LANCER_APPLICATION.bat"
$ExcelPath = Join-Path $AppDir "DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx"

# Detection du binaire officiel pythonw.exe (signe par Microsoft / PSF et exempt de blocage SAC)
$PywPath = "C:\Users\dell\AppData\Local\Python\pythoncore-3.15-64\pythonw.exe"
if (-not (Test-Path $PywPath)) {
    $found = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($found) { $PywPath = $found.Source }
}

# 1. Raccourci Bureau Principal "DIADJI FAMILY"
$ShortcutDesktop = $WshShell.CreateShortcut((Join-Path $DesktopPath "DIADJI FAMILY.lnk"))
if (Test-Path $PywPath) {
    $ShortcutDesktop.TargetPath = $PywPath
    $ShortcutDesktop.Arguments = "`"$AppPy`""
} else {
    $ShortcutDesktop.TargetPath = $BatLauncher
}
$ShortcutDesktop.WorkingDirectory = $AppDir
$ShortcutDesktop.Description = "Logiciel de Caisse & Stock Embarque - DIADJI FAMILY"
if (Test-Path $IconPath) {
    $ShortcutDesktop.IconLocation = $IconPath
}
$ShortcutDesktop.Save()
Write-Host "[OK] Raccourci Bureau 'DIADJI FAMILY' cree avec succes."

# 2. Dossier et Raccourcis Menu Demarrer
$StartMenuPath = [System.Environment]::GetFolderPath('StartMenu')
$StartProgramsDir = Join-Path (Join-Path $StartMenuPath "Programs") "DIADJI FAMILY"
if (-not (Test-Path $StartProgramsDir)) {
    New-Item -ItemType Directory -Path $StartProgramsDir -Force | Out-Null
}

$ShortcutApp = $WshShell.CreateShortcut((Join-Path $StartProgramsDir "DIADJI FAMILY.lnk"))
if (Test-Path $PywPath) {
    $ShortcutApp.TargetPath = $PywPath
    $ShortcutApp.Arguments = "`"$AppPy`""
} else {
    $ShortcutApp.TargetPath = $BatLauncher
}
$ShortcutApp.WorkingDirectory = $AppDir
$ShortcutApp.Description = "Logiciel de Caisse & Stock Embarque - DIADJI FAMILY"
if (Test-Path $IconPath) {
    $ShortcutApp.IconLocation = $IconPath
}
$ShortcutApp.Save()

# Raccourci Classeur Excel
if (Test-Path $ExcelPath) {
    $ShortcutExcel = $WshShell.CreateShortcut((Join-Path $StartProgramsDir "Classeur Excel DIADJI FAMILY.lnk"))
    $ShortcutExcel.TargetPath = $ExcelPath
    $ShortcutExcel.WorkingDirectory = $AppDir
    $ShortcutExcel.Description = "Tableau de Bord Excel DIADJI FAMILY"
    $ShortcutExcel.Save()
}

Write-Host "[OK] Raccourcis Windows crees avec succes et configures sans alerte de securite."
