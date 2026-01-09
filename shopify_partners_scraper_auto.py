import sys
import subprocess
import time
import re
import os

# ---------- 自动安装依赖 ----------
required = ["pandas", "selenium", "webdriver-manager", "tqdm", "openpyxl"]
for pkg in required:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        print(f"🔧 未检测到 {pkg}，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# ---------- 引入库 ----------
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm

def scrape_shopify_partners(
    country: str,
    visible: bool = True,
    max_pages: int = 400,
    sleep_short: float = 1.0,
    sleep_item: float = 0.8,
    output_path: str | None = None,
    log_func=print,
    country_chinese_name: str | None = None,  # 新增：中文国家名参数
):
    """
    核心抓取函数，方便 GUI 或命令行调用。

    - country: 国家代号（如 'netherlands', 'italy', 'united-kingdom'）
    - visible: True=有界面，False=无头模式
    - max_pages: 最大翻页数
    - sleep_short: 列表页等待秒数
    - sleep_item: 详情页等待秒数
    - output_path: Excel 输出完整路径；为空则默认保存在当前目录
    - log_func: 日志函数，默认 print，GUI 中可传入自定义追加文本函数
    - country_chinese_name: 中文国家名（用于文件名）
    """
    country = (country or "").strip().lower()
    if not country:
        raise ValueError("国家代号不能为空")

    base_list_url = f"https://www.shopify.com/partners/directory/locations/{country}?page={{}}"

    # 使用中文国家名生成文件名
    if country_chinese_name:
        country_name_for_file = country_chinese_name
    else:
        # 如果没有提供中文名，使用国家代号（向后兼容）
        country_name_for_file = country

    if not output_path:
        output_path = os.path.abspath(f"Shopify合作伙伴_{country_name_for_file}.xlsx")
    else:
        # 如果给的是目录，则拼接默认文件名（包含中文国家名）
        if os.path.isdir(output_path):
            output_path = os.path.join(output_path, f"Shopify合作伙伴_{country_name_for_file}.xlsx")
        else:
            # 检查文件名是否已包含国家名
            base_name = os.path.basename(output_path)
            dir_name = os.path.dirname(output_path) if os.path.dirname(output_path) else "."
            name_without_ext, ext = os.path.splitext(base_name)
            
            # 如果文件名不包含国家名，自动添加
            if country_name_for_file not in name_without_ext and country not in name_without_ext.lower():
                # 在文件名末尾添加中文国家名（在扩展名之前）
                new_name = f"{name_without_ext}_{country_name_for_file}{ext}"
                output_path = os.path.join(dir_name, new_name)
                log_func(f"文件名已自动添加国家名: {os.path.basename(output_path)}")

    chrome_options = webdriver.ChromeOptions()
    if not visible:
        # note: new headless flag may differ by chrome version
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    log_func(f"\n🚀 开始爬取 Shopify 合作伙伴（{country}）目录...\n")

    # ---------- STEP 1: 收集详情页链接 ----------
    profile_links = []
    page = 1
    while page <= max_pages:
        list_url = base_list_url.format(page)
        log_func(f"打开列表页：{list_url}")
        try:
            driver.get(list_url)
        except Exception as e:
            log_func(f"打开列表页出错：{e}")
            break

        time.sleep(sleep_short)

        # 查找可能的个人页链接：尝试多种 xpath/css
        try:
            elems = driver.find_elements(
                By.XPATH,
                "//a[contains(@href,'/partners/directory/partner/') or contains(@href,'/partners/partner/')]",
            )
            links = []
            for e in elems:
                href = e.get_attribute("href")
                if href and "/partner/" in href:
                    links.append(href)
            links = list(dict.fromkeys([l for l in links if l]))  # 去重并保持顺序
        except Exception as e:
            log_func(f"列表页解析失败：{e}")
            links = []

        if not links:
            log_func("本页未找到合作伙伴链接，认为已到最后一页或页面结构变化，停止翻页。")
            break

        log_func(f"第 {page} 页：找到 {len(links)} 个候选链接")
        profile_links.extend(links)
        page += 1

    # 最终去重
    profile_links = list(dict.fromkeys(profile_links))
    log_func(f"\n共收集到 {len(profile_links)} 个详情页链接，开始抓取详细信息...\n")

    # ---------- STEP 2: 逐条抓取详情信息 ----------
    results = []
    total_links = len(profile_links)
    
    # 检查是否在 GUI 环境中（log_func 不是 print）
    is_gui_mode = log_func != print
    
    # 使用普通循环（GUI 模式下禁用 tqdm 以避免写入错误）
    if is_gui_mode:
        # GUI 模式：使用普通循环，手动输出进度
        for idx, link in enumerate(profile_links, 1):
            if idx % 10 == 0 or idx == 1 or idx == total_links:
                log_func(f"正在抓取详情页: {idx}/{total_links} - {link[:80]}...")
            try:
                driver.get(link)
            except Exception as e:
                log_func(f"打开详情页失败：{link} {e}")
                continue

            time.sleep(sleep_item)

            # name
            name = ""
            try:
                h1s = driver.find_elements(By.TAG_NAME, "h1")
                if h1s:
                    name = h1s[0].text.strip()
            except Exception:
                name = ""

            # location（尝试从左侧卡片或页面文本抓取）
            location = ""
            try:
                # 优先找包含 'Primary location' 等字段的相邻文本
                loc_candidates = driver.find_elements(
                    By.XPATH,
                    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'primary location') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location') or contains(.,'Netherlands') or contains(.,'Nederland') or contains(.,'意大利')]",
                )
                if loc_candidates:
                    for c in loc_candidates:
                        txt = c.text.strip()
                        if txt and (
                            ("Netherlands" in txt)
                            or ("Nederland" in txt)
                            or ("意大利" in txt)
                            or re.search(
                                r"[A-Za-z\s]+,?\s*(Netherlands|Nederland|Italy|Italia|United Kingdom|UK|England)",
                                txt,
                            )
                        ):
                            location = txt
                            break
            except Exception:
                location = ""

            # 联系信息提取（主方法）
            email, phone, website = extract_from_contact_section(driver)

            results.append(
                {
                    "名称": name,
                    "页面链接": link,
                    "邮箱": email,
                    "电话": phone,
                    "网站": website,
                    "位置": location,
                }
            )
            
            # 每抓取一定数量后输出进度（GUI 模式）
            if len(results) % 10 == 0:
                log_func(f"已抓取 {len(results)}/{total_links} 条记录...")
    else:
        # 命令行模式：尝试使用 tqdm 显示进度条，如果失败则使用普通循环
        try:
            link_iterator = tqdm(profile_links, desc="抓取详情页", ncols=80, disable=False)
        except (AttributeError, OSError, IOError) as e:
            # 如果 tqdm 失败（例如 stdout 不可写），使用普通迭代器
            log_func(f"注意: 无法显示进度条，使用普通模式: {e}")
            link_iterator = profile_links
        
        for link in link_iterator:
            try:
                driver.get(link)
            except Exception as e:
                log_func(f"打开详情页失败：{link} {e}")
                continue

            time.sleep(sleep_item)

            # name
            name = ""
            try:
                h1s = driver.find_elements(By.TAG_NAME, "h1")
                if h1s:
                    name = h1s[0].text.strip()
            except Exception:
                name = ""

            # location（尝试从左侧卡片或页面文本抓取）
            location = ""
            try:
                # 优先找包含 'Primary location' 等字段的相邻文本
                loc_candidates = driver.find_elements(
                    By.XPATH,
                    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'primary location') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'location') or contains(.,'Netherlands') or contains(.,'Nederland') or contains(.,'意大利')]",
                )
                if loc_candidates:
                    for c in loc_candidates:
                        txt = c.text.strip()
                        if txt and (
                            ("Netherlands" in txt)
                            or ("Nederland" in txt)
                            or ("意大利" in txt)
                            or re.search(
                                r"[A-Za-z\s]+,?\s*(Netherlands|Nederland|Italy|Italia|United Kingdom|UK|England)",
                                txt,
                            )
                        ):
                            location = txt
                            break
            except Exception:
                location = ""

            # 联系信息提取（主方法）
            email, phone, website = extract_from_contact_section(driver)

            results.append(
                {
                    "名称": name,
                    "页面链接": link,
                    "邮箱": email,
                    "电话": phone,
                    "网站": website,
                    "位置": location,
                }
            )

    # 关闭浏览器
    driver.quit()

    # ---------- STEP 3: 保存到 Excel ----------
    df = pd.DataFrame(results)
    df.to_excel(output_path, index=False)
    log_func(f"\n🎉 完成！共抓取 {len(results)} 条记录，已保存为：{output_path}")

