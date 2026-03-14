@echo off
title MOV to WebM Converter - Setup
echo ============================================
echo   MOV to WebM Converter - One-Time Setup
echo ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Download it from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found.

:: Check for FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%~dp0ffmpeg.exe" (
        echo [OK] FFmpeg found next to script.
    ) else (
        echo [..] FFmpeg not found. Downloading...
        echo.

        :: Download ffmpeg using Python (no extra dependencies needed)
        python -c "import urllib.request, zipfile, os, shutil; print('Downloading FFmpeg...'); urllib.request.urlretrieve('https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip', 'ffmpeg.zip'); print('Extracting...'); z = zipfile.ZipFile('ffmpeg.zip'); [z.extract(f) for f in z.namelist() if f.endswith('ffmpeg.exe')]; z.close(); os.remove('ffmpeg.zip'); found = [os.path.join(r,f) for r,d,files in os.walk('.') for f in files if f == 'ffmpeg.exe']; shutil.move(found[0], '%~dp0ffmpeg.exe') if found else None; [shutil.rmtree(d) for d in os.listdir('.') if os.path.isdir(d) and d.startswith('ffmpeg-')];"

        if exist "%~dp0ffmpeg.exe" (
            echo [OK] FFmpeg downloaded successfully.
        ) else (
            echo [ERROR] Could not download FFmpeg automatically.
            echo Please download ffmpeg.exe manually from https://ffmpeg.org
            echo and place it in: %~dp0
            pause
            exit /b 1
        )
    )
) else (
    echo [OK] FFmpeg found in PATH.
)

echo.
echo ============================================
echo   Setup complete! You can now run the app.
echo ============================================
echo.

:: Create a shortcut-like launcher
echo @echo off > "%~dp0Convert.bat"
echo start "" pythonw "%~dp0converter.py" >> "%~dp0Convert.bat"
echo [OK] Created "Convert.bat" - double-click it to launch the converter.
echo.
pause
