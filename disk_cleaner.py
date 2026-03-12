# -*- coding: utf-8 -*-
"""
Windows C盘清理工具 (DiskCleaner)
功能：
1. 扫描识别垃圾文件
2. 扫描大文件
3. 一键清理
"""

import os
import sys
import threading
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    print("请先安装 psutil: pip install psutil")
    sys.exit(1)

# 尝试导入 tkinter
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    from tkinter.scrolledtext import ScrolledText
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("警告: tkinter 不可用，将使用命令行模式")


class DiskCleaner:
    """C盘清理工具主类"""
    
    # 垃圾文件路径配置
    JUNK_PATHS = [
        # Windows 更新
        (r"C:\Windows\SoftwareDistribution\Download", "Windows 更新缓存", True),
        # 临时文件
        (r"C:\Windows\Temp", "Windows 临时文件", True),
        (r"%TEMP%", "用户临时文件", True),
        (r"C:\Users\{}\AppData\Local\Temp", "用户临时文件", True),
        # 回收站
        (r"C:\$Recycle.Bin", "回收站", False),  # 需要管理员权限
        # 浏览器缓存
        (r"C:\Users\{}\AppData\Local\Google\Chrome\User Data\Default\Cache", "Chrome 缓存", False),
        (r"C:\Users\{}\AppData\Local\Microsoft\Edge\User Data\Default\Cache", "Edge 缓存", False),
        (r"C:\Users\{}\AppData\Local\Mozilla\Firefox\Profiles", "Firefox 缓存", False),
        # Windows 日志
        (r"C:\Windows\Logs", "Windows 日志", True),
        (r"C:\Windows\Prefetch", "预读取文件", True),
        # 系统缓存
        (r"C:\Users\{}\AppData\Local\Microsoft\Windows\INetCache", "IE/Edge 缓存", False),
    ]
    
    def __init__(self):
        self.results = {
            'junk_files': [],
            'large_files': [],
            'total_junk_size': 0,
            'total_large_size': 0
        }
        self.username = os.environ.get('USERNAME', 'Default')
        self.scan_callback = None
        self.status_callback = None
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
    
    def get_real_path(self, path_template):
        """获取实际路径"""
        path_template = path_template.replace("{}", self.username)
        path_template = os.path.expandvars(path_template)
        return path_template
    
    def scan_junk_files(self):
        """扫描垃圾文件"""
        self.results['junk_files'] = []
        self.results['total_junk_size'] = 0
        
        self._update_status("正在扫描垃圾文件...")
        
        for path_template, description, needs_admin in self.JUNK_PATHS:
            try:
                path = self.get_real_path(path_template)
                if not os.path.exists(path):
                    continue
                
                size = 0
                count = 0
                
                for root, dirs, files in os.walk(path):
                    try:
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                size += os.path.getsize(fp)
                                count += 1
                            except (PermissionError, OSError):
                                continue
                    except (PermissionError, OSError):
                        continue
                
                if size > 0:
                    self.results['junk_files'].append({
                        'path': path,
                        'description': description,
                        'size': size,
                        'count': count,
                        'needs_admin': needs_admin
                    })
                    self.results['total_junk_size'] += size
                    
            except Exception as e:
                continue
        
        self._update_status(f"垃圾文件扫描完成: {len(self.results['junk_files'])} 项")
    
    def scan_large_files(self, min_size_mb=100, max_files=50):
        """扫描大文件"""
        self.results['large_files'] = []
        self.results['total_large_size'] = 0
        
        self._update_status("正在扫描大文件...")
        
        # C盘根目录
        drive = r"C:\\"
        large_files = []
        
        try:
            for root, dirs, files in os.walk(drive):
                # 跳过系统目录
                dirs[:] = [d for d in dirs if d not in ['$Recycle.Bin', 'System Volume Information', 'Windows', 'Program Files', 'Program Files (x86)']]
                
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size = os.path.getsize(fp)
                        
                        if size >= min_size_mb * 1024 * 1024:
                            large_files.append({
                                'path': fp,
                                'name': f,
                                'size': size,
                                'modified': os.path.getmtime(fp)
                            })
                    except (PermissionError, OSError, FileNotFoundError):
                        continue
                    
                    # 限制数量
                    if len(large_files) > max_files * 2:
                        break
                        
        except Exception as e:
            pass
        
        # 按大小排序，取最大的
        large_files.sort(key=lambda x: x['size'], reverse=True)
        self.results['large_files'] = large_files[:max_files]
        
        for f in self.results['large_files']:
            self.results['total_large_size'] += f['size']
        
        self._update_status(f"大文件扫描完成: {len(self.results['large_files'])} 个")
    
    def delete_junk_item(self, item_path):
        """删除指定垃圾文件"""
        try:
            path = self.get_real_path(item_path)
            if os.path.exists(path):
                # 使用命令行删除，避免 tkinter 权限问题
                os.system(f'rd /s /q "{path}" 2>nul')
                return True
        except Exception as e:
            return False
        return False
    
    def delete_file(self, file_path):
        """删除指定文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            return False
        return False
    
    def _update_status(self, message):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)
        print(message)


class DiskCleanerGUI:
    """图形界面"""
    
    def __init__(self):
        self.cleaner = DiskCleaner()
        self.cleaner.status_callback = self.update_status
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("C盘清理工具 (DiskCleaner)")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(title_frame, text="🗑️ C盘清理工具", 
                                font=('微软雅黑', 18, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # 磁盘信息
        disk_frame = ttk.LabelFrame(self.root, text="💾 磁盘信息", padding=10)
        disk_frame.pack(fill=tk.X, padx=10, pady=5)
        
        try:
            disk = psutil.disk_usage('C:\\')
            self.disk_label = ttk.Label(disk_frame, 
                text=f"C盘: {self.cleaner.format_size(disk.used)} / {self.cleaner.format_size(disk.total)} ({disk.percent}%)",
                font=('微软雅黑', 12))
            self.disk_label.pack()
        except:
            pass
        
        # 按钮区域
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.scan_junk_btn = ttk.Button(btn_frame, text="🔍 扫描垃圾文件", 
                                        command=self.scan_junk)
        self.scan_junk_btn.pack(side=tk.LEFT, padx=5)
        
        self.scan_large_btn = ttk.Button(btn_frame, text="📁 扫描大文件", 
                                         command=self.scan_large)
        self.scan_large_btn.pack(side=tk.LEFT, padx=5)
        
        self.clean_btn = ttk.Button(btn_frame, text="🗑️ 一键清理", 
                                    command=self.clean_all, state=tk.DISABLED)
        self.clean_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(btn_frame, text="🔄 刷新", 
                                      command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_label = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 结果区域 - Notebooks
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 垃圾文件页面
        self.junk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.junk_frame, text="🗑️ 垃圾文件")
        
        # 垃圾文件列表
        junk_list_frame = ttk.Frame(self.junk_frame)
        junk_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.junk_tree = ttk.Treeview(junk_list_frame, columns=("size", "count", "path"), 
                                       show="tree headings", height=10)
        self.junk_tree.heading("#0", text="类型")
        self.junk_tree.heading("size", text="大小")
        self.junk_tree.heading("count", text="文件数")
        self.junk_tree.heading("path", text="路径")
        
        self.junk_tree.column("#0", width=150)
        self.junk_tree.column("size", width=100)
        self.junk_tree.column("count", width=80)
        self.junk_tree.column("path", width=400)
        
        junk_scroll = ttk.Scrollbar(junk_list_frame, orient=tk.VERTICAL, 
                                     command=self.junk_tree.yview)
        self.junk_tree.configure(yscrollcommand=junk_scroll.set)
        
        self.junk_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        junk_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 大文件页面
        self.large_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.large_frame, text="📁 大文件")
        
        large_list_frame = ttk.Frame(self.large_frame)
        large_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.large_tree = ttk.Treeview(large_list_frame, columns=("size", "modified", "path"), 
                                        show="tree headings", height=10)
        self.large_tree.heading("#0", text="文件名")
        self.large_tree.heading("size", text="大小")
        self.large_tree.heading("modified", text="修改时间")
        self.large_tree.heading("path", text="路径")
        
        self.large_tree.column("#0", width=200)
        self.large_tree.column("size", width=100)
        self.large_tree.column("modified", width=150)
        self.large_tree.column("path", width=400)
        
        large_scroll = ttk.Scrollbar(large_list_frame, orient=tk.VERTICAL, 
                                      command=self.large_tree.yview)
        self.large_tree.configure(yscrollcommand=large_scroll.set)
        
        self.large_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        large_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部说明
        info_frame = ttk.LabelFrame(self.root, text="ℹ️ 说明", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_text = "• 扫描大文件: 查找 C 盘下 >100MB 的文件\n"
        info_text += "• 扫描垃圾: 清理临时文件、浏览器缓存等\n"
        info_text += "• 部分清理需要管理员权限"
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_label.config(text=message)
        self.root.update()
    
    def scan_junk(self):
        """扫描垃圾文件"""
        self.scan_junk_btn.config(state=tk.DISABLED)
        self.update_status("正在扫描垃圾文件...")
        
        # 使用线程避免界面卡顿
        thread = threading.Thread(target=self._scan_junk_thread)
        thread.daemon = True
        thread.start()
    
    def _scan_junk_thread(self):
        """扫描垃圾文件线程"""
        self.cleaner.scan_junk_files()
        
        # 更新界面
        self.root.after(0, self._update_junk_ui)
    
    def _update_junk_ui(self):
        """更新垃圾文件界面"""
        # 清除现有数据
        for item in self.junk_tree.get_children():
            self.junk_tree.delete(item)
        
        # 添加新数据
        for item in self.cleaner.results['junk_files']:
            self.junk_tree.insert("", tk.END, 
                text=item['description'],
                values=(
                    self.cleaner.format_size(item['size']),
                    item['count'],
                    item['path']
                ))
        
        total = self.cleaner.results['total_junk_size']
        self.update_status(f"垃圾文件扫描完成: 共 {self.cleaner.format_size(total)}")
        self.scan_junk_btn.config(state=tk.NORMAL)
        self.clean_btn.config(state=tk.NORMAL)
    
    def scan_large(self):
        """扫描大文件"""
        self.scan_large_btn.config(state=tk.DISABLED)
        self.update_status("正在扫描大文件...")
        
        thread = threading.Thread(target=self._scan_large_thread)
        thread.daemon = True
        thread.start()
    
    def _scan_large_thread(self):
        """扫描大文件线程"""
        self.cleaner.scan_large_files(min_size_mb=100, max_files=30)
        
        self.root.after(0, self._update_large_ui)
    
    def _update_large_ui(self):
        """更新大文件界面"""
        # 清除现有数据
        for item in self.large_tree.get_children():
            self.large_tree.delete(item)
        
        # 添加新数据
        for item in self.cleaner.results['large_files']:
            modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(item['modified']))
            self.large_tree.insert("", tk.END, 
                text=item['name'],
                values=(
                    self.cleaner.format_size(item['size']),
                    modified,
                    item['path']
                ))
        
        total = self.cleaner.results['total_large_size']
        self.update_status(f"大文件扫描完成: 共 {len(self.cleaner.results['large_files'])} 个, {self.cleaner.format_size(total)}")
        self.scan_large_btn.config(state=tk.NORMAL)
    
    def clean_all(self):
        """一键清理"""
        if not messagebox.askyesno("确认", "确定要清理所有垃圾文件吗？\n此操作不可恢复！"):
            return
        
        self.clean_btn.config(state=tk.DISABLED)
        self.update_status("正在清理...")
        
        thread = threading.Thread(target=self._clean_thread)
        thread.daemon = True
        thread.start()
    
    def _clean_thread(self):
        """清理线程"""
        deleted_count = 0
        deleted_size = 0
        
        for item in self.cleaner.results['junk_files']:
            if self.cleaner.delete_junk_item(item['path']):
                deleted_count += 1
                deleted_size += item['size']
        
        self.root.after(0, lambda: self._clean_done(deleted_count, deleted_size))
    
    def _clean_done(self, count, size):
        """清理完成"""
        messagebox.showinfo("完成", f"已清理 {count} 项垃圾文件\n共释放 {self.cleaner.format_size(size)}")
        self.clean_btn.config(state=tk.NORMAL)
        self.refresh()
    
    def refresh(self):
        """刷新"""
        # 刷新磁盘信息
        try:
            disk = psutil.disk_usage('C:\\')
            self.disk_label.config(text=f"C盘: {self.cleaner.format_size(disk.used)} / {self.cleaner.format_size(disk.total)} ({disk.percent}%)")
        except:
            pass
        
        self.update_status("已刷新")
    
    def run(self):
        """运行程序"""
        self.root.mainloop()


class DiskCleanerCLI:
    """命令行版本"""
    
    def __init__(self):
        self.cleaner = DiskCleaner()
    
    def run(self):
        print("=" * 50)
        print("🗑️  C盘清理工具")
        print("=" * 50)
        
        # 扫描垃圾
        print("\n[1/2] 扫描垃圾文件...")
        self.cleaner.scan_junk_files()
        
        print(f"\n发现 {len(self.cleaner.results['junk_files'])} 项垃圾文件:")
        print(f"总大小: {self.cleaner.format_size(self.cleaner.results['total_junk_size'])}\n")
        
        for item in self.cleaner.results['junk_files']:
            print(f"  • {item['description']}: {self.cleaner.format_size(item['size'])}")
        
        # 扫描大文件
        print("\n[2/2] 扫描大文件 (>100MB)...")
        self.cleaner.scan_large_files(min_size_mb=100, max_files=20)
        
        print(f"\n发现 {len(self.cleaner.results['large_files'])} 个大文件:")
        print(f"总大小: {self.cleaner.format_size(self.cleaner.results['total_large_size'])}\n")
        
        for i, item in enumerate(self.cleaner.results['large_files'][:10], 1):
            print(f"  {i}. {item['name']} ({self.cleaner.format_size(item['size'])})")
        
        print("\n" + "=" * 50)


def main():
    """主入口"""
    if TKINTER_AVAILABLE:
        # 尝试使用 GUI 模式
        try:
            app = DiskCleanerGUI()
            app.run()
        except Exception as e:
            print(f"GUI 模式启动失败: {e}")
            print("将使用命令行模式...")
            cli = DiskCleanerCLI()
            cli.run()
    else:
        # 使用命令行模式
        cli = DiskCleanerCLI()
        cli.run()


if __name__ == "__main__":
    main()
