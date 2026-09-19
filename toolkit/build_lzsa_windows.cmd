@echo off
setlocal
rem Arguments: Visual Studio root, LZSA source root, build directory.
if "%~3"=="" exit /b 2
call "%~1\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
if not exist "%~3" mkdir "%~3"
pushd "%~3"
cl /nologo /O2 /MT /D_CRT_SECURE_NO_WARNINGS /DNDEBUG /I"%~2\src" /I"%~2\src\libdivsufsort\include" "%~2\src\*.c" "%~2\src\libdivsufsort\lib\*.c" /Fe:lzsa.exe
set "build_result=%errorlevel%"
popd
exit /b %build_result%
