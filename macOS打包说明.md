# macOS 打包说明（Apple Silicon M 芯片）

## 系统要求

- macOS 10.15 或更高版本
- Apple Silicon (M1/M2/M3) 芯片
- Python 3.8 或更高版本
- 已安装 Chrome 浏览器（程序需要）

## 快速开始

### 方法一：使用 Python 脚本（推荐）

1. **打开终端（Terminal）**

2. **进入项目目录**：
   ```bash
   cd /path/to/web10
   ```

3. **运行打包脚本**：
   ```bash
   python build_mac.py
   ```

4. **等待打包完成**

5. **找到应用**：
   - 应用位置：`dist/Shop工具合集.app`
   - 可以拖到 Applications 文件夹使用

### 方法二：单文件打包

如果需要打包成单个可执行文件（而不是 .app 包）：

```bash
python build_mac_onefile.py
```

输出：`dist/Shop工具合集`（可执行文件）

## 创建 DMG 安装包（可选）

如果你想创建一个更专业的安装包：

```bash
python create_dmg.py
```

这会创建一个 `.dmg` 文件，用户可以：
1. 双击 DMG 文件
2. 将应用拖到 Applications 文件夹
3. 完成安装

## 打包选项说明

### .app 包（推荐）
- **优点**：标准的 macOS 应用格式，用户体验好
- **缺点**：是一个文件夹（虽然看起来像单个文件）
- **使用**：`python build_mac.py`

### 单文件
- **优点**：真正的单个文件
- **缺点**：首次启动较慢（需要解压）
- **使用**：`python build_mac_onefile.py`

## 首次运行注意事项

### 安全限制

macOS 可能会阻止运行未签名的应用：

1. **右键点击应用** -> **打开**
2. 在系统设置中允许运行
3. 或者在终端运行：
   ```bash
   xattr -cr "dist/Shop工具合集.app"
   ```

### 代码签名（可选，需要开发者账号）

如果你有 Apple 开发者账号，可以签名应用：

```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" "dist/Shop工具合集.app"
```

## 分发方式

### 方式一：直接分发 .app
- 将 `Shop工具合集.app` 压缩成 zip
- 用户解压后拖到 Applications 即可

### 方式二：DMG 安装包（推荐）
- 运行 `python create_dmg.py`
- 分发 `.dmg` 文件
- 用户双击安装

### 方式三：通过 App Store（需要开发者账号）
- 需要代码签名
- 需要遵循 App Store 审核规则

## 常见问题

### Q: 打包失败怎么办？
A: 
1. 确保所有依赖已安装：`pip install -r requirements.txt`
2. 确保在 macOS 上运行（不能在 Windows/Linux 上打包 macOS 应用）
3. 检查 Python 版本（建议 3.8+）

### Q: 应用无法运行？
A:
1. 右键点击 -> 打开（绕过安全限制）
2. 在系统设置 -> 安全性与隐私 -> 允许运行
3. 运行：`xattr -cr "dist/Shop工具合集.app"`

### Q: 如何创建图标？
A:
1. 准备一个 `.icns` 图标文件
2. 在打包命令中添加：`--icon=图标.icns`
3. 或者打包后手动替换图标

### Q: 支持 Intel Mac 吗？
A:
- 当前脚本主要针对 Apple Silicon 优化
- 如果需要支持 Intel，可以：
  1. 移除 `--target-arch=arm64` 参数
  2. 或者创建通用二进制文件（需要交叉编译）

### Q: 文件太大怎么办？
A:
- 使用 `--onedir` 代替 `--onefile`（.app 包默认就是 onedir）
- 或者使用 UPX 压缩（需要安装 UPX）

## 测试建议

打包完成后，建议测试：
1. 在干净的 macOS 系统上测试
2. 测试所有功能是否正常
3. 检查 Chrome 浏览器是否能正常启动
4. 测试文件读写权限

## 性能优化

- 首次启动可能较慢（需要加载依赖）
- 后续启动会快很多
- 建议在打包时使用 `--onedir` 模式以获得更好的性能
