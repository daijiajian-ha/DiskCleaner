# DiskCleaner 设计文档

## 功能概述

智能磁盘清理工具，自动识别可清理文件，提供安全的清理建议。

---

## 一、核心功能

### 1.1 大文件扫描
- 扫描指定目录，列出大于设定阈值的文件
- 按大小排序，显示文件路径、大小、最后修改时间

### 1.2 IM 数据清理
- **支持**：企业微信、微信
- **动态路径搜索**：自动检测实际存在的目录
- **时间范围**：用户可选 3个月 / 6个月 / 1年以上

### 1.3 安全分类（参考360逻辑）

| 分类 | 标识 | 规则 |
|------|------|------|
| ✅ 安全清理 | 绿色 | 临时文件、缓存、Logs |
| ⚠️ 谨慎清理 | 黄色 | 大文件 >100MB，需用户确认 |
| ❌ 建议保留 | 红色 | 系统文件、受保护文件 |

---

## 二、安全规则

### 2.1 系统文件（红色-强制跳过）

```python
SYSTEM_PROTECTED_FILES = [
    "pagefile.sys",      # 页面文件
    "hiberfil.sys",     # 休眠文件
    "swapfile.sys",     # 交换文件
    "desktop.ini",      # 桌面配置
    "thumbs.db",        # 缩略图缓存
    "$Recycle.Bin",     # 回收站
    "System Volume Information",  # 系统还原
]

# 扩展名规则
SYSTEM_EXTENSIONS = [".sys", ".drv", ".ini"]
```

### 2.2 正在使用的文件（红色-跳过）

- 最近24小时内被访问/修改的文件
- 正在运行的程序相关文件

### 2.3 隐藏文件（黄色-谨慎处理）

- 除非在明确的用户缓存目录
- 包含 `.` 开头的文件

### 2.4 可安全清理的文件（绿色）

| 来源 | 路径 | 说明 |
|------|------|------|
| 企微缓存 | `%LOCALAPPDATA%\Tencent\WeCom\Cache` | 图片缓存 |
| 企微日志 | `%LOCALAPPDATA%\Tencent\WeCom\logs` | 运行日志 |
| 微信缓存 | `%LOCALAPPDATA%\Tencent\WeChat\Cache` | 图片缓存 |
| 临时文件 | `%TEMP%` | 临时文件 |
| Windows 临时 | `%WINDIR%\Temp` | 系统临时 |

---

## 三、IM 清理流程

### 3.1 动态路径搜索

```python
# 企微搜索路径（按优先级）
WECOM_SEARCH_PATHS = [
    os.path.expandvars("%USERPROFILE%\\Documents\\WXWork"),
    os.path.expandvars("%APPDATA%\\Tencent\\WeCom"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeCom"),
]

# 微信搜索路径
WECHAT_SEARCH_PATHS = [
    os.path.expandvars("%APPDATA%\\Tencent\\WeChat"),
    os.path.expandvars("%APPDATA%\\Tencent\\WeChat\\Files"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeChat"),
]
```

### 3.2 可清理目录

| 目录 | 分类 | 说明 |
|------|------|------|
| `Cache` | 绿色 | 图片/视频缓存 |
| `logs` | 绿色 | 运行日志 |
| `Blob` | 绿色 | 消息存储 |
| `Image` | 绿色 | 聊天图片 |
| `File` | 黄色 | 用户文件，需确认 |

### 3.3 时间范围选项

| 选项 | 天数 | 说明 |
|------|------|------|
| 激进 | 90天 | 3个月 |
| 常规 | 180天 | 6个月 |
| 保守 | 365天 | 1年以上（默认） |

---

## 四、UI 交互流程

### 4.1 主界面

```
┌─────────────────────────────────────────┐
│  DiskCleaner v2.0                      │
├─────────────────────────────────────────┤
│  [大文件扫描]  [IM清理]  [自定义清理]   │
│                                         │
│  扫描完成：共 X GB 可清理               │
│                                         │
│  ┌─ 建议保留（红色） ─────────────────┐ │
│  │ ⚠️ pagefile.sys                    │ │
│  │ ⚠️ hiberfil.sys                    │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ┌─ 可清理（绿色） ───────────────────┐ │
│  │ ✅ WeCom/logs (200MB)             │ │
│  │ ✅ WeCom/Cache (150MB)            │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  [全选] [反选]  [开始清理]              │
└─────────────────────────────────────────┘
```

### 4.2 IM 清理子界面

```
┌─────────────────────────────────────────┐
│  IM 数据清理 - 企业微信/微信             │
├─────────────────────────────────────────┤
│  时间范围：[3个月] [6个月] [1年以上]    │
│                                         │
│  扫描结果：                             │
│                                         │
│  ✅ 企微 Cache: 200MB                   │
│  ✅ 企微 logs: 50MB                    │
│  ✅ 微信 Cache: 100MB                  │
│  ───────────────────────────────────    │
│  总计: 350MB                            │
│                                         │
│  ⚠️ 清理后聊天记录将无法恢复            │
│                                         │
│        [预览文件]  [开始清理]            │
└─────────────────────────────────────────┘
```

---

## 五、清理执行

### 5.1 删除模式

| 模式 | 行为 |
|------|------|
| 安全删除 | 移动到回收站 |
| 彻底删除 | 直接删除（不可恢复） |

### 5.2 确认机制

- **小文件** (<10MB)：直接清理，无需确认
- **中等文件** (10-100MB)：显示列表，用户确认
- **大文件** (>100MB)：强制确认，并显示警告

---

## 六、版本规划

### v2.0 优先实现
1. 大文件扫描 + 安全分类
2. 企微/微信动态路径扫描
3. 时间范围选择
4. 基础 UI

### v2.1 后续迭代
1. 自定义清理目录
2. 清理历史记录
3. 定时清理任务

---

## 七、技术实现要点

### 7.1 文件安全判断

```python
def classify_file(filepath):
    """返回: 'green'(安全) / 'yellow'(谨慎) / 'red'(保留)"""
    
    filename = os.path.basename(filepath)
    
    # 红色：系统文件
    if filename in SYSTEM_PROTECTED_FILES:
        return 'red'
    if filepath.endswith(SYSTEM_EXTENSIONS):
        return 'red'
    
    # 红色：最近24小时访问
    if is_recently_used(filepath, hours=24):
        return 'red'
    
    # 黄色：隐藏文件
    if filename.startswith('.') and not is_user_cache(filepath):
        return 'yellow'
    
    # 绿色：已知可清理目录
    if is_known_cleanup_dir(filepath):
        return 'green'
    
    # 黄色：默认
    return 'yellow'
```

### 7.2 路径检测

```python
def scan_im_data():
    """扫描所有IM数据路径"""
    results = []
    
    # 企微
    for path in WECOM_SEARCH_PATHS:
        if os.path.exists(path):
            results.extend(scan_directory(path))
    
    # 微信
    for path in WECHAT_SEARCH_PATHS:
        if os.path.exists(path):
            results.extend(scan_directory(path))
    
    return results
```
