# -*- coding: utf-8 -*-
"""
Windows系统清理助手 (DiskCleaner) - v3 UI版本
功能：
1. 扫描识别垃圾文件
2. 扫描大文件
3. 微信/企微清理
4. 一键清理
"""

import os
import sys
import threading
import time
from pathlib import Path
import ctypes

# 用 ctypes 替代 psutil 获取磁盘空间
try:
    kernel32 = ctypes.windll.kernel32
    GetDiskFreeSpaceEx = kernel32.GetDiskFreeSpaceExW
    GetDiskFreeSpaceEx.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong)]
    GetDiskFreeSpaceEx.restype = ctypes.c_bool
    
    def get_disk_usage(path):
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        total_free = ctypes.c_ulonglong(0)
        if GetDiskFreeSpaceEx(path, ctypes.byref(free_bytes), ctypes.byref(total_bytes), ctypes.byref(total_free)):
            used = total_bytes.value - free_bytes.value
            return type('obj', (object,), {
                'total': total_bytes.value,
                'used': used,
                'free': free_bytes.value,
                'percent': round(used / total_bytes.value * 100, 1) if total_bytes.value > 0 else 0
            })()
        return None
except:
    def get_disk_usage(path):
        return None

# 尝试导入 tkinter
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("警告: tkinter 不可用，将使用命令行模式")

import datetime

# ============== IM 清理配置 ==============
# 企微搜索路径（按优先级）
WECHAT_WORK_PATHS = [
    os.path.expanduser("~/Documents/WXWork"),
    os.path.expanduser("~/Documents/WeChat Files"),
    "C:/Documents and Settings/%USERNAME%/Documents/WXWork",
    "C:/Users/%USERNAME%/Documents/WXWork",
]

# 企微子目录（按用户分组的目录名）
WECHAT_WORK_SUBDIRS = ["CrashDump", " miscellaneous", "Headless", "Storage", "Backup"]

# 微信搜索路径
WECHAT_PATHS = [
    os.path.expanduser("~/Documents/WeChat Files"),
    "C:/Documents and Settings/%USERNAME%/Documents/WeChat Files",
    "C:/Users/%USERNAME%/Documents/WeChat Files",
]

# 微信用户目录（MicroMsg下的每个文件夹对应一个用户）
WECHAT_SUBDIRS = ["MicroMsg", "FileTransfer", "Image", "Video", "Voice"]

# 安全分类规则
SAFE_EXTENSIONS = {'.tmp', '.temp', '.log', '.bak', '.old', '.cache', '.thumbs'}
DANGER_EXTENSIONS = {'.exe', '.dll', '.sys', '.ini', '.cfg'}


