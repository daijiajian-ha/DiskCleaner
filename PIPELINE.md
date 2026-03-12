# DiskCleaner CI/CD 流程

> 自动化构建发布流程，持续迭代优化

## 流程概览

```
需求 → 代码 → 构建 → 发布 → 验证
```

---

## 1. 触发方式

### 自动触发（推荐）
- 代码 push 到 master 分支
- workflow 配置 `on.push.branches: [master]`

### 手动触发
- 网页：https://github.com/daijiajian-ha/DiskCleaner/actions → Run workflow
- API：`gh api .../dispatch -f ref=master`

---

## 2. 构建配置

### workflow 文件结构
```yaml
name: Build Windows EXE

on:
  push:
    branches: [master]
  workflow_dispatch:
    inputs:
      python_version:
        default: '3.11'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install psutil pyinstaller
      - run: pyinstaller --onefile --windowed --name DiskCleaner disk_cleaner.py --clean
      - uses: actions/upload-artifact@v4
```

### 常见错误排查
| 错误 | 原因 | 修复 |
|------|------|------|
| checkoutBv4 | 拼写错误 | → checkout@v4 |
| piinstaller | 拼写错误 | → pyinstaller |
| 缩进错误 | YAML 格式 | 检查缩进对齐 |
| 权限不足 | Token 无 workflow scope | 用 Classic Token |

---

## 3. 下载与发布

### 获取最新构建
```bash
# 查看最新构建状态
gh run list --repo daijiajian-ha/DiskCleaner

# 下载 EXE
gh run download <run_id> -n DiskCleaner-EXE
```

### 发布方式
1. **GitHub Releases**：手动创建 Release，上传 EXE
2. **阿里云盘/网盘**：分享下载链接
3. **直接分发**：通过微信/QQ 发送

---

## 4. Token 配置

### 必须权限（Classic Token）
- ✅ repo
- ✅ workflow

### 创建链接
https://github.com/settings/tokens/new?scopes=repo,workflow

### 验证命令
```bash
gh auth status
# 确保显示: Token scopes: ...repo, workflow...
```

---

## 5. 本地开发流程

### 修改代码 → 自动发布
```bash
# 1. 克隆仓库（已配置 remote）
cd DiskCleaner

# 2. 修改代码
vim disk_cleaner.py

# 3. 提交推送
git add . && git commit -m "描述" && git push

# 4. 等待构建（约2分钟）
# 查看状态：https://github.com/daijiajian-ha/DiskCleaner/actions

# 5. 下载新版本
gh run download <latest_run_id> -n DiskCleaner-EXE
```

---

## 6. 常用命令速查

```bash
# 查看构建状态
gh run list --repo daijiajian-ha/DiskCleaner

# 查看最新构建详情
gh run view <run_id>

# 下载 EXE
gh run download <run_id> -n DiskCleaner-EXE

# 查看 artifacts
gh api repos/daijiajian-ha/DiskCleaner/actions/runs/<run_id>/artifacts

# 手动触发构建
gh api repos/daijiajian-ha/DiskCleaner/dispatches -f event_type=build
```

---

## 7. 注意事项

1. **Token 安全**：不写入代码，只存本地或环境变量
2. **构建时间**：Windows runner 约 2-3 分钟
3. **Artifact 保留期**：默认 30 天
4. **Python 版本**：建议 3.11，兼容性最好

---

## 迭代记录

| 日期 | 更新内容 |
|------|---------|
| 2026-03-12 | 初始流程创建 |
