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
echo [2/3] 打包为 EXE...
pyinstaller --onefile --windowed --name DiskCleaner --clean disk_cleaner.py

echo.
echo [3/3] 完成!
echo.
echo 生成的 EXE 文件在: dist\DiskCleaner.exe
echo.

pause
