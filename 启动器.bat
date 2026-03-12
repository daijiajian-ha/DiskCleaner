@echo off
chcp 65001 >nul
title C盘清理工具
color 3f

echo ========================================
echo   C盘清理工具 - DiskCleaner
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python
    echo 请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时务必勾选: Add Python to PATH
    echo.
    pause
    exit /b 1
)

REM 检查 psutil
python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖 psutil...
    pip install psutil
    if errorlevel 1 (
        echo [错误] 安装 psutil 失败
        pause
        exit /b 1
    )
)

echo [OK] 环境检查通过
echo.
echo 正在启动...
echo.

REM 运行主程序
python "%~dp0disk_cleaner.py"

pause
