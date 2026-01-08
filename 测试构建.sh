#!/bin/bash
# 本地测试构建脚本 - 用于调试

echo "=== 测试 macOS 构建 ==="

# 检查 Python
echo "Python 版本:"
python --version

# 检查文件
echo -e "\n检查必要文件:"
for file in shop_tools_gui.py data_cleaner.py shopify_partners_scraper_auto.py shop_contact_scraper_google_login_v7_7.py; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (缺失)"
    fi
done

# 安装依赖
echo -e "\n安装依赖..."
pip install -q pandas openpyxl selenium webdriver-manager tqdm dnspython phonenumbers pyinstaller

# 测试导入
echo -e "\n测试导入..."
python -c "import shop_tools_gui; print('✓ shop_tools_gui 导入成功')" || echo "✗ shop_tools_gui 导入失败"

# 简单构建测试
echo -e "\n测试 PyInstaller..."
pyinstaller --version || echo "PyInstaller 未安装"

echo -e "\n=== 测试完成 ==="
