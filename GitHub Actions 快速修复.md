# GitHub Actions 快速修复指南

## 当前问题

构建在 8 秒内失败，可能的原因：
1. 脚本执行错误
2. 文件路径问题
3. 依赖安装失败
4. Python 版本问题

## 解决方案

### 方案 1: 使用简化版工作流（推荐）

我已经创建了一个更简单的工作流文件：`.github/workflows/build-macos-simple.yml`

**使用方法：**
1. 删除或重命名旧的工作流文件
2. 将 `build-macos-simple.yml` 重命名为 `build-macos.yml`
3. 提交并推送

```bash
git mv .github/workflows/build-macos.yml .github/workflows/build-macos.yml.old
git mv .github/workflows/build-macos-simple.yml .github/workflows/build-macos.yml
git add .github/workflows/
git commit -m "Use simplified build workflow"
git push
```

### 方案 2: 直接使用 PyInstaller

我已经更新了主工作流，现在直接使用 PyInstaller 命令，不依赖构建脚本。

**优势：**
- 更少的依赖
- 更清晰的错误信息
- 更容易调试

### 方案 3: 查看具体错误

要找出具体错误：

1. **在 GitHub 网页上：**
   - 点击失败的构建（红色 X）
   - 展开每个步骤
   - 查看 "Build macOS app" 步骤的详细输出

2. **常见错误：**

   **错误：找不到文件**
   ```
   解决：确保所有 .py 文件都已提交到 Git
   ```

   **错误：模块导入失败**
   ```
   解决：检查 requirements.txt，确保所有依赖都列出
   ```

   **错误：PyInstaller 失败**
   ```
   解决：查看 build/*/warn-*.txt 文件中的警告
   ```

## 调试步骤

### 1. 检查文件是否提交

```bash
git status
git ls-files | grep -E "\.(py|txt|yml)$"
```

确保以下文件已提交：
- ✅ shop_tools_gui.py
- ✅ data_cleaner.py
- ✅ shopify_partners_scraper_auto.py
- ✅ shop_contact_scraper_google_login_v7_7.py
- ✅ requirements.txt
- ✅ .github/workflows/build-macos.yml

### 2. 本地测试（如果有 Mac）

```bash
# 安装依赖
pip install -r requirements.txt

# 测试导入
python -c "import shop_tools_gui; print('OK')"

# 测试 PyInstaller
pyinstaller --version
```

### 3. 查看构建日志

在 GitHub Actions 页面：
1. 点击失败的构建
2. 点击 "Build macOS app" 步骤
3. 查看完整输出
4. 查找 "ERROR" 或 "FAILED" 关键字

## 快速修复命令

```bash
# 1. 确保所有文件已提交
git add .
git status

# 2. 提交更改
git commit -m "Fix GitHub Actions build"

# 3. 推送
git push

# 4. 在 GitHub 网页触发新的构建
```

## 如果仍然失败

请提供以下信息：

1. **构建日志中的具体错误信息**
   - 复制 "Build macOS app" 步骤的完整输出

2. **文件列表**
   - 运行 `git ls-files` 的输出

3. **错误截图**
   - GitHub Actions 页面的错误信息

## 备用方案

如果 GitHub Actions 持续失败，可以考虑：

1. **使用本地 Mac 打包**
   - 如果有 Mac 电脑，直接在本地运行 `python build_mac.py`

2. **使用云 Mac 服务**
   - MacStadium、AWS EC2 Mac 等

3. **简化应用**
   - 先移除 Selenium 等复杂依赖
   - 只打包核心功能
   - 逐步添加功能
