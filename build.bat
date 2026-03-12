@echo off
echo ========================================
echo   DiskCleaner 打包脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 安装依赖 (仅 tkinter)...
pip install pyinstaller

echo.
echo [2/4] 打包为 EXE (排除不需要的模块)...
pyinstaller --onefile --windowed --name DiskCleaner --clean ^
  --exclude-module=psutil ^
  --exclude-module=xml ^
  --exclude-module=email ^
  --exclude-module=html ^
  --exclude-module=http ^
  --exclude-module=urllib ^
  --exclude-module=ssl ^
  --exclude-module=cryptography ^
  --exclude-module=pkg_resources ^
  disk_cleaner.py

echo.
echo [3/4] 压缩 EXE (UPX极限压缩)...
upx -9 --force dist\DiskCleaner.exe -o dist\DiskCleaner.exe.upx
if exist dist\DiskCleaner.exe.upx (
    del dist\DiskCleaner.exe
    ren dist\DiskCleaner.exe.upx DiskCleaner.exe
)

echo.
echo [4/4] 完成!
echo.
echo 生成的 EXE 文件: dist\DiskCleaner.exe
powershell -Command "if (Test-Path 'dist\DiskCleaner.exe') { Write-Host '文件大小:' (Get-Item 'dist\DiskCleaner.exe').Length 'bytes' -ForegroundColor Green }"
echo.
echo 生成的 EXE 文件在: dist\DiskCleaner.exe
echo.

pause
