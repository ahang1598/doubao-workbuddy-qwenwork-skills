@echo off
chcp 65001 >nul
setlocal
set "PS1=%~dp0install-win.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
