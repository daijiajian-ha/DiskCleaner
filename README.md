# Windows C盘清理工具 (DiskCleaner)

## 环境要求
- Python 3.8+
- Windows 10/11

## 安装依赖
```bash
pip install psutil
```

## 打包为 EXE
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DiskCleaner disk_cleaner.py
```

## 使用说明
双击运行 DiskCleaner.exe 即可
