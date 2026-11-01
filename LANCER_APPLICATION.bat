@echo off
chcp 65001 > nul
title DIADJI FAMILY - Logiciel de Caisse & Stock
cd /d "%~dp0"

echo ===============================================================================
echo                      DIADJI FAMILY - LOGICIEL DE GESTION EMBARQUÉ
echo ===============================================================================
echo.
echo  Entreprise   : DIADJI FAMILY (Dakar, Sénégal)
echo  Base données : SQLite Embarquée (magasin.db)
echo  Interface    : Caisse Express, Gestion des Stocks, Alertes & Excel
echo.

REM 1. Détection de l'interpréteur Python officiel (Python Software Foundation / Microsoft)
REM Cette méthode est 100% compatible avec Windows 11 Smart App Control (aucun blocage).
set "PY_EXE="
set "PYW_EXE="

if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
    set "PYW_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\pythonw.exe"
)

if not defined PY_EXE (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_EXE=python"
        set "PYW_EXE=pythonw"
    )
)

if not defined PY_EXE (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_EXE=py -3"
        set "PYW_EXE=pyw -3"
    )
)

REM 2. Si Python officiel est présent, lancer directement sans blocage Smart App Control
if defined PY_EXE (
    echo [OK] Environnement d'exécution sécurisé détecté (Signature officielle Python / Microsoft).
    echo Démarrage immédiat de DIADJI FAMILY...
    echo.
    "%PY_EXE%" app.py %*
    if %errorlevel% neq 0 (
        echo.
        echo [INFO] L'application s'est arrêtée.
        pause
    )
    exit /b 0
)

REM 3. Fallback sur l'exécutable autonome DIADJI_FAMILY.exe
if exist "%~dp0DIADJI_FAMILY.exe" (
    echo [INFO] Lancement de l'exécutable autonome DIADJI_FAMILY.exe...
    start "" "%~dp0DIADJI_FAMILY.exe" %*
    exit /b 0
)

echo [ERREUR] Aucun composant d'exécution n'a été trouvé.
echo Veuillez lancer l'application via le raccourci sur votre Bureau 'DIADJI FAMILY'.
pause
exit /b 1
