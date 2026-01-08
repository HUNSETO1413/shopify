"""
打包脚本 - 将项目打包为 exe 文件
使用方法: python build_exe.py
"""

import os
import sys
import subprocess
import shutil

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

def build_exe():
    """构建 exe 文件"""
    print("=" * 60)
    print("开始打包 Shop 工具合集")
    print("=" * 60)
    
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
    
    # PyInstaller 命令
    cmd = [
        'pyinstaller',
        '--name=Shop工具合集',
        '--onefile',  # 打包成单个 exe 文件
        '--windowed',  # 不显示控制台窗口（GUI应用）
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
        '--noconfirm',  # 覆盖输出目录而不询问
    ]
    
    # 如果存在 keywords.xlsx，添加到数据文件
    if os.path.exists('keywords.xlsx'):
        cmd.append('--add-data=keywords.xlsx;.')
    
    # 添加主程序文件
    cmd.append('shop_tools_gui.py')
    
    print("\n开始打包...")
    print("命令:", ' '.join(cmd))
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("-" * 60)
        print("\n✓ 打包成功！")
        print(f"\n输出文件位置: dist/Shop工具合集.exe")
        print("\n提示:")
        print("1. 可以将 dist/Shop工具合集.exe 复制到任何位置使用")
        print("2. 首次运行可能需要几秒钟启动时间")
        print("3. 如果遇到杀毒软件误报，请添加信任")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
