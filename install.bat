@echo off
setlocal EnableDelayedExpansion

echo =============================
echo   WindowsFetch Installer
echo =============================

:: --- Check admin rights ---
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [*] Admin rights required. Restarting as Admin...
  powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

:: --- Target folder ---
set TARGET=%ProgramData%\WindowsFetch
if not exist "%TARGET%" mkdir "%TARGET%"

echo [*] Target folder: %TARGET%

:: --- Remove old installation if exists ---
if exist "%TARGET%\windowsfetch.py" (
  del /f /q "%TARGET%\windowsfetch.py"
  echo [*] Old windowsfetch.py removed.
)
if exist "%TARGET%\windowsfetch.cmd" (
  del /f /q "%TARGET%\windowsfetch.cmd"
  echo [*] Old windowsfetch.cmd removed.
)

:: --- Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] Python not found. Installing...

  :: Try winget
  echo [*] Installing Python via winget...
  winget install -e --id Python.Python.3.12 -h --accept-source-agreements --accept-package-agreements
  if %errorlevel% neq 0 (
    echo [!] Winget failed, downloading installer...
    set PY_VER=3.12.6
    set PY_INSTALLER=%TEMP%\python-%PY_VER%-amd64.exe
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe -OutFile '%PY_INSTALLER%'" 2>nul
    if exist "%PY_INSTALLER%" (
      echo [*] Running Python installer...
      start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
      del /f /q "%PY_INSTALLER%"
    ) else (
      echo [!] Failed to download Python. Aborting.
      pause
      exit /b 1
    )
  )
)

:: --- Verify Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] Python still not available. Installation failed.
  pause
  exit /b 1
)

:: --- Install Libs ---
pip install psutil colorize cx_Freeze pyinstaller

:: --- Copy windowsfetch.py ---
if not exist "%~dp0windowsfetch.py" (
  echo [!] Missing windowsfetch.py in the same folder as installer!
  pause
  exit /b 1
)

copy /y "%~dp0windowsfetch.py" "%TARGET%\windowsfetch.py" >nul

:: --- Create CMD launcher ---
set CMDFILE=%TARGET%\windowsfetch.cmd
(
echo @echo off
echo python "%%~dp0windowsfetch.py" %%*
) > "%CMDFILE%"

echo [*] Installed:
echo   %TARGET%\windowsfetch.py
echo   %TARGET%\windowsfetch.cmd

:: --- Add target to PATH ---
echo %PATH% | findstr /i "%TARGET%" >nul
if %errorlevel% neq 0 (
  echo [*] Adding %TARGET% to PATH...
  setx PATH "%PATH%;%TARGET%" /M
)

:: --- Defender exclusion ---
powershell -Command ^
 "try { Add-MpPreference -ExclusionPath '%TARGET%' -ErrorAction SilentlyContinue; Write-Output 'Defender exclusion added.' } catch { Write-Output 'Skipped: ' + $_.Exception.Message }"

echo.
echo =============================
echo [*] Installation complete!
echo [*] Restart CMD/PowerShell and run:
echo     windowsfetch
echo =============================

pause
endlocal
