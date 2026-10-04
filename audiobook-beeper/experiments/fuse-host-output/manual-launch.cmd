@echo off
setlocal
rem Interactive comparison with the recorded run's explicit audio/machine options.
rem No movie recording, debugger, hidden window, or persistent settings changes.
set "fuse_exe=%ProgramFiles(x86)%\Fuse\fuse.exe"
if not exist "%fuse_exe%" set "fuse_exe=%ProgramFiles%\Fuse\fuse.exe"
set "audio_disk=%~dp0..\..\..\ZX-audiobook-IMA3-overlap-test.trd"
if not exist "%fuse_exe%" (
  echo Installed Fuse executable was not found.
  exit /b 1
)
if not exist "%audio_disk%" (
  echo The overlap test disk was not found in this checkout.
  exit /b 1
)
if /i "%~1"=="--print-command" goto print_command
rem Prevent overlapping emulator instances from confusing the listening test.
tasklist /FI "IMAGENAME eq fuse.exe" /NH | find /I "fuse.exe" >nul
if not errorlevel 1 (
  echo Close the existing Fuse instance before starting this comparison.
  pause
  exit /b 1
)
start "" "%fuse_exe%" --sound --sound-freq 44100 --no-sound-force-8bit --no-autosave-settings --no-confirm-actions --speed 100 --machine 128 --beta128 "%audio_disk%"
exit /b %errorlevel%
:print_command
echo "%fuse_exe%" --sound --sound-freq 44100 --no-sound-force-8bit --no-autosave-settings --no-confirm-actions --speed 100 --machine 128 --beta128 "%audio_disk%"
