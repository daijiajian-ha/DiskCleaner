# -*- coding: utf-8 -*-
"""
Windows系统清理助手 (DiskCleaner)
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

import datetime


# ============== IM 清理配置 ==============

# 系统保护文件（红色-建议保留）
SYSTEM_PROTECTED_FILES = [
    "pagefile.sys", "hiberfil.sys", "swapfile.sys",
    "desktop.ini", "thumbs.db", "$Recycle.Bin",
    "System Volume Information"
]

# 系统扩展名
SYSTEM_EXTENSIONS = [".sys", ".drv"]

# 企微搜索路径（按优先级）
WECOM_SEARCH_PATHS = [
    os.path.expandvars("%USERPROFILE%\\Documents\\WXWork"),
    os.path.expandvars("%APPDATA%\\Tencent\\WeCom"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeCom"),
]

# 企微子目录（按用户分组的目录名）
WECOM_USER_DIRS = ["WDFileRecv", "Doc", "Data"]

# 微信搜索路径
WECHAT_SEARCH_PATHS = [
    os.path.expandvars("%APPDATA%\\Tencent\\WeChat"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeChat"),
]

# 微信用户目录（MicroMsg下的每个文件夹对应一个用户）
WECHAT_USER_DIR = "MicroMsg"

# 可清理目录（绿色）
CLEANABLE_DIRS = ["Cache", "logs", "Blob", "Image", "Video", "File"]

# 需要确认的目录（黄色）
CONFIRM_DIRS = ["File", "Data"]


class DiskCleaner:
    """系统清理工具主类"""
    
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
            'total_large_size': 0,
            'im_files': {'green': [], 'yellow': [], 'red': [], 'total_size': 0}
        }
        self.username = os.environ.get('USERNAME', 'Default')
        self.scan_callback = None
        self.status_callback = None
        self.im_days_threshold = 365  # 默认1年
    
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
    
    # ============== IM 清理功能 ==============
    
    def classify_file(self, filepath, days_threshold=365):
        """
        分类文件安全级别
        返回: 'green'(安全清理) / 'yellow'(谨慎) / 'red'(保留)
        """
        try:
            filename = os.path.basename(filepath)
            
            # 红色：系统保护文件
            if filename in SYSTEM_PROTECTED_FILES:
                return 'red', '系统保护文件'
            
            # 红色：系统扩展名
            if any(filename.endswith(ext) for ext in SYSTEM_EXTENSIONS):
                return 'red', '系统文件'
            
            # 红色：最近24小时访问（正在使用）
            mtime = os.path.getmtime(filepath)
            if datetime.datetime.now().timestamp() - mtime < 24*3600:
                return 'red', '最近使用'
            
            # 黄色：隐藏文件（除非在缓存目录）
            if filename.startswith('.') and not self._is_user_cache(filepath):
                return 'red', '隐藏文件'
            
            # 绿色：已知可清理目录
            dirname = os.path.basename(os.path.dirname(filepath))
            if dirname in CLEANABLE_DIRS:
                return 'green', f'缓存目录({dirname})'
            
            # 黄色：需要确认的目录
            if dirname in CONFIRM_DIRS:
                return 'yellow', f'用户目录({dirname})'
            
            # 根据时间判断
            mtime = os.path.getmtime(filepath)
            age_days = (datetime.datetime.now().timestamp() - mtime) / (24*3600)
            
            if age_days > days_threshold:
                return 'green', f'长期未用({int(age_days)}天)'
            else:
                return 'yellow', f'近期文件({int(age_days)}天)'
                
        except Exception as e:
            return 'yellow', '无法判断'
    
    def _is_user_cache(self, filepath):
        """判断是否在用户缓存目录"""
        cache_paths = ["Cache", "Temp", "logs", "Blob"]
        return any(p in filepath for p in cache_paths)
    
    def scan_im_files(self, days_threshold=365):
        """
        扫描 IM 数据（企业微信+微信）
        返回: 按用户分组的结果
        """
        self._update_status("正在扫描 IM 数据...")
        
        # 按用户分组的结果
        results = {
            'wecom': {},   # 企微: {用户: [文件列表]}
            'wechat': {},  # 微信: {用户: [文件列表]}
            'total_size': 0
        }
        
        # 扫描企微
        for base_path in WECOM_SEARCH_PATHS:
            if os.path.exists(base_path):
                self._scan_wecom_by_user(base_path, results['wecom'], days_threshold)
        
        # 扫描微信
        for base_path in WECHAT_SEARCH_PATHS:
            if os.path.exists(base_path):
                self._scan_wechat_by_user(base_path, results['wechat'], days_threshold)
        
        # 统计总大小
        for user_data in results['wecom'].values():
            for f in user_data:
                results['total_size'] += f['size']
        for user_data in results['wechat'].values():
            for f in user_data:
                results['total_size'] += f['size']
        
        wecom_users = len(results['wecom'])
        wechat_users = len(results['wechat'])
        
        self._update_status(f"IM 扫描完成: 企微{len(results['wecom'])}用户, 微信{len(results['wechat'])}用户")
        return results
    
    def _scan_wecom_by_user(self, base_path, user_results, days_threshold):
        """按用户扫描企微数据"""
        try:
            # 遍历企微目录，识别用户目录
            for root, dirs, files in os.walk(base_path):
                # 检查当前目录是否是用户目录
                dirname = os.path.basename(root)
                
                # 跳过系统目录
                if dirname.startswith('.') or dirname in ['System', 'logs', 'Cache']:
                    continue
                
                # 判断是否为用户目录（有文件或子目录）
                user_name = dirname  # 使用目录名作为用户名
                
                if user_name not in user_results:
                    user_results[user_name] = []
                
                # 扫描该用户目录下的文件
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size = os.path.getsize(fp)
                        if size == 0:
                            continue
                        
                        mtime = os.path.getmtime(fp)
                        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                        age_days = (datetime.datetime.now().timestamp() - mtime) / (24*3600)
                        
                        # 根据时间判断分类
                        if age_days > days_threshold:
                            classification = 'green'
                            reason = f"超过{days_threshold}天"
                        else:
                            classification = 'yellow'
                            reason = f"{int(age_days)}天前"
                        
                        file_info = {
                            'path': fp,
                            'name': f,
                            'size': size,
                            'user': user_name,
                            'im': '企微',
                            'mtime': mtime_str,
                            'age_days': int(age_days),
                            'reason': reason,
                            'classification': classification,
                            'relative_path': fp.replace(base_path, '').strip('\\')
                        }
                        
                        user_results[user_name].append(file_info)
                        
                    except (PermissionError, OSError, FileNotFoundError):
                        continue
                
                # 用户目录下可能有子目录，继续递归
                
        except Exception as e:
            pass
    
    def _scan_wechat_by_user(self, base_path, user_results, days_threshold):
        """按用户扫描微信数据"""
        try:
            # 微信: 目录结构是 MicroMsg/微信ID/...
            micromsg_path = os.path.join(base_path, "MicroMsg")
            if not os.path.exists(micromsg_path):
                return
            
            # 遍历微信用户目录
            for root, dirs, files in os.walk(micromsg_path):
                dirname = os.path.basename(root)
                
                # 跳过非用户目录
                if dirname in ['MicroMsg', 'System', '.'] or len(dirname) < 10:
                    continue
                
                # 微信ID通常是很长的字符串，隐藏处理
                wechat_id = dirname[:8] + "***" if len(dirname) > 8 else dirname
                
                if wechat_id not in user_results:
                    user_results[wechat_id] = []
                
                # 扫描该用户目录下的文件（只扫描常见缓存目录）
                cache_dirs = ['Image', 'File', 'Video', 'Voice', 'Avatar']
                
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        size = os.path.getsize(fp)
                        if size == 0:
                            continue
                        
                        mtime = os.path.getmtime(fp)
                        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                        age_days = (datetime.datetime.now().timestamp() - mtime) / (24*3600)
                        
                        # 根据时间判断分类
                        if age_days > days_threshold:
                            classification = 'green'
                            reason = f"超过{days_threshold}天"
                        else:
                            classification = 'yellow'
                            reason = f"{int(age_days)}天前"
                        
                        file_info = {
                            'path': fp,
                            'name': f,
                            'size': size,
                            'user': wechat_id,
                            'im': '微信',
                            'mtime': mtime_str,
                            'age_days': int(age_days),
                            'reason': reason,
                            'classification': classification,
                            'relative_path': fp.replace(base_path, '').strip('\\')
                        }
                        
                        user_results[wechat_id].append(file_info)
                        
                    except (PermissionError, OSError, FileNotFoundError):
                        continue
                
        except Exception as e:
            pass


class DiskCleanerGUI:
    """图形界面"""
    
    def __init__(self):
        self.cleaner = DiskCleaner()
        self.cleaner.status_callback = self.update_status
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("Windows系统清理助手 (DiskCleaner)")
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
        
        title_label = ttk.Label(title_frame, text="🧹 Windows系统清理助手", 
                                font=('微软雅黑', 18, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # 磁盘信息（精简版）
        disk_frame = ttk.Frame(self.root)
        disk_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # 盘符选择
        self.drive_var = tk.StringVar(value="C")
        self.drive_frame = ttk.Frame(disk_frame)
        self.drive_frame.pack(fill=tk.X)
        
        self.drives = {}  # 存储盘符信息
        
        # 添加盘符选择按钮
        self.drive_buttons = {}
        for drive in ['C', 'D', 'E', 'F']:
            try:
                path = drive + ":\\"
                disk = psutil.disk_usage(path)
                btn = ttk.Radiobutton(
                    self.drive_frame, 
                    text=f"{drive}: {disk.percent}%", 
                    value=drive,
                    variable=self.drive_var,
                    command=self.on_drive_changed
                )
                btn.pack(side=tk.LEFT, padx=5)
                self.drive_buttons[drive] = {
                    'btn': btn,
                    'percent': disk.percent,
                    'free': disk.free
                }
            except:
                pass
        
        # 警告提示
        warning_frame = ttk.Frame(self.root)
        warning_frame.pack(fill=tk.X, padx=10, pady=5)
        
        warning_label = tk.Label(
            warning_frame,
            text="⚠️ 清理数据需谨慎，建议定期做好备份，避免数据丢失！",
            bg="#FFF3CD",
            fg="#856404",
            font=('微软雅黑', 10),
            pady=8
        )
        warning_label.pack(fill=tk.X)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 主清理按钮
        self.clean_btn = ttk.Button(
            btn_frame, 
            text="🚀 一键清理选中文件", 
            command=self.clean_all, 
            state=tk.DISABLED
        )
        self.clean_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 扫描按钮行
        scan_frame = ttk.Frame(btn_frame)
        scan_frame.pack(fill=tk.X)
        
        self.scan_junk_btn = ttk.Button(scan_frame, text="🗑️ 垃圾清理", 
                                        command=self.scan_junk)
        self.scan_junk_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.scan_large_btn = ttk.Button(scan_frame, text="📁 大文件清理", 
                                         command=self.scan_large)
        self.scan_large_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.scan_im_btn = ttk.Button(scan_frame, text="💬 微信/企微清理", 
                                      command=self.scan_im)
        self.scan_im_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        # 状态栏
        self.status_label = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 结果区域 - Notebooks
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 垃圾文件页面
        self.junk_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.junk_frame, text="🗑️ 垃圾清理")
        
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
        self.notebook.add(self.large_frame, text="📁 大文件清理")
        
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
        
        # IM 清理页面
        self.im_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.im_frame, text="💬 微信/企微清理")
        
        # IM 页面内容
        im_top_frame = ttk.Frame(self.im_frame)
        im_top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 时间范围选择
        ttk.Label(im_top_frame, text="时间范围:").pack(side=tk.LEFT, padx=5)
        self.im_days_var = tk.StringVar(value="365")
        self.im_days_combo = ttk.Combobox(im_top_frame, textvariable=self.im_days_var, 
                                          values=["90", "180", "365"], 
                                          state="readonly", width=8)
        self.im_days_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(im_top_frame, text="天").pack(side=tk.LEFT)
        
        # IM 扫描按钮
        self.im_scan_btn = ttk.Button(im_top_frame, text="🔍 扫描", 
                                       command=self.scan_im)
        self.im_scan_btn.pack(side=tk.LEFT, padx=10)
        
        # IM 结果统计
        self.im_stats_label = ttk.Label(im_top_frame, text="", font=('微软雅黑', 10))
        self.im_stats_label.pack(side=tk.RIGHT, padx=10)
        
        # IM 文件列表（带分类颜色）
        im_list_frame = ttk.Frame(self.im_frame)
        im_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.im_tree = ttk.Treeview(im_list_frame, columns=("size", "im", "reason"), 
                                     show="tree headings", height=12)
        self.im_tree.heading("#0", text="文件")
        self.im_tree.heading("size", text="大小")
        self.im_tree.heading("im", text="来源")
        self.im_tree.heading("reason", text="分类原因")
        
        self.im_tree.column("#0", width=250)
        self.im_tree.column("size", width=80)
        self.im_tree.column("im", width=60)
        self.im_tree.column("reason", width=150)
        
        # 配置标签颜色
        self.style.configure("Treeview", rowheight=25)
        
        im_scroll = ttk.Scrollbar(im_list_frame, orient=tk.VERTICAL, 
                                   command=self.im_tree.yview)
        self.im_tree.configure(yscrollcommand=im_scroll.set)
        
        self.im_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        im_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # IM 清理按钮
        im_btn_frame = ttk.Frame(self.im_frame)
        im_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.im_clean_btn = ttk.Button(im_btn_frame, text="🗑️ 清理选中", 
                                        command=self.clean_im_selected,
                                        state=tk.DISABLED)
        self.im_clean_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(im_btn_frame, text="💡 绿色:可清理  ⚠️黄色:需确认  ❌红色:保留").pack(side=tk.RIGHT)
        
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
    
    def on_drive_changed(self):
        """盘符切换"""
        drive = self.drive_var.get()
        self.update_status(f"已切换到 {drive} 盘")
    
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
    
    # ============== IM 清理 UI 方法 ==============
    
    def scan_im(self):
        """扫描 IM 数据"""
        days = int(self.im_days_var.get())
        self.cleaner.im_days_threshold = days
        
        self.im_scan_btn.config(state=tk.DISABLED)
        self.update_status(f"正在扫描 {days} 天前的 IM 数据...")
        
        thread = threading.Thread(target=self._scan_im_thread, args=(days,))
        thread.daemon = True
        thread.start()
    
    def _scan_im_thread(self, days):
        """扫描 IM 数据线程"""
        results = self.cleaner.scan_im_files(days_threshold=days)
        self.cleaner.results['im_files'] = results
        
        self.root.after(0, self._update_im_ui)
    
    def _update_im_ui(self):
        """更新 IM 清理界面"""
        # 清除现有数据
        for item in self.im_tree.get_children():
            self.im_tree.delete(item)
        
        results = self.cleaner.results['im_files']
        
        # 分类显示
        for item in results.get('green', []):
            self.im_tree.insert("", tk.END, text=item['relative_path'][:50],
                values=(self.cleaner.format_size(item['size']), item['im'], "✅ " + item['reason']),
                tags=('green',))
        
        for item in results.get('yellow', []):
            self.im_tree.insert("", tk.END, text=item['relative_path'][:50],
                values=(self.cleaner.format_size(item['size']), item['im'], "⚠️ " + item['reason']),
                tags=('yellow',))
        
        for item in results.get('red', []):
            self.im_tree.insert("", tk.END, text=item['relative_path'][:50],
                values=(self.cleaner.format_size(item['size']), item['im'], "❌ " + item['reason']),
                tags=('red',))
        
        # 配置标签颜色
        self.im_tree.tag_configure('green', foreground='green')
        self.im_tree.tag_configure('yellow', foreground='orange')
        self.im_tree.tag_configure('red', foreground='red')
        
        # 更新统计
        green_size = sum(f['size'] for f in results.get('green', []))
        yellow_size = sum(f['size'] for f in results.get('yellow', []))
        
        stats = f"绿色: {self.cleaner.format_size(green_size)} | 黄色: {self.cleaner.format_size(yellow_size)}"
        self.im_stats_label.config(text=stats)
        
        self.update_status(f"IM 扫描完成: 绿色{len(results.get('green',[]))}项, 黄色{len(results.get('yellow',[]))}项, 红色{len(results.get('red',[]))}项")
        self.im_scan_btn.config(state=tk.NORMAL)
        self.im_clean_btn.config(state=tk.NORMAL)
    
    def clean_im_selected(self):
        """清理选中的 IM 文件"""
        selected = self.im_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要清理的文件")
            return
        
        # 获取选中的文件（只清理绿色和黄色的）
        to_delete = []
        for item_id in selected:
            values = self.im_tree.item(item_id)['values']
            path = self.im_tree.item(item_id)['text']
            # 找到完整路径
            for f in self.cleaner.results['im_files'].get('green', []) + \
                     self.cleaner.results['im_files'].get('yellow', []):
                if path in f['relative_path'] or f['relative_path'].endswith(path):
                    to_delete.append(f)
                    break
        
        if not to_delete:
            messagebox.showwarning("提示", "选中的文件无法清理（红色保护）")
            return
        
        if not messagebox.askyesno("确认", f"确定要清理 {len(to_delete)} 个文件吗？\n此操作不可恢复！"):
            return
        
        # 执行清理
        deleted = 0
        deleted_size = 0
        for f in to_delete:
            if self.cleaner.delete_file(f['path']):
                deleted += 1
                deleted_size += f['size']
        
        messagebox.showinfo("完成", f"已清理 {deleted} 个文件\n共释放 {self.cleaner.format_size(deleted_size)}")
        
        # 重新扫描
        self.scan_im()
    
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
        print("🧹  Windows系统清理助手")
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
