@echo off
rem Windows entry point for verifier-hub (POSIX invokes ./bin/verifier).
rem bin/verifier is an extension-less shebang script. Windows does not read
rem shebangs, so executing it directly raises WinError 193; this launcher
rem hands it to the interpreter instead. %~dp0 is this file's own directory,
rem so the call works from any working directory.
where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0verifier" %*
) else (
  py -3 "%~dp0verifier" %*
)
