"""
macOS 打包脚本 - CI/CD 优化版本
专门为 GitHub Actions 等 CI/CD 环境优化
使用方法: python build_mac_ci.py
"""

import os
import sys
import subprocess
import shutil

def build_mac_app_ci():
    """在 CI/CD 环境中构建 macOS 应用"""
    print("=" * 60)
    print("开始打包 Shop 工具合集 (macOS - CI/CD)")
    print("=" * 60)
    
    # 检查 PyInstaller
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 清理
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
    
    # PyInstaller 命令（CI/CD 优化）
    cmd = [
        'pyinstaller',
        '--name=Shop工具合集',
        '--onedir',  # macOS 使用 onedir
        '--windowed',  # 不显示控制台
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
        cmd.append('--add-data=keywords.xlsx:.')
    
    # 添加主程序文件
    cmd.append('shop_tools_gui.py')
    
    print("\n开始打包...")
    print("命令:", ' '.join(cmd))
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 60)
        print("\n✓ 打包成功！")
        
        # 检查输出
        app_path = 'dist/Shop工具合集.app'
        if os.path.exists(app_path):
            print(f"\n✓ 应用已创建: {app_path}")
            # 显示文件大小
            import subprocess as sp
            try:
                size = sp.check_output(['du', '-sh', app_path]).decode().split()[0]
                print(f"  大小: {size}")
            except:
                pass
            return True
        else:
            print("\n✗ 未找到 .app 文件")
            print("检查 dist 文件夹内容:")
            if os.path.exists('dist'):
                for item in os.listdir('dist'):
                    print(f"  - {item}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        print("\n错误详情:")
        if os.path.exists('build'):
            print("检查 build 文件夹中的警告文件...")
        return False
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = build_mac_app_ci()
    sys.exit(0 if success else 1)
