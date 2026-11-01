@echo off
chcp 65001 > nul
title Tests Automatisés - DIADJI FAMILY
cd /d "%~dp0"
echo ===============================================================================
echo             LANCEMENT DES TESTS DE VALIDATION - DIADJI FAMILY
echo ===============================================================================
echo.
python tests/run_tests.py
echo.
pause
