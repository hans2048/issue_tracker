@echo off
:: Activate venv via PowerShell and launch VS Code
start /b powershell -ExecutionPolicy Bypass -Command "& { . .\.venv\Scripts\Activate.ps1; code . }"
exit
