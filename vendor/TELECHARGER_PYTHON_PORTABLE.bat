@echo off
chcp 65001 > nul
title Téléchargement Python Portable - DIADJI FAMILY
cd /d "%~dp0.."

echo ===============================================================================
echo        TÉLÉCHARGEMENT ET EMBARQUEMENT DE PYTHON PORTABLE WINDOWS
echo ===============================================================================
echo.
echo Ce script configure un interpréteur Python autonome dans vendor\python_embed.
echo Une fois configuré, l'application fonctionnera sans jamais nécessiter
echo d'installation de Python sur la machine Windows de l'utilisateur final.
echo.

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Interpréteur Python système détecté, lancement du script de configuration...
    python vendor\telecharger_python_portable.py
    goto :FIN
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" vendor\telecharger_python_portable.py
    goto :FIN
)

echo [INFO] Aucun Python système détecté. Configuration via PowerShell natif Windows...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop';" ^
    "$vDir = Join-Path (Get-Location) 'vendor';" ^
    "$eDir = Join-Path $vDir 'python_embed';" ^
    "$wDir = Join-Path $vDir 'wheels';" ^
    "$zipPath = Join-Path $vDir 'python-embed.zip';" ^
    "$url = 'https://www.python.org/ftp/python/3.13.2/python-3.13.2-embed-amd64.zip';" ^
    "Write-Host '[*] Téléchargement de Python 3.13.2 Embeddable...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "(New-Object System.Net.WebClient).DownloadFile($url, $zipPath);" ^
    "Write-Host '[OK] Téléchargement terminé. Extraction vers vendor\python_embed...';" ^
    "New-Item -ItemType Directory -Path $eDir -Force | Out-Null;" ^
    "Expand-Archive -Path $zipPath -DestinationPath $eDir -Force;" ^
    "Remove-Item $zipPath -Force;" ^
    "$spDir = Join-Path $eDir 'Lib\site-packages';" ^
    "New-Item -ItemType Directory -Path $spDir -Force | Out-Null;" ^
    "Get-ChildItem -Path $eDir -Filter '*._pth' | ForEach-Object {" ^
    "    $pyz = $_.Name.Replace('._pth', '.zip');" ^
    "    Set-Content -Path $_.FullName -Value \"$pyz`n.`nLib`nLib/site-packages`n..`n..\..`nimport site`n\" -Encoding UTF8;" ^
    "};" ^
    "if (Test-Path $wDir) {" ^
    "    Get-ChildItem -Path $wDir -Filter '*.whl' | ForEach-Object {" ^
    "        Write-Host \"[*] Extraction de $($_.Name)...\" ;" ^
    "        Expand-Archive -Path $_.FullName -DestinationPath $spDir -Force;" ^
    "    };" ^
    "};" ^
    "Write-Host '[OK] Python Portable configuré avec succès dans vendor\python_embed !';"

:FIN
echo.
pause
