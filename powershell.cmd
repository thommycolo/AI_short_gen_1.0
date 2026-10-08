@echo off
if exist "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" goto :winps
if exist "C:\Program Files\PowerShell\7\pwsh.exe" goto :pwsh7
goto :fallback

:winps
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" %*
exit /b %ERRORLEVEL%

:pwsh7
"C:\Program Files\PowerShell\7\pwsh.exe" %*
exit /b %ERRORLEVEL%

:fallback
cmd.exe /c %*
exit /b %ERRORLEVEL%

