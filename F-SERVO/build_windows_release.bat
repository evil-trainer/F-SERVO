@echo off
setlocal

echo F-SERVO Wii U fork - Windows release build
echo.

where flutter >nul 2>nul
if errorlevel 1 (
  echo ERROR: Flutter was not found in PATH.
  echo Install Flutter for Windows first: https://docs.flutter.dev/get-started/install/windows
  exit /b 1
)

echo Checking Flutter environment...
flutter doctor
if errorlevel 1 exit /b 1

echo.
echo Fetching Dart/Flutter dependencies...
flutter pub get
if errorlevel 1 exit /b 1

echo.
echo Building Windows release executable...
flutter build windows --release
if errorlevel 1 exit /b 1

echo.
echo Build completed.
echo Output folder: build\windows\x64\runner\Release\
endlocal
