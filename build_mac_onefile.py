"""
macOS 单文件打包脚本 - 打包成单个可执行文件
适用于 Apple Silicon (M1/M2/M3) 芯片
使用方法: python build_mac_onefile.py
"""

import os
import sys
import subprocess
import shutil
import platform

def check_platform():
    """检查是否在 macOS 上运行"""
    if sys.platform != 'darwin':
        print("错误: 此脚本只能在 macOS 上运行")
        return False
    
    arch = platform.machine()
    print(f"✓ 检测到架构: {arch}")
    return True

def check_pyinstaller():
    """检查 PyInstaller 是否已安装"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True

def build_mac_onefile():
    """构建 macOS 单文件应用"""
    print("=" * 60)
    print("开始打包 Shop 工具合集 (macOS - 单文件)")
    print("=" * 60)
    
    if not check_platform() or not check_pyinstaller():
        return False
    
    # 清理
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # 打包命令
    cmd = [
        'pyinstaller',
        '--name=Shop工具合集',
        '--onefile',  # 单文件模式
        '--windowed',
        '--target-arch=arm64',
        '--osx-bundle-identifier=com.shop.tools',
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
        'shop_tools_gui.py'
    ]
    
    print("\n开始打包...")
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ 打包成功！")
        print("可执行文件位置: dist/Shop工具合集")
        return True
    except Exception as e:
        print(f"\n✗ 打包失败: {e}")
        return False

if __name__ == "__main__":
    build_mac_onefile()
