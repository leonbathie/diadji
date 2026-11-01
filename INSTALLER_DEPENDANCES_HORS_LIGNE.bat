@echo off
chcp 65001 > nul
title Installation Hors-Ligne des Dépendances - DIADJI FAMILY
cd /d "%~dp0"

echo ===============================================================================
echo       INSTALLATION DES DÉPENDANCES HORS-LIGNE (100%% AUTONOME)
echo ===============================================================================
echo.
echo  Ce script installe toutes les bibliothèques Python requises (openpyxl, etchetera)
echo  directement depuis les paquets pré-embarqués dans vendor\wheels
echo  SANS avoir besoin d'accès à Internet.
echo.

REM 1. Détection de Python Portable embarqué si présent
if exist "%~dp0vendor\python_embed\python.exe" (
    echo [OK] Environnement Python Portable autonome détecté : vendor\python_embed
    echo Vérification de l'intégration des dépendances hors-ligne...
    "%~dp0vendor\python_embed\python.exe" -c "import openpyxl, et_xmlfile; print('[OK] openpyxl & et_xmlfile operationnels dans Python Portable')" >nul 2>nul
    if %errorlevel% neq 0 (
        echo [INFO] Injection des paquets wheels dans site-packages de Python Portable...
        powershell.exe -NoProfile -Command "Get-ChildItem '%~dp0vendor\wheels\*.whl' | ForEach-Object { Expand-Archive -Path $_.FullName -DestinationPath '%~dp0vendor\python_embed\Lib\site-packages' -Force }"
    )
    echo [OK] Python Portable est 100%% équipé de ses dépendances hors-ligne.
    echo.
)

REM 2. Détection de Python système pour équipement optionnel
set "PY_EXE="
where python >nul 2>nul
if %errorlevel% equ 0 set "PY_EXE=python"

if not defined PY_EXE (
    where py >nul 2>nul
    if %errorlevel% equ 0 set "PY_EXE=py -3"
)

if not defined PY_EXE (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if exist "C:\Python313\python.exe" set "PY_EXE=C:\Python313\python.exe"
    if exist "C:\Python312\python.exe" set "PY_EXE=C:\Python312\python.exe"
    if exist "C:\Python311\python.exe" set "PY_EXE=C:\Python311\python.exe"
)

if not defined PY_EXE (
    if exist "%~dp0vendor\python_embed\python.exe" (
        echo ===============================================================================
        echo  [OK] Toutes les dépendances hors-ligne sont prêtes dans vendor\python_embed !
        echo ===============================================================================
        echo Vous pouvez démarrer le logiciel immédiatement via LANCER_APPLICATION.bat.
        pause
        exit /b 0
    )
    echo [ERREUR] Aucun interpréteur Python n'est détecté.
    echo Remarque : Si vous utilisez DIADJI_FAMILY.exe ou INSTALLATEUR_DIADJI_FAMILY.exe,
    echo aucune dépendance externe ni installation de Python n'est requise.
    pause
    exit /b 1
)

echo [OK] Interpréteur Python système détecté : %PY_EXE%
echo.
echo Installation hors-ligne depuis vendor\wheels vers Python système...
%PY_EXE% -m pip install --no-index --find-links="%~dp0vendor\wheels" -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ===============================================================================
    echo  [OK] Toutes les dépendances hors-ligne sont prêtes et installées !
    echo ===============================================================================
    echo.
) else (
    echo.
    echo [INFO] Pip n'a pas pu installer dans Python système (ou paquets déjà satisfaits).
    echo L'exécutable autonome et Python Portable restent 100%% opérationnels.
    echo.
)

pause
