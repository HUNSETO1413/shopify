"""
创建 DMG 安装包脚本
将 .app 打包成 .dmg 文件，方便分发
使用方法: python create_dmg.py
"""

import os
import sys
import subprocess
import shutil

def create_dmg():
    """创建 DMG 安装包"""
    print("=" * 60)
    print("创建 DMG 安装包")
    print("=" * 60)
    
    app_path = 'dist/Shop工具合集.app'
    if not os.path.exists(app_path):
        print(f"错误: 未找到应用文件 {app_path}")
        print("请先运行 python build_mac.py 打包应用")
        return False
    
    dmg_name = 'Shop工具合集'
    dmg_path = f'dist/{dmg_name}.dmg'
    
    # 清理旧的 DMG
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    
    print(f"\n正在创建 DMG: {dmg_path}")
    print("这可能需要几分钟...")
    
    # 使用 hdiutil 创建 DMG
    try:
        # 创建临时目录
        temp_dir = 'dist/dmg_temp'
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # 复制应用
        shutil.copytree(app_path, os.path.join(temp_dir, 'Shop工具合集.app'))
        
        # 创建 Applications 链接（可选）
        os.symlink('/Applications', os.path.join(temp_dir, 'Applications'))
        
        # 创建 DMG
        cmd = [
            'hdiutil', 'create',
            '-volname', dmg_name,
            '-srcfolder', temp_dir,
            '-ov',
            '-format', 'UDZO',
            dmg_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        print(f"\n✓ DMG 创建成功: {dmg_path}")
        print("\n提示:")
        print("1. DMG 文件可以直接分发给其他用户")
        print("2. 用户双击 DMG 文件即可安装")
        print("3. 将应用拖到 Applications 文件夹即可")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 创建 DMG 失败: {e}")
        print("\n提示: 如果 hdiutil 命令失败，可以手动创建 DMG:")
        print("1. 打开 磁盘工具")
        print("2. 文件 -> 新建映像 -> 来自文件夹的映像")
        print("3. 选择 dist/Shop工具合集.app")
        print("4. 保存为 DMG 格式")
        return False
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        return False

if __name__ == "__main__":
    create_dmg()
