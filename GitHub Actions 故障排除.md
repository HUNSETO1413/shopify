# GitHub Actions 构建故障排除指南

## 常见错误及解决方案

### 错误 1: 构建在几秒内失败

**可能原因：**
- Python 版本不兼容
- 缺少必要的文件
- 脚本执行权限问题
- 依赖安装失败

**解决方案：**
1. 检查工作流日志，查看具体错误信息
2. 确保所有 Python 文件都已提交到 Git
3. 检查 `requirements.txt` 是否存在
4. 尝试使用 Python 3.10 而不是 3.11

### 错误 2: "build_mac.py not found"

**原因：** 文件未提交到 Git 仓库

**解决方案：**
```bash
git add build_mac.py build_mac_ci.py
git commit -m "Add macOS build scripts"
git push
```

### 错误 3: 依赖安装失败

**可能原因：**
- 网络问题
- 依赖版本冲突
- 平台特定依赖

**解决方案：**
1. 检查 `requirements.txt` 中的版本要求
2. 尝试放宽版本要求（使用 `>=` 而不是 `==`）
3. 添加重试机制

### 错误 4: PyInstaller 打包失败

**可能原因：**
- 缺少隐藏导入
- 文件路径问题
- 权限问题

**解决方案：**
1. 检查工作流日志中的详细错误
2. 确保所有模块都已添加到 `--hidden-import`
3. 检查文件路径是否正确

### 错误 5: 应用包未创建

**可能原因：**
- 打包过程出错但未报错
- 输出路径不正确
- 权限问题

**解决方案：**
1. 检查 `dist` 文件夹内容
2. 查看构建日志
3. 确保有写入权限

## 调试步骤

### 1. 查看详细日志

在 GitHub Actions 页面：
1. 点击失败的构建
2. 展开每个步骤
3. 查看详细输出

### 2. 本地测试

在本地 macOS 上测试：
```bash
python build_mac_ci.py
```

### 3. 检查文件

确保以下文件存在：
- ✅ `shop_tools_gui.py`
- ✅ `data_cleaner.py`
- ✅ `shopify_partners_scraper_auto.py`
- ✅ `shop_contact_scraper_google_login_v7_7.py`
- ✅ `build_mac_ci.py` 或 `build_mac.py`
- ✅ `requirements.txt`

### 4. 验证依赖

检查 `requirements.txt` 是否包含所有依赖：
```bash
cat requirements.txt
```

## 更新的工作流特性

我已经更新了工作流文件，添加了：

1. **更好的错误处理**
   - 每个步骤都有错误检查
   - 失败时上传日志

2. **调试信息**
   - 显示 Python 版本
   - 列出文件
   - 检查脚本是否存在

3. **CI 优化脚本**
   - `build_mac_ci.py` 专门为 CI/CD 优化
   - 移除了平台检查（在 CI 中总是通过）
   - 更好的错误报告

4. **容错处理**
   - DMG 创建失败不会导致整个构建失败
   - 即使部分失败也会上传可用的文件

## 快速修复

如果构建失败，按以下步骤操作：

1. **检查最新提交**
   ```bash
   git status
   git add .
   git commit -m "Fix build"
   git push
   ```

2. **查看工作流日志**
   - 在 GitHub 网页上查看详细错误

3. **使用 CI 优化脚本**
   - 确保 `build_mac_ci.py` 已提交
   - 工作流会自动使用它

4. **简化测试**
   - 可以先注释掉 DMG 创建步骤
   - 只构建 .app 包

## 联系支持

如果问题持续存在：
1. 查看完整的构建日志
2. 检查是否有特定的错误消息
3. 尝试在本地 macOS 上重现问题
