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

echo [1/3] 安装依赖...
pip install psutil pyinstaller

echo.
echo [2/3] 打包为 EXE (含UPX压缩)...
pyinstaller --onefile --windowed --name DiskCleaner --clean --upx-dir=. disk_cleaner.py

echo.
echo [3/3] 压缩 EXE...
upx -9 -o dist\DiskCleaner_compressed.exe dist\DiskCleaner.exe
if exist dist\DiskCleaner_compressed.exe (
    echo 压缩完成!
    powershell -Command "Write-Host '原始大小:' (Get-Item 'dist\DiskCleaner.exe').Length 'bytes' -ForegroundColor Yellow; Write-Host '压缩后:' (Get-Item 'dist\DiskCleaner_compressed.exe').Length 'bytes' -ForegroundColor Green"
    del dist\DiskCleaner.exe
    ren dist\DiskCleaner_compressed.exe DiskCleaner.exe
)
echo.
echo 生成的 EXE 文件在: dist\DiskCleaner.exe
echo.

pause