def extract_from_contact_section(driver):
    """在当前详情页中尝试定位联系信息区并提取 email/phone/website"""
    email = ""
    phone = ""
    website = ""

    # 1) 首先尝试定位包含 Contact / 联系 / Contact information / Contactinformatie 的元素，然后查找其后面的链接
    xpaths_title = [
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact information')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contactinformatie')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'information')]", 
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contact') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'informatie')]",
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '联系')]"  # 中文页面备用
    ]
    contact_container = None
    for xp in xpaths_title:
        try:
            els = driver.find_elements(By.XPATH, xp)
            if els:
                # 尝试取第一个匹配元素的父或兄弟节点作为整体区域
                el = els[0]
                # 先尝试后面紧邻的兄弟节点
                try:
                    sibling = el.find_element(By.XPATH, "following-sibling::*[1]")
                    contact_container = sibling
                    break
                except Exception:
                    try:
                        parent = el.find_element(By.XPATH, "..")
                        contact_container = parent
                        break
                    except Exception:
                        contact_container = el
                        break
        except Exception:
            continue

    # 2) 如果没找到，上面不行则尝试找侧边卡片内的常见类名（例如 breakword / p.breakword 等）
    if not contact_container:
        candidate_selectors = [
            "//div[contains(@class,'breakword')]",
            "//div[contains(@class,'card')]",
            "//section//div[contains(@class,'col') and .//a[contains(@href,'mailto:')]]",
            "//aside//a[contains(@href,'mailto:')]",
        ]
        for xp in candidate_selectors:
            try:
                els = driver.find_elements(By.XPATH, xp)
                if els:
                    contact_container = els[0]
                    break
            except Exception:
                continue

    # 3) 从 contact_container 中收集所有 a 标签并分类
    if contact_container:
        try:
            anchors = contact_container.find_elements(By.TAG_NAME, "a")
            for a in anchors:
                href = (a.get_attribute("href") or "").strip()
                if href.startswith("mailto:") and not email:
                    email = href.replace("mailto:", "").strip()
                elif href.startswith("tel:") and not phone:
                    phone = href.replace("tel:", "").strip()
                elif href.startswith("http") and "shopify.com" not in href and not website:
                    website = href
        except Exception:
            pass

    # 4) 兜底：如果仍为空，直接从整页查找 mailto/tel/http（优先 mailto/tel）
    if not email:
        try:
            m = driver.find_elements(By.XPATH, "//a[starts-with(@href,'mailto:')]")
            if m:
                email = (m[0].get_attribute("href") or "").replace("mailto:", "").strip()
        except Exception:
            pass
    if not phone:
        try:
            t = driver.find_elements(By.XPATH, "//a[starts-with(@href,'tel:')]")
            if t:
                phone = (t[0].get_attribute("href") or "").replace("tel:", "").strip()
        except Exception:
            pass
    if not website:
        try:
            http_els = driver.find_elements(By.XPATH, "//a[starts-with(@href,'http')]")
            for h in http_els:
                href = (h.get_attribute("href") or "").strip()
                if href and "shopify.com" not in href and "linkedin.com" not in href:
                    website = href
                    break
        except Exception:
            pass

    return email, phone, website


if __name__ == "__main__":
    # 兼容原有命令行用法
    country = input("请输入国家代号（小写，如 netherlands / italy / united-kingdom）：").strip().lower()
    if not country:
        print("未输入国家，程序退出。")
        sys.exit(1)
    scrape_shopify_partners(country)
