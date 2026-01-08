"""
macOS 打包脚本 - 将项目打包为 macOS 应用
适用于 Apple Silicon (M1/M2/M3) 芯片
使用方法: python build_mac.py
"""

import os
import sys
import subprocess
import shutil
import platform

def check_platform():
    """检查是否在 macOS 上运行"""
    if sys.platform != 'darwin':
        print(f"警告: 当前系统是 {sys.platform}，不是 macOS")
        print("在 CI/CD 环境中继续执行...")
        # 在 GitHub Actions 中，即使检查失败也继续
        # return False
    
    # 检查架构
    try:
        arch = platform.machine()
        if arch == 'arm64':
            print(f"✓ 检测到 Apple Silicon (M 芯片) - {arch}")
        elif arch == 'x86_64':
            print(f"⚠ 检测到 Intel 芯片 - {arch}")
            print("  注意: 此脚本主要针对 M 芯片优化")
        else:
            print(f"⚠ 未知架构: {arch}")
    except Exception as e:
        print(f"⚠ 无法检测架构: {e}")
    
    return True  # 在 CI/CD 中总是返回 True

def check_pyinstaller():
    """检查 PyInstaller 是否已安装"""
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
        return True
    except ImportError:
        print("✗ PyInstaller 未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller 安装成功")
            return True
        except Exception as e:
            print(f"✗ PyInstaller 安装失败: {e}")
            return False

def build_mac_app():
    """构建 macOS 应用"""
    print("=" * 60)
    print("开始打包 Shop 工具合集 (macOS)")
    print("=" * 60)
    
    # 检查平台
    if not check_platform():
        return False
    
    # 检查 PyInstaller
    if not check_pyinstaller():
        print("错误: 无法安装 PyInstaller，请手动安装: pip install pyinstaller")
        return False
    
    # 清理之前的构建文件
    print("\n清理旧的构建文件...")
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"✓ 已删除 {folder}")
            except Exception as e:
                print(f"⚠ 删除 {folder} 失败: {e}")
    
    # 删除旧的 spec 文件
    spec_file = 'shop_tools_gui.spec'
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"✓ 已删除 {spec_file}")
        except Exception as e:
            print(f"⚠ 删除 {spec_file} 失败: {e}")
    
    # PyInstaller 命令（macOS 特定）
    cmd = [
        'pyinstaller',
        '--name=Shop工具合集',
        '--onedir',  # macOS 通常使用 onedir（文件夹形式）
        '--windowed',  # 不显示控制台窗口（GUI应用）
        '--target-arch=arm64',  # 指定为 Apple Silicon
        '--osx-bundle-identifier=com.shop.tools',  # Bundle ID
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=selenium',
        '--hidden-import=webdriver_manager',
        '--hidden-import=tqdm',
        '--hidden-import=dnspython',
        '--hidden-import=dns',
        '--hidden-import=phonenumbers',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=data_cleaner',
        '--hidden-import=shopify_partners_scraper_auto',
        '--hidden-import=shop_contact_scraper_google_login_v7_7',
        '--collect-all=selenium',
        '--collect-all=webdriver_manager',
        '--collect-all=phonenumbers',
        '--collect-all=dnspython',
        '--noconfirm',
    ]
    
    # 如果存在 keywords.xlsx，添加到数据文件
    if os.path.exists('keywords.xlsx'):
        cmd.append('--add-data=keywords.xlsx:.')  # macOS 使用冒号分隔
    
    # 添加主程序文件
    cmd.append('shop_tools_gui.py')
    
    print("\n开始打包...")
    print("命令:", ' '.join(cmd))
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("-" * 60)
        print("\n✓ 打包成功！")
        
        # 查找生成的 .app 文件
        app_path = 'dist/Shop工具合集.app'
        if os.path.exists(app_path):
            print(f"\n✓ 应用已创建: {app_path}")
            print("\n提示:")
            print("1. 可以将 Shop工具合集.app 复制到 Applications 文件夹")
            print("2. 首次运行可能需要右键点击 -> 打开（绕过安全限制）")
            print("3. 如果遇到安全提示，请在系统设置中允许运行")
            print("\n创建 DMG 安装包（可选）:")
            print("  运行: python create_dmg.py")
        else:
            print("\n⚠ 未找到 .app 文件，请检查 dist 文件夹")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        return False

if __name__ == "__main__":
    success = build_mac_app()
    sys.exit(0 if success else 1)
