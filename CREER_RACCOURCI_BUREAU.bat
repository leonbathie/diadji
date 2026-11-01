@echo off
chcp 65001 > nul
title Création des Raccourcis - DIADJI FAMILY
cd /d "%~dp0"

echo ===============================================================================
echo            CRÉATION DES RACCOURCIS WINDOWS - DIADJI FAMILY
echo ===============================================================================
echo.
echo Configuration des raccourcis Bureau et Menu Démarrer Windows...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcuts.ps1"

if %errorlevel% equ 0 (
    echo.
    echo ===============================================================================
    echo  [✓] Raccourcis créés avec succès sur votre Bureau et Menu Démarrer !
    echo ===============================================================================
    echo.
) else (
    echo.
    echo [ATTENTION] Impossible de créer automatiquement les raccourcis via PowerShell.
    echo Vous pouvez lancer l'application en double-cliquant sur LANCER_APPLICATION.bat.
    echo.
)

pause
