# IM 数据清理 - 调研报告

## 1. 企业微信 (WeCom)

### 数据存储位置（动态搜索）
| 类型 | 路径 |
|------|------|
| 用户目录 | `%USERPROFILE%\Documents\WXWork\` |
| 应用数据 | `%APPDATA%\Tencent\WeCom\` |
| 本地缓存 | `%LOCALAPPDATA%\Tencent\WeCom\` |

### 搜索策略
1. 先检查 `%USERPROFILE%\Documents\WXWork\`（用户目录优先）
2. 再检查 `%APPDATA%\Tencent\WeCom\`（漫游数据）
3. 最后检查 `%LOCALAPPDATA%\Tencent\WeCom\`（本地缓存）
4. 扫描所有存在的路径，汇总可清理数据

### 可清理数据
- 缓存文件（`Cache`, `Blob`, `Image` 等文件夹）
- 日志文件（`logs`）
- 聊天记录文件（`.dat` 文件）

### 判断"长期未使用"方式
- 检查登录账号的最后活跃时间
- 检查特定联系人/群聊的最后消息时间
- 需要读取 WeCom 的本地数据库（SQLite）

---

## 2. 微信 (WeChat)

### 数据存储位置（动态搜索）
| 类型 | 路径 |
|------|------|
| 应用数据 | `%APPDATA%\Tencent\WeChat\` |
| 用户文件 | `%APPDATA%\Tencent\WeChat\Files\` |
| 本地缓存 | `%LOCALAPPDATA%\Tencent\WeChat\` |

### 搜索策略
- 扫描上述所有路径，检测实际存在的目录

### 可清理数据
- 缓存图片/视频
- 聊天记录（可选择性清理）
- 表情包

### 判断"长期未使用"
- 微信无"账号不活跃"概念，只能清理聊天记录

---

## 3. 技术方案

### 读取企微数据
- 使用 Python 读取 `%APPDATA%\Tencent\WeCom\` 目录
- 解析 `config.db` 获取账号信息
- 扫描目录获取文件修改时间

### 判断标准（用户可选）
- **3个月**：激进清理
- **6个月**：常规清理
- **1年以上**：保守清理（默认）
- 未登录账号 → 可清理

### UI 交互设计
- 扫描完成后显示各类数据大小
- 用户选择时间范围后，动态计算可清理空间
- 确认后再执行清理

### 清理方式
- 删除缓存文件夹
- 移动大文件到回收站
- 提供用户确认后再删除

---

## 4. 风险与限制

| 风险 | 说明 |
|------|------|
| 数据丢失 | 误删重要聊天记录 |
| 权限问题 | 需要管理员权限访问 AppData |
| 版本差异 | 不同版本数据格式可能不同 |

---

## 5. 下一步

1. **在你本地运行** DiskCleaner，扫描 `%APPDATA%\Tencent\` 目录
2. **确认数据位置**是否正确
3. **设计具体清理逻辑**

---

## 附录：动态搜索路径

```python
# 企微搜索路径（优先级顺序）
SEARCH_PATHS_WECOM = [
    os.path.expandvars("%USERPROFILE%\\Documents\\WXWork"),
    os.path.expandvars("%APPDATA%\\Tencent\\WeCom"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeCom"),
]

# 微信搜索路径
SEARCH_PATHS_WECHAT = [
    os.path.expandvars("%APPDATA%\\Tencent\\WeChat"),
    os.path.expandvars("%APPDATA%\\Tencent\\WeChat\\Files"),
    os.path.expandvars("%LOCALAPPDATA%\\Tencent\\WeChat"),
]
```
