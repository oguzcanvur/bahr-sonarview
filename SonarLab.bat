@echo off
rem SonarLab'i baslatir: tarayicida http://127.0.0.1:8765 acilir. Kapatmak icin bu pencereyi kapatin.
cd /d "%~dp0"
title SonarLab
if not exist ".venv\Scripts\python.exe" (
  echo Python ortami bulunamadi. Once kurulum yapin:  py -m venv .venv  ve  .venv\Scripts\python -m pip install -r sonarlab\requirements.txt
  pause
  exit /b 1
)
echo SonarLab baslatiliyor... Tarayici birazdan acilacak.
echo Kapatmak icin bu pencereyi kapatin.
".venv\Scripts\python.exe" sonarlab\app.py
pause
