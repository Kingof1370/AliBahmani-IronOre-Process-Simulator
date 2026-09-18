@echo off
title AH-SIM - Generate Engineering Reports
cd /d "%~dp0"
if exist "..\runtime\python\python.exe" (
  set "PYEXE=..\runtime\python\python.exe"
) else if exist "runtime\python\python.exe" (
  set "PYEXE=runtime\python\python.exe"
) else (
  set "PYEXE=python"
)
echo Generating Excel / DXF / PDF / MP4 outputs from one simulation run ...
"%PYEXE%" scripts\make_release.py %*
echo.
pause
