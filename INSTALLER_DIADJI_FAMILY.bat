@echo off
chcp 65001 > nul
title Installation - DIADJI FAMILY
cd /d "%~dp0"

echo ===============================================================================
echo            INSTALLATEUR OFFICIEL POUR WINDOWS - DIADJI FAMILY
echo ===============================================================================
echo.
echo  Bienvenue dans le programme d'installation de DIADJI FAMILY.
echo  Ce script installe les raccourcis, initialise la base et configure votre système.
echo.

REM 1. Lancement direct si l'installateur autonome existe
if exist "%~dp0INSTALLATEUR_DIADJI_FAMILY.exe" (
    echo [OK] Assistant d'installation autonome détecté : INSTALLATEUR_DIADJI_FAMILY.exe
    echo Démarrage direct sans dépendance...
    start "" "%~dp0INSTALLATEUR_DIADJI_FAMILY.exe" %*
    exit /b 0
)

if exist "%~dp0dist\INSTALLATEUR_DIADJI_FAMILY.exe" (
    echo [OK] Assistant d'installation autonome détecté : dist\INSTALLATEUR_DIADJI_FAMILY.exe
    echo Démarrage direct sans dépendance...
    start "" "%~dp0dist\INSTALLATEUR_DIADJI_FAMILY.exe" %*
    exit /b 0
)

REM 2. Détection de Python Portable embarqué si présent
if exist "%~dp0vendor\python_embed\python.exe" (
    set "PY_EXE=%~dp0vendor\python_embed\python.exe"
    goto :PYTHON_READY
)

REM 3. Détection de l'interpréteur Python système
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
    echo [ERREUR] Aucun exécutable d'installation ni interpréteur Python n'a été trouvé.
    echo.
    echo Options :
    echo  1. Téléchargez l'exécutable INSTALLATEUR_DIADJI_FAMILY.exe (autonome).
    echo  2. Ou installez Python 3 depuis https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:PYTHON_READY
echo [OK] Interpréteur Python détecté : %PY_EXE%

REM Vérification silencieuse et installation hors-ligne de openpyxl si manquant
%PY_EXE% -c "import openpyxl" >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%~dp0vendor\wheels" (
        echo [INFO] Installation automatique hors-ligne de openpyxl depuis vendor\wheels...
        %PY_EXE% -m pip install --no-index --find-links="%~dp0vendor\wheels" openpyxl et_xmlfile >nul 2>nul
    )
)

echo Démarrage de l'assistant d'installation...
echo.

%PY_EXE% installer.py %*

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Passage en mode console de secours...
    %PY_EXE% installer.py --cli
    pause
)