class DiskCleaner:
    def __init__(self):
        self.results = {
            'junk_files': [],
            'large_files': [],
            'im_files': {'wecom': {}, 'wechat': {}},
            'total_junk_size': 0,
            'total_large_size': 0,
        }
        self.scanning = False
        self.stop_scan = False
    
    def format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
    
    def get_real_path(self, path_template):
        return path_template.replace("%USERNAME%", os.getenv("USERNAME", ""))
    
    def scan_junk_files(self):
        self.results['junk_files'] = []
        self.results['total_junk_size'] = 0
        
        drive = getattr(self, 'current_drive', 'C')
        paths_to_scan = [
            f"{drive}:/Windows/Temp",
            f"{drive}:/Temp",
            f"{drive}:/Windows/Prefetch",
            os.path.expanduser("~/AppData/Local/Temp"),
        ]
        
        for scan_path in paths_to_scan:
            if not os.path.exists(scan_path):
                continue
            try:
                for root, dirs, files in os.walk(scan_path):
                    for f in files:
                        filepath = os.path.join(root, f)
                        try:
                            size = os.path.getsize(filepath)
                            self.results['junk_files'].append({
                                'path': filepath,
                                'size': size,
                                'type': 'junk'
                            })
                            self.results['total_junk_size'] += size
                        except:
                            pass
            except:
                pass
    
    def scan_large_files(self, min_size_mb=100, max_files=50):
        self.results['large_files'] = []
        self.results['total_large_size'] = 0
        
        drive = getattr(self, 'current_drive', 'C')
        
        large_files = []
        try:
            for root, dirs, files in os.walk(f"{drive}:/"):
                if self.stop_scan:
                    break
                for f in files:
                    if self.stop_scan:
                        break
                    try:
                        filepath = os.path.join(root, f)
                        size = os.path.getsize(filepath)
                        if size >= min_size_mb * 1024 * 1024:
                            large_files.append({
                                'path': filepath,
                                'size': size,
                                'name': f
                            })
                            if len(large_files) > max_files * 2:
                                break
                    except:
                        pass
        except:
            pass
        
        large_files.sort(key=lambda x: x['size'], reverse=True)
        self.results['large_files'] = large_files[:max_files]
        
        for f in self.results['large_files']:
            self.results['total_large_size'] += f['size']
    
    def classify_file(self, filepath, days_threshold=365):
        ext = os.path.splitext(filepath)[1].lower()
        mtime = os.path.getmtime(filepath)
        age_days = (datetime.datetime.now() - datetime.datetime.fromtimestamp(mtime)).days
        
        if ext in DANGER_EXTENSIONS:
            return 'red'
        elif ext in SAFE_EXTENSIONS or age_days > days_threshold:
            return 'green'
        else:
            return 'yellow'
    
    def scan_im_files(self, days_threshold=365):
        results = {
            'wecom': {},
            'wechat': {}
        }
        
        # 扫描企微
        for base_path in WECHAT_WORK_PATHS:
            base_path = self.get_real_path(base_path)
            if os.path.exists(base_path):
                self._scan_wechat_by_user(base_path, results['wecom'], days_threshold)
        
        # 扫描微信
        for base_path in WECHAT_PATHS:
            base_path = self.get_real_path(base_path)
            if os.path.exists(base_path):
                self._scan_wechat_by_user(base_path, results['wechat'], days_threshold)
        
        total_size = 0
        for user_data in results['wecom'].values():
            total_size += sum(f['size'] for f in user_data)
        for user_data in results['wechat'].values():
            total_size += sum(f['size'] for f in user_data)
        
        self.results['im_files'] = results
        return total_size
    
    def _scan_wechat_by_user(self, base_path, user_results, days_threshold):
        try:
            for user_dir in os.listdir(base_path):
                user_path = os.path.join(base_path, user_dir)
                if not os.path.isdir(user_path):
                    continue
                
                if user_dir not in user_results:
                    user_results[user_dir] = []
                
                for subdir in WECHAT_WORK_SUBDIRS + WECHAT_SUBDIRS:
                    subdir_path = os.path.join(user_path, subdir)
                    if not os.path.exists(subdir_path):
                        continue
                    
                    try:
                        for root, dirs, files in os.walk(subdir_path):
                            for f in files:
                                filepath = os.path.join(root, f)
                                try:
                                    size = os.path.getsize(filepath)
                                    classification = self.classify_file(filepath, days_threshold)
                                    user_results[user_dir].append({
                                        'path': filepath,
                                        'size': size,
                                        'classification': classification,
                                        'subdir': subdir
                                    })
                                except:
                                    pass
                    except:
                        pass
        except:
            pass
    
    def delete_files(self, file_list):
        deleted_count = 0
        deleted_size = 0
        for f in file_list:
            if f.get('selected', True):
                try:
                    os.remove(f['path'])
                    deleted_count += 1
                    deleted_size += f['size']
                except:
                    pass
        return deleted_count, deleted_size


