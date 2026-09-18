@echo off
title AliBahmani IronOre Process Simulator v1.0.0
cd /d "%~dp0"
echo ================================================================
echo  AliBahmani IronOre Process Simulator v1.0.0
echo  Developer / Manufacturer: Ali Bahmani (علی بهمنی)
echo  Contact: 09915420558
echo ================================================================
echo.
if exist "..\runtime\python\python.exe" (
  set "PYEXE=..\runtime\python\python.exe"
) else if exist "runtime\python\python.exe" (
  set "PYEXE=runtime\python\python.exe"
) else (
  set "PYEXE=python"
)
"%PYEXE%" ahsim_app.py %*
echo.
echo ----------------------------------------------------------------
echo Exit code: %ERRORLEVEL%
pause
