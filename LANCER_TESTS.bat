@echo off
chcp 65001 > nul
title Tests Automatisés - DIADJI FAMILY
cd /d "%~dp0"
echo ===============================================================================
echo             LANCEMENT DES TESTS DE VALIDATION - DIADJI FAMILY
echo ===============================================================================
echo.
set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
) else if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
)
"%PY_EXE%" tests/run_tests.py
echo.
pause
