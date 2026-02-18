@echo off
chcp 1251 >nul
cd /d "%~dp0"

echo.
echo ====================================================
echo =                   Parser YMaps                   =
echo ====================================================
echo.

echo Installing dependencies globally...
pip install -U sv-ttk pyinstaller deep_translator playwright openpyxl

echo.
echo Checking for tkinter...
python -c "import tkinter" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: tkinter not found!
)

echo.
echo Setting global Playwright path...

set "PLAYWRIGHT_BROWSERS_PATH=%LOCALAPPDATA%\ms-playwright"
setx PLAYWRIGHT_BROWSERS_PATH "%LOCALAPPDATA%\ms-playwright"

if not exist "%LOCALAPPDATA%\ms-playwright" (
    mkdir "%LOCALAPPDATA%\ms-playwright"
)

echo Installing Chromium globally...
python -m playwright install chromium --force

echo.
echo Compiling to SINGLE EXE file...

for /f "tokens=*" %%i in ('python -c "import sys; print(sys.prefix)"') do set PYTHON_PREFIX=%%i

pyinstaller --clean --noconfirm ^
    --distpath=. ^
    --name="YMaps_Parser" ^
    --onefile ^
    --windowed ^
    --icon="static/yandex_map_pic.ico" ^
    --add-data="static;static" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.filedialog ^
    --hidden-import=sv_ttk ^
    --hidden-import=deep_translator ^
    --hidden-import=playwright ^
    --hidden-import=openpyxl ^
    --exclude-module=unittest ^
    --exclude-module=pydoc ^
    gui.py

if not exist "YMaps_Parser.exe" (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Cleaning up...
if exist "build" rmdir /s /q "build"
if exist "*.spec" del *.spec

echo.
echo Creating desktop shortcut...

set "EXE_PATH=%CD%\YMaps_Parser.exe"
set "DESKTOP_PATH=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=YMaps Parser.lnk"
set "ICON_PATH=%CD%\static\yandex_map_pic.ico"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%DESKTOP_PATH%\%SHORTCUT_NAME%'); ^
$Shortcut.TargetPath = '%EXE_PATH%'; ^
$Shortcut.WorkingDirectory = '%CD%'; ^
$Shortcut.IconLocation = '%ICON_PATH%'; ^
$Shortcut.Save();"

echo.
echo.
echo Executable: %EXE_PATH%
echo.
echo Playwright browsers location:
echo %LOCALAPPDATA%\ms-playwright
echo.
pause