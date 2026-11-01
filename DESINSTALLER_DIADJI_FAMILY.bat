@echo off
chcp 65001 > nul
title Désinstallation des raccourcis - DIADJI FAMILY
echo ===============================================================================
echo                DÉSINSTALLATION DES RACCOURCIS DIADJI FAMILY
echo ===============================================================================
echo.
echo Cette opération va supprimer les raccourcis du Bureau et du Menu Démarrer.
echo Vos données (magasin.db et classeur Excel) seront conservées en sécurité.
echo.
set /p confirm="Confirmer la suppression des raccourcis (O/N) ? "
if /i "%confirm%" neq "O" (
    echo Opération annulée.
    pause
    exit /b 0
)

powershell -NoProfile -Command "$desktop = [System.Environment]::GetFolderPath('Desktop'); $s1 = "$desktop\DIADJI FAMILY.lnk"; if (Test-Path $s1) { Remove-Item -Force $s1; Write-Host '[OK] Raccourci Bureau supprimé.' }; $start = [System.Environment]::GetFolderPath('StartMenu'); $dir = "$start\Programs\DIADJI FAMILY"; if (Test-Path $dir) { Remove-Item -Recurse -Force $dir; Write-Host '[OK] Raccourcis Menu Démarrer supprimés.' }"

echo.
echo ===============================================================================
echo  Désinstallation terminée avec succès.
echo ===============================================================================
pause
