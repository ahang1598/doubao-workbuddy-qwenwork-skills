@echo off
setlocal

if "%~1"=="" (
  echo Codex app tools could not start: missing MCP server path. 1>&2
  exit /b 64
)

if defined CODEX_MCP_NODE_PATH if exist "%CODEX_MCP_NODE_PATH%" (
  "%CODEX_MCP_NODE_PATH%" %*
  exit /b
)
if defined CODEX_BROWSER_USE_NODE_PATH if exist "%CODEX_BROWSER_USE_NODE_PATH%" (
  "%CODEX_BROWSER_USE_NODE_PATH%" %*
  exit /b
)
if defined CODEX_ELECTRON_RESOURCES_PATH if exist "%CODEX_ELECTRON_RESOURCES_PATH%\cua_node\bin\node.exe" (
  "%CODEX_ELECTRON_RESOURCES_PATH%\cua_node\bin\node.exe" %*
  exit /b
)
if defined CODEX_CLI_PATH for %%I in ("%CODEX_CLI_PATH%") do if exist "%%~dpIcua_node\bin\node.exe" (
  "%%~dpIcua_node\bin\node.exe" %*
  exit /b
)
if defined USERPROFILE if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" %*
  exit /b
)
if defined LOCALAPPDATA for /d %%D in ("%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\*") do if exist "%%~fD\bin\node.exe" (
  "%%~fD\bin\node.exe" %*
  exit /b
)

where node >nul 2>&1
if not errorlevel 1 (
  node %*
  exit /b
)

echo Codex app tools could not find a Node runtime. Reinstall or update Codex. 1>&2
exit /b 127