class DiskCleanerGUI:
    def __init__(self):
        self.cleaner = DiskCleaner()
        self.cleaner.current_drive = 'C'
        self.current_tab = 'junk'
        
        if not TKINTER_AVAILABLE:
            print("tkinter 不可用，请安装 Python tkinter")
            return
        
        self.root = tk.Tk()
        self.root.title("🧹 Windows系统清理助手")
        self.root.geometry("800x600")
        self.root.configure(bg='#F5F7FA')
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 颜色配置
        self.colors = {
            'primary': '#0078D4',
            'accent': '#FF8C00',
            'bg': '#F5F7FA',
            'card_bg': '#FFFFFF',
            'text': '#1A1A1A',
            'green': '#28A745',
            'yellow': '#FFC107',
            'red': '#DC3545'
        }
        
        self._create_ui()
    
    def _create_ui(self):
        # 标题栏
        title_frame = tk.Frame(self.root, bg=self.colors['primary'], height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="🧹 Windows系统清理助手", 
                               font=("Microsoft YaHei", 18, "bold"),
                               bg=self.colors['primary'], fg="white")
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # 盘符选择
        drive_frame = tk.Frame(self.root, bg=self.colors['bg'])
        drive_frame.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        tk.Label(drive_frame, text="选择盘符:", font=("Microsoft YaHei", 12),
                bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.drive_buttons = {}
        drives = ['C', 'D', 'E', 'F', 'G']
        for drive in drives:
            usage = self._get_drive_usage(f"{drive}:/")
            if usage is not None:
                btn = tk.Button(drive_frame, text=f"{drive}: {usage}%",
                               font=("Microsoft YaHei", 10),
                               bg=self._get_usage_color(usage),
                               fg="white" if usage > 50 else "black",
                               relief=tk.FLAT, padx=15, pady=5,
                               command=lambda d=drive: self._select_drive(d))
                btn.pack(side=tk.LEFT, padx=5)
                self.drive_buttons[drive] = btn
        
        # 选中 C 盘
        if 'C' in self.drive_buttons:
            self.drive_buttons['C'].config(relief=tk.SUNKEN)
        
        # Tab 切换
        tab_frame = tk.Frame(self.root, bg=self.colors['bg'])
        tab_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.tab_junk = tk.Button(tab_frame, text="🗑️ 垃圾清理",
                                  font=("Microsoft YaHei", 11), bg=self.colors['primary'], fg="white",
                                  relief=tk.FLAT, padx=20, pady=8,
                                  command=lambda: self._switch_tab('junk'))
        self.tab_junk.pack(side=tk.LEFT, padx=5)
        
        self.tab_large = tk.Button(tab_frame, text="📁 大文件清理",
                                   font=("Microsoft YaHei", 11), bg='#CCCCCC', fg="black",
                                   relief=tk.FLAT, padx=20, pady=8,
                                   command=lambda: self._switch_tab('large'))
        self.tab_large.pack(side=tk.LEFT, padx=5)
        
        self.tab_im = tk.Button(tab_frame, text="💬 微信/企微清理",
                                font=("Microsoft YaHei", 11), bg='#CCCCCC', fg="black",
                                relief=tk.FLAT, padx=20, pady=8,
                                command=lambda: self._switch_tab('im'))
        self.tab_im.pack(side=tk.LEFT, padx=5)
        
        # 设置区域
        self.settings_frame = tk.Frame(self.root, bg=self.colors['card_bg'], relief=tk.FLAT)
        self.settings_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self._create_junk_settings()
        self._create_large_settings()
        self._create_im_settings()
        
        # 进度条
        self.progress_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.progress_label = tk.Label(self.progress_frame, text="就绪",
                                       font=("Microsoft YaHei", 10), bg=self.colors['bg'])
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # 结果列表
        self.result_frame = tk.Frame(self.root, bg=self.colors['card_bg'], relief=tk.FLAT)
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_list = tk.Listbox(self.result_frame, font=("Microsoft YaHei", 10),
                                      yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        self.result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.result_list.yview)
        
        # 底部按钮
        btn_frame = tk.Frame(self.root, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.scan_btn = tk.Button(btn_frame, text="🔍 开始扫描",
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg=self.colors['accent'], fg="white",
                                  relief=tk.FLAT, padx=30, pady=10,
                                  command=self._start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.clean_btn = tk.Button(btn_frame, text="🗑️ 删除选中",
                                  font=("Microsoft YaHei", 12),
                                  bg=self.colors['red'], fg="white",
                                  relief=tk.FLAT, padx=30, pady=10,
                                  state=tk.DISABLED, command=self._delete_selected)
        self.clean_btn.pack(side=tk.RIGHT, padx=5)
        
        self.total_label = tk.Label(btn_frame, text="共 0 项，0 B",
                                    font=("Microsoft YaHei", 10), bg=self.colors['bg'])
        self.total_label.pack(side=tk.RIGHT, padx=20)
    
    def _get_drive_usage(self, path):
        try:
            usage = get_disk_usage(path)
            return int(usage.percent) if usage else None
        except:
            return None
    
    def _get_usage_color(self, percent):
        if percent >= 90:
            return '#DC3545'  # red
        elif percent >= 70:
            return '#FFC107'  # yellow
        else:
            return '#28A745'  # green
    
    def _select_drive(self, drive):
        for d, btn in self.drive_buttons.items():
            btn.config(relief=tk.FLAT)
        self.drive_buttons[drive].config(relief=tk.SUNKEN)
        self.cleaner.current_drive = drive
    
    def _switch_tab(self, tab):
        self.current_tab = tab
        
        # 更新 Tab 样式
        self.tab_junk.config(bg='#CCCCCC' if tab != 'junk' else self.colors['primary'],
                            fg="black" if tab != 'junk' else "white")
        self.tab_large.config(bg='#CCCCCC' if tab != 'large' else self.colors['primary'],
                              fg="black" if tab != 'large' else "white")
        self.tab_im.config(bg='#CCCCCC' if tab != 'im' else self.colors['primary'],
                           fg="black" if tab != 'im' else "white")
        
        # 显示/隐藏设置
        if tab == 'junk':
            self.junk_settings.pack(fill=tk.X, padx=10, pady=10)
            self.large_settings.pack_forget()
            self.im_settings.pack_forget()
        elif tab == 'large':
            self.junk_settings.pack_forget()
            self.large_settings.pack(fill=tk.X, padx=10, pady=10)
            self.im_settings.pack_forget()
        else:
            self.junk_settings.pack_forget()
            self.large_settings.pack_forget()
            self.im_settings.pack(fill=tk.X, padx=10, pady=10)
        
        # 清空结果
        self.result_list.delete(0, tk.END)
        self.total_label.config(text="共 0 项，0 B")
    
    def _create_junk_settings(self):
        self.junk_settings = tk.Frame(self.result_frame, bg=self.colors['card_bg'])
        
        tk.Label(self.junk_settings, text="扫描 Windows 临时文件、浏览器缓存等",
                font=("Microsoft YaHei", 10), bg=self.colors['card_bg'],
                fg='#666666').pack(anchor=tk.W, padx=10, pady=5)
    
    def _create_large_settings(self):
        self.large_settings = tk.Frame(self.result_frame, bg=self.colors['card_bg'])
        
        tk.Label(self.large_settings, text="扫描大于指定大小的文件:",
                font=("Microsoft YaHei", 10), bg=self.colors['card_bg']).pack(anchor=tk.W, padx=10, pady=5)
        
        size_frame = tk.Frame(self.large_settings, bg=self.colors['card_bg'])
        size_frame.pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Label(size_frame, text="最小文件大小:", bg=self.colors['card_bg']).pack(side=tk.LEFT)
        self.size_input = tk.Entry(size_frame, width=10)
        self.size_input.insert(0, "100")
        self.size_input.pack(side=tk.LEFT, padx=5)
        tk.Label(size_frame, text="MB", bg=self.colors['card_bg']).pack(side=tk.LEFT)
    
    def _create_im_settings(self):
        self.im_settings = tk.Frame(self.result_frame, bg=self.colors['card_bg'])
        
        tk.Label(self.im_settings, text="扫描微信/企业微信文件:",
                font=("Microsoft YaHei", 10), bg=self.colors['card_bg']).pack(anchor=tk.W, padx=10, pady=5)
        
        days_frame = tk.Frame(self.im_settings, bg=self.colors['card_bg'])
        days_frame.pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Label(days_frame, text="清理", bg=self.colors['card_bg']).pack(side=tk.LEFT)
        self.days_input = tk.Entry(days_frame, width=10)
        self.days_input.insert(0, "365")
        self.days_input.pack(side=tk.LEFT, padx=5)
        tk.Label(days_frame, text="天前的文件", bg=self.colors['card_bg']).pack(side=tk.LEFT)
        
        # 安全提示
        tk.Label(self.im_settings, text="⚠️ 建议备份重要文件后再清理",
                font=("Microsoft YaHei", 9), bg=self.colors['card_bg'],
                fg=self.colors['yellow']).pack(anchor=tk.W, padx=10, pady=5)
    
    def _start_scan(self):
        if self.cleaner.scanning:
            return
        
        self.scan_btn.config(state=tk.DISABLED, text="扫描中...")
        self.result_list.delete(0, tk.END)
        self.progress_bar['value'] = 0
        
        def scan():
            self.cleaner.scanning = True
            self.cleaner.stop_scan = False
            
            try:
                if self.current_tab == 'junk':
                    self._update_progress("正在扫描垃圾文件...", 10)
                    self.cleaner.scan_junk_files()
                    self._update_progress("扫描完成", 100)
                    self._show_results('junk')
                
                elif self.current_tab == 'large':
                    try:
                        min_size = int(self.size_input.get() or 100)
                    except:
                        min_size = 100
                    
                    self._update_progress(f"正在扫描大文件 ({min_size}MB+)...", 10)
                    self.cleaner.scan_large_files(min_size_mb=min_size)
                    self._update_progress("扫描完成", 100)
                    self._show_results('large')
                
                elif self.current_tab == 'im':
                    try:
                        days = int(self.days_input.get() or 365)
                    except:
                        days = 365
                    
                    self._update_progress("正在扫描微信/企微文件...", 30)
                    self.cleaner.scan_im_files(days_threshold=days)
                    self._update_progress("扫描完成", 100)
                    self._show_results('im')
            
            except Exception as e:
                self._update_progress(f"错误: {str(e)}", 0)
            
            finally:
                self.cleaner.scanning = False
                self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL, text="🔍 开始扫描"))
        
        thread = threading.Thread(target=scan, daemon=True)
        thread.start()
    
    def _update_progress(self, text, percent):
        self.root.after(0, lambda: self.progress_label.config(text=text))
        self.root.after(0, lambda: self.progress_bar.config(value=percent))
    
    def _show_results(self, tab):
        self.result_list.delete(0, tk.END)
        
        if tab == 'junk':
            files = self.cleaner.results['junk_files']
            for f in files:
                self.result_list.insert(tk.END, f"☑ {f['path'][:70]}... ({self.cleaner.format_size(f['size'])})")
        
        elif tab == 'large':
            files = self.cleaner.results['large_files']
            for f in files:
                self.result_list.insert(tk.END, f"☑ {f['name'][:50]} ({self.cleaner.format_size(f['size'])})")
        
        elif tab == 'im':
            files = self.cleaner.results['im_files']
            count = 0
            for im_type, users in files.items():
                for user, user_files in users.items():
                    for f in user_files:
                        count += 1
                        if count <= 100:
                            self.result_list.insert(tk.END, 
                                f"☑ {user[:15]}.../{f['subdir']} ({self.cleaner.format_size(f['size'])})")
        
        total = len(files) if tab != 'im' else count
        size = self.cleaner.results.get('total_junk_size' if tab == 'junk' else 'total_large_size', 0)
        
        self.total_label.config(text=f"共 {total} 项，{self.cleaner.format_size(size)}")
        self.clean_btn.config(state=tk.NORMAL)
    
    def _delete_selected(self):
        selected = self.result_list.curselection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的文件")
            return
        
        if not messagebox.askyesno("确认", "确定要删除选中的文件吗？"):
            return
        
        files_to_delete = []
        
        if self.current_tab == 'junk':
            files_to_delete = self.cleaner.results['junk_files']
        elif self.current_tab == 'large':
            files_to_delete = self.cleaner.results['large_files']
        
        deleted, size = self.cleaner.delete_files(files_to_delete)
        
        messagebox.showinfo("完成", f"已删除 {deleted} 个文件，释放 {self.cleaner.format_size(size)}")
        
        # 重新扫描
        self._start_scan()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if TKINTER_AVAILABLE:
        app = DiskCleanerGUI()
        app.run()
    else:
        print("tkinter 不可用")
