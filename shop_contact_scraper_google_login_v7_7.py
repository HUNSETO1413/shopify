#!/usr/bin/env python3

import os
import re
import time
import random
import shutil
from urllib.parse import urlsplit, urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
import tldextract
import phonenumbers

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: 未安装 selenium，请运行: pip install selenium webdriver-manager")

# ---------------- SPEED CONFIG ----------------
# 并发抓取的网站数量（根据机器/网络可调，3~10 之间比较合适）
MAX_WORKERS = 5

# 站点之间、站内路径之间的随机等待（避免太像机器人）
SLEEP_BETWEEN_SITES = (0.4, 0.9)
SLEEP_BETWEEN_PAGES = (0.2, 0.5)

# ---------------- 功能开关 ----------------
# False = 深度模式（会跑很多路径），True = 快速模式（只少量路径）
FAST_MODE = True

# ---------------- 基本 CONFIG ----------------
DEFAULT_KEYWORDS_XLSX = "keywords.xlsx"
DEFAULT_OUTPUT_ALL = "shop_contacts_all.xlsx"
DEFAULT_FAILED_FILE = "failed_keywords.txt"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.I)
TEL_HREF_RE = re.compile(r'href=[\'"]tel:([^\'"]+)[\'"]', re.I)
MAILTO_RE = re.compile(r'href=[\'"]mailto:([^\'"]+)[\'"]', re.I)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124 Safari/537.36"
    )
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com",
    "qq.com", "163.com", "126.com", "sina.com", "yeah.net",
    "proton.me", "protonmail.com",
    "gmx.com", "mail.com", "yandex.ru", "yandex.com", "zoho.com",
}

BAD_LOCALPART_PREFIXES = {
    "abuse", "security", "legal", "dmca", "privacy",
    "no-reply", "noreply", "donotreply",
    "mailer-daemon", "mailerdaemon", "bounce",
}

BAD_TLDS = {
    "webp", "png", "jpg", "jpeg", "gif", "svg",
    "webm", "mp4", "mp3", "ico", "css", "js",
}

SKIP_SITE_DOMAINS = {
    "apps.shopify.com",
    "shopify.com",
    "partners.shopify.com",
    "help.shopify.com",
    "community.shopify.com",
    "developers.shopify.com",
    "myshopify.com",

    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "youtu.be", "linkedin.com", "pinterest.com",
    "tiktok.com", "snapchat.com",

    "google.com", "support.google.com", "accounts.google.com",
    "cloudflare.com", "cloudflare.net",
    "wix.com", "wixsite.com", "wixstatic.com",
    "squarespace.com", "godaddy.com", "weebly.com",
    "shopifycdn.com", "cdn.shopify.com",
}

SOCIAL_DOMAINS = {
    "facebook.com", "instagram.com", "tiktok.com",
    "twitter.com", "x.com", "youtube.com", "youtu.be",
    "pinterest.com",
}

# 深度模式路径
CONTACT_PATHS_DEEP = [
    "/",  # 首页
    # 联系
    "/pages/contact",
    "/pages/contact-us",
    "/pages/contact_us",
    "/pages/contactus",
    "/contact",
    "/contact-us",
    "/contact_us",
    "/contact-1",
    "/contact-us-1",
    # 关于
    "/pages/about",
    "/pages/about-us",
    "/pages/about_us",
    "/about",
    "/about-us",
    # FAQ / 帮助 / 支持
    "/pages/faq",
    "/faq",
    "/pages/help",
    "/help",
    "/pages/support",
    "/support",
    "/pages/customer-service",
    "/customer-service",
    # 发货 / 退货
    "/pages/shipping",
    "/pages/returns",
    "/pages/refund-policy",
    "/refund-policy",
    # 批发 / B2B
    "/pages/wholesale",
    "/wholesale",
]

# 快速模式路径
CONTACT_PATHS_FAST = [
    "/",
    "/contact",
    "/contact-us",
    "/pages/contact",
    "/pages/contact-us",
]

CONTACT_PATHS = CONTACT_PATHS_FAST if FAST_MODE else CONTACT_PATHS_DEEP

# ---------------- UTIL ----------------
def get_registered_domain(url_or_host: str):
    try:
        ext = tldextract.extract(url_or_host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        return None
    except Exception:
        return None


def should_skip_site(url: str) -> bool:
    dom = get_registered_domain(url) or ""
    return dom in SKIP_SITE_DOMAINS


def make_session():
    """每个线程用自己的 Session，提高连接复用效率。"""
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_html(url, session=None, timeout=15, headers=None):
    if headers is None:
        headers = HEADERS
    try:
        if session is not None:
            r = session.get(url, headers=headers, timeout=timeout)
        else:
            r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def decode_cfemail(encoded: str) -> str:
    """Cloudflare data-cfemail 解码"""
    try:
        r = int(encoded[:2], 16)
        email = ""
        for i in range(2, len(encoded), 2):
            c = int(encoded[i:i + 2], 16) ^ r
            email += chr(c)
        return email
    except Exception:
        return ""


def extract_cloudflare_emails(soup: BeautifulSoup):
    emails = []
    for el in soup.select("a.__cf_email__, span.__cf_email__"):
        enc = el.get("data-cfemail")
        if enc:
            dec = decode_cfemail(enc)
            if dec and "@" in dec:
                emails.append(dec)
    return emails


def extract_emails_from_html(html: str, soup: BeautifulSoup):
    emails = []

    if html:
        emails.extend([m.group(0) for m in EMAIL_RE.finditer(html)])

        for m in MAILTO_RE.finditer(html):
            raw = m.group(1).strip()
            raw = unquote(raw.split("?", 1)[0])
            if "@" in raw:
                emails.append(raw)

    emails.extend(extract_cloudflare_emails(soup))

    return list(dict.fromkeys(emails))


def extract_phones_from_html(html):
    if not html:
        return []

    phones = set()
    for m in TEL_HREF_RE.finditer(html):
        raw = m.group(1).strip()
        clean = re.sub(r"[^\d\+]", "", raw)
        if len(clean) < 7:
            continue
        try:
            pn = phonenumbers.parse(clean, None)
            if phonenumbers.is_valid_number(pn):
                phones.add(
                    phonenumbers.format_number(
                        pn, phonenumbers.PhoneNumberFormat.E164
                    )
                )
        except Exception:
            phones.add(clean)

    return list(phones)


def extract_social_links(soup: BeautifulSoup, base_url: str):
    links = set()
    if not soup:
        return list(links)

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        full = urljoin(base_url, href)
        parts = urlsplit(full)
        host = parts.netloc.lower()
        if not host:
            continue
        for dom in SOCIAL_DOMAINS:
            if dom in host:
                links.add(full)
                break

    return list(links)


def extract_whatsapp(html: str, soup: BeautifulSoup):
    """提取WhatsApp号码"""
    whatsapp = None
    if not html or not soup:
        return whatsapp
    
    # 查找 wa.me 链接
    whatsapp_patterns = [
        r'wa\.me/(\d+)',
        r'whatsapp\.com/send\?phone=(\d+)',
        r'whatsapp://send\?phone=(\d+)',
        r'href=["\'](?:https?://)?wa\.me/(\d+)',
        r'href=["\'](?:https?://)?whatsapp\.com/send\?phone=(\d+)',
    ]
    
    for pattern in whatsapp_patterns:
        matches = re.findall(pattern, html, re.I)
        if matches:
            whatsapp = matches[0]
            break
    
    # 从链接中查找
    if not whatsapp:
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").lower()
            if "wa.me" in href or "whatsapp.com" in href:
                match = re.search(r'(\d{10,})', href)
                if match:
                    whatsapp = match.group(1)
                    break
    
    return whatsapp


def extract_address(soup: BeautifulSoup):
    """提取地址信息"""
    address = None
    if not soup:
        return address
    
    # 查找包含地址关键词的元素
    address_keywords = [
        "address", "location", "location", "地址", "所在地",
        "street", "avenue", "road", "boulevard", "city", "state", "zip", "postal"
    ]
    
    # 尝试找包含地址关键词的文本
    for keyword in address_keywords:
        elements = soup.find_all(string=re.compile(keyword, re.I))
        for elem in elements:
            parent = elem.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) > 10 and len(text) < 200:  # 合理长度
                    address = text
                    break
        if address:
            break
    
    # 尝试找结构化数据（schema.org）
    if not address:
        addr_elem = soup.find(attrs={"itemprop": "address"})
        if addr_elem:
            address = addr_elem.get_text(strip=True)
    
    return address


def extract_description(soup: BeautifulSoup, url: str):
    """提取公司介绍/描述"""
    description = None
    if not soup:
        return description
    
    # 优先查找 meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()
        if description:
            return description
    
    # 查找 og:description
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()
        if description:
            return description
    
    # 查找包含 "about" 的段落
    about_sections = soup.find_all(["p", "div"], string=re.compile("about|介绍|简介", re.I))
    for section in about_sections[:3]:  # 只取前3个
        text = section.get_text(strip=True)
        if len(text) > 50 and len(text) < 500:
            description = text
            break
    
    return description


def filter_emails_for_site(emails, site_url):
    if not emails:
        return []

    site_domain = get_registered_domain(site_url) or ""
    base_clean = []

    for e in emails:
        e = e.strip()
        if "@" not in e:
            continue
        local, domain = e.rsplit("@", 1)
        local = local.strip().lower()
        domain = domain.strip().lower()

        ext = tldextract.extract(domain)
        tld = (ext.suffix or "").split(".")[-1].lower()
        if tld in BAD_TLDS:
            continue

        local_clean = local.replace(".", "").replace("_", "").replace("-", "")
        bad_local = False
        for bad_prefix in BAD_LOCALPART_PREFIXES:
            if local.startswith(bad_prefix) or local_clean.startswith(
                bad_prefix.replace("-", "")
            ):
                bad_local = True
                break
        if bad_local:
            continue

        base_clean.append(f"{local}@{domain}")

    if not base_clean:
        return []

    strong = []
    weak = []
    for e in base_clean:
        local, domain = e.split("@", 1)
        dom_reg = get_registered_domain(domain) or ""

        if site_domain and dom_reg == site_domain:
            strong.append(e)
        elif domain in FREE_EMAIL_DOMAINS:
            strong.append(e)
        else:
            weak.append(e)

    if strong or weak:
        combined = strong + weak
        return list(dict.fromkeys(combined))

    return list(dict.fromkeys(base_clean))


def extract_shop_name(soup: BeautifulSoup, url: str) -> str:
    try:
        meta_site = soup.find("meta", attrs={"property": "og:site_name"})
        if meta_site and meta_site.get("content"):
            name = meta_site["content"].strip()
            if name:
                return name
    except Exception:
        pass

    try:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if title:
                return title
    except Exception:
        pass

    dom = get_registered_domain(url)
    return dom or url


def build_base_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return url

# ---------------- GOOGLE SEARCH ----------------
def google_search(query, pages=1, headless=False, log_func=print):
    """使用 Selenium Chrome 访客模式搜索 Google"""
    if not SELENIUM_AVAILABLE:
        log_func("错误: selenium 未安装，请运行: pip install selenium webdriver-manager")
        return []
    
    urls = []
    driver = None
    temp_user_data = None
    
    try:
        # 创建临时用户数据目录（访客模式）
        import tempfile
        temp_user_data = tempfile.mkdtemp(prefix="chrome_guest_")
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"--user-data-dir={temp_user_data}")
        chrome_options.add_argument("--guest")  # 访客模式
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # 设置超时
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        
        log_func("正在打开 Google 页面...")
        driver.get("https://www.google.com/ncr")
        time.sleep(2)
        
        # 处理可能的同意页面
        try:
            consent_selectors = [
                'button:contains("Accept all")',
                'button:contains("I agree")',
                'button:contains("接受")',
                'button[id*="accept"]',
                'button[aria-label*="Accept"]',
            ]
            for selector in consent_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector.replace(":contains", ""))
                    for btn in buttons:
                        if "accept" in btn.text.lower() or "同意" in btn.text or "agree" in btn.text.lower():
                            btn.click()
                            time.sleep(1)
                            break
                except Exception:
                    continue
        except Exception:
            pass
        
        log_func("定位搜索框...")
        search_box = None
        search_selectors = [
            (By.NAME, "q"),
            (By.CSS_SELECTOR, 'textarea[name="q"]'),
            (By.CSS_SELECTOR, 'input[name="q"]'),
            (By.CSS_SELECTOR, 'textarea[aria-label*="Search"]'),
            (By.CSS_SELECTOR, 'input[aria-label*="Search"]'),
        ]
        
        for by, selector in search_selectors:
            try:
                elements = driver.find_elements(by, selector)
                if elements:
                    search_box = elements[0]
                    break
            except Exception:
                continue
        
        if not search_box:
            log_func("未找到搜索框，尝试直接解析当前页面...")
        else:
            log_func(f"找到搜索框，输入关键词: {query}")
            try:
                search_box.clear()
                search_box.send_keys(query)
                time.sleep(0.5)
                search_box.send_keys(Keys.RETURN)
                time.sleep(3)  # 等待搜索结果加载
            except Exception as e:
                log_func(f"输入搜索关键词失败: {e}")
        
        # 提取搜索结果链接
        for page_num in range(pages):
            log_func(f"正在提取第 {page_num + 1} 页搜索结果...")
            
            try:
                # 等待结果加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h3, a h3"))
                )
            except TimeoutException:
                log_func("等待搜索结果超时，尝试继续解析...")
            
            # 提取所有结果链接
            try:
                result_links = driver.find_elements(By.CSS_SELECTOR, "div.g a, div[data-ved] a, h3 a")
                for link_elem in result_links:
                    try:
                        href = link_elem.get_attribute("href")
                        if href and href.startswith("http") and "google" not in href.lower():
                            urls.append(href)
                    except Exception:
                        continue
            except Exception as e:
                log_func(f"提取链接时出错: {e}")
            
            # 如果不是最后一页，尝试翻页
            if page_num < pages - 1:
                try:
                    next_button = driver.find_element(By.ID, "pnnext")
                    if next_button and next_button.is_displayed():
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(3)  # 等待下一页加载
                    else:
                        log_func("已到最后一页")
                        break
                except (NoSuchElementException, Exception):
                    log_func("未找到下一页按钮，可能已到最后一页")
                    break
        
    except Exception as e:
        log_func(f"Google 搜索过程出错: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        # 清理临时目录
        try:
            import shutil
            if os.path.exists(temp_user_data):
                shutil.rmtree(temp_user_data, ignore_errors=True)
        except Exception:
            pass
    
    urls = list(dict.fromkeys(urls))
    urls = [u for u in urls if not should_skip_site(u)]
    log_func(f"本次搜索得到可用链接数量: {len(urls)}")
    return urls

# ---------------- SCRAPE SITE（使用浏览器） ----------------
def scrape_site(url, driver=None, timeout=20):
    """
    抓取单个站点：
      - site_emails: 官网邮箱
      - phones: 电话
      - whatsapp: WhatsApp号码
      - address: 地址
      - company_name: 公司名称
      - description: 公司介绍
      - 社媒 URL：facebook_links / instagram_links / tiktok_links / twitter_links / youtube_links / pinterest_links
    """
    out = {
        "url": url,
        "shop_name": None,
        "company_name": None,
        "description": None,
        "address": None,

        "site_emails": [],
        "phones": [],
        "whatsapp": None,

        "social_links": [],
        "facebook_links": [],
        "instagram_links": [],
        "tiktok_links": [],
        "twitter_links": [],
        "youtube_links": [],
        "pinterest_links": [],

        "status": "failed",
    }

    visited = set()
    all_raw_emails = []
    all_phones = set()
    all_social = set()

    # 使用浏览器打开页面
    if driver:
        try:
            driver.get(url)
            time.sleep(2)  # 等待页面加载
            main_html = driver.page_source
        except Exception as e:
            out["status"] = f"failed_fetch_error: {str(e)[:50]}"
            return out
    else:
        # 如果没有提供driver，回退到requests方式
        try:
            session = make_session()
            main_html = fetch_html(url, session=session, timeout=timeout)
            if not main_html:
                out["status"] = "failed_fetch"
                return out
        except Exception as e:
            out["status"] = f"failed_fetch_error: {str(e)[:50]}"
            return out

    visited.add(url)
    main_soup = BeautifulSoup(main_html, "html.parser")
    base_url = build_base_url(url)

    out["shop_name"] = extract_shop_name(main_soup, url)
    out["company_name"] = out["shop_name"]  # 公司名称默认使用shop_name
    out["description"] = extract_description(main_soup, url)
    out["address"] = extract_address(main_soup)
    out["whatsapp"] = extract_whatsapp(main_html, main_soup)

    all_raw_emails.extend(extract_emails_from_html(main_html, main_soup))
    for ph in extract_phones_from_html(main_html):
        all_phones.add(ph)
    for sl in extract_social_links(main_soup, base_url):
        all_social.add(sl)

    # 站内路径
    for path in CONTACT_PATHS:
        full = urljoin(base_url, path)
        if full in visited:
            continue
        visited.add(full)

        try:
            if driver:
                # 使用浏览器打开
                driver.get(full)
                time.sleep(1)  # 等待页面加载
                html = driver.page_source
            else:
                # 回退到requests
                session = make_session()
                html = fetch_html(full, session=session, timeout=timeout)
                if not html:
                    continue
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            continue
        all_raw_emails.extend(extract_emails_from_html(html, soup))
        for ph in extract_phones_from_html(html):
            all_phones.add(ph)
        for sl in extract_social_links(soup, base_url):
            all_social.add(sl)
        
        # 如果主页面没有找到这些信息，尝试从其他页面获取
        if not out["description"]:
            desc = extract_description(soup, full)
            if desc:
                out["description"] = desc
        if not out["address"]:
            addr = extract_address(soup)
            if addr:
                out["address"] = addr
        if not out["whatsapp"]:
            wa = extract_whatsapp(html, soup)
            if wa:
                out["whatsapp"] = wa

        time.sleep(random.uniform(*SLEEP_BETWEEN_PAGES))

    # 官网邮箱
    site_emails = filter_emails_for_site(all_raw_emails, url)
    out["site_emails"] = site_emails

    out["phones"] = list(all_phones)
    out["social_links"] = list(all_social)

    fb_links = []
    ig_links = []
    tk_links = []
    tw_links = []
    yt_links = []
    pt_links = []

    for sl in all_social:
        host = urlsplit(sl).netloc.lower()
        if "facebook.com" in host:
            fb_links.append(sl)
        elif "instagram.com" in host:
            ig_links.append(sl)
        elif "tiktok.com" in host:
            tk_links.append(sl)
        elif "twitter.com" in host or host == "x.com":
            tw_links.append(sl)
        elif "youtube.com" in host or "youtu.be" in host:
            yt_links.append(sl)
        elif "pinterest.com" in host:
            pt_links.append(sl)

    out["facebook_links"] = fb_links
    out["instagram_links"] = ig_links
    out["tiktok_links"] = tk_links
    out["twitter_links"] = tw_links
    out["youtube_links"] = yt_links
    out["pinterest_links"] = pt_links

    out["status"] = "ok" if site_emails else "no_email"
    return out


# 已改为单线程顺序抓取，不再需要 worker 函数

# ---------------- MAIN ----------------
def ensure_keywords(keywords_path: str):
    if not os.path.exists(keywords_path):
        demo = pd.DataFrame(
            {
                "keyword": [
                    "shopify clothing boutique",
                    "site:shopify.com t-shirt store",
                    "site:shopify.com floor cleaner",
                ]
            }
        )
        demo.to_excel(keywords_path, index=False)
        print(f"已创建示例文件 {keywords_path}，请打开编辑关键词后重新运行。")
        return False
    return True


def run_shop_contact_scraper(
    keywords_path: str = DEFAULT_KEYWORDS_XLSX,
    pages: int = 1,
    output_path: str | None = None,
    failed_file: str | None = None,
    headless: bool = False,
    log_func=print,
):
    """
    核心抓取函数，方便 GUI / 命令行调用。

    - keywords_path: 关键词 Excel 路径，需要一列 'keyword'
    - pages: 每个关键词搜索页数
    - output_path: 结果 Excel 路径；为空则使用默认名
    - failed_file: 失败 URL 输出 txt 路径；为空则使用默认名
    - headless: True=无头浏览器，False=有界面
    - log_func: 日志函数，可用于 GUI 文本框输出
    """
    print("=== shop_contact_scraper_google_login_v8_parallel ===")
    print(f"FAST_MODE = {FAST_MODE} (False=深度模式, True=快速模式)")
    print(f"MAX_WORKERS = {MAX_WORKERS} (并发抓取网站数)")

    if not ensure_keywords(keywords_path):
        return

    df = pd.read_excel(keywords_path)
    if "keyword" not in df.columns:
        log_func("Excel 文件中必须包含列名 'keyword'")
        return
    keywords = df["keyword"].dropna().astype(str).tolist()

    all_data = []
    failed = []

    log_func("\n开始预扫描可抓取链接数量，这一步只做 URL 收集，不抓邮箱...\n")
    raw_pairs = []

    for kw in keywords:
        log_func("\n" + "=" * 50)
        log_func(f"当前关键词: {kw}")
        try:
            urls = google_search(kw, pages=pages, headless=headless, log_func=log_func)
            for u in urls:
                raw_pairs.append((kw, u))
        except Exception as e:
            log_func(f"搜索关键词 '{kw}' 时出错: {e}")
            continue

    if not raw_pairs:
        log_func("没有可抓取的新链接（搜索没有结果）。")
        return

    # 去重（同一个 URL 只抓一次，keyword 用第一次的）
    seen = set()
    all_urls = []
    for kw, u in raw_pairs:
        if u not in seen:
            seen.add(u)
            all_urls.append((kw, u))

    total = len(all_urls)
    log_func(f"\n预扫描完成，本次总共需要抓取 {total} 个网址。\n")
    log_func("开始顺序抓取，每次只处理一个链接（浏览器保持打开状态）...\n")

    global_pbar = tqdm(total=total, desc="整体抓取进度", unit="site")

    # --- 创建浏览器实例，保持打开状态 ---
    driver = None
    temp_user_data = None
    if SELENIUM_AVAILABLE:
        try:
            import tempfile
            temp_user_data = tempfile.mkdtemp(prefix="chrome_scraper_")
            
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument(f"--user-data-dir={temp_user_data}")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            if headless:
                chrome_options.add_argument("--headless=new")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)
            log_func("✅ 浏览器已启动，将保持打开状态以便观察抓取过程\n")
        except Exception as e:
            log_func(f"⚠️ 启动浏览器失败，将使用requests方式: {e}\n")
            driver = None
    
    # --- 单线程顺序抓取（使用浏览器）---
    try:
        for idx, (kw, url) in enumerate(all_urls, 1):
            log_func(f"\n[{idx}/{total}] 正在打开浏览器抓取: {url}")
            try:
                info = scrape_site(url, driver=driver, timeout=20)
                info["keyword"] = kw
                
                if info:
                    all_data.append(info)
                    status = info.get("status", "unknown")
                    email_count = len(info.get("site_emails", []))
                    log_func(f"  ✓ 完成 - 状态: {status}, 邮箱数: {email_count}")
                else:
                    failed.append(f"{kw}: {url}")
                    log_func(f"  ✗ 失败 - 未获取到数据")
                    
            except Exception as e:
                failed.append(f"{kw}: {url} - {str(e)[:100]}")
                log_func(f"  ✗ 异常 - {str(e)[:100]}")
            
            global_pbar.update(1)
            
            # 站点之间等待，避免请求过快
            if idx < total:  # 最后一个不需要等待
                sleep_time = random.uniform(*SLEEP_BETWEEN_SITES)
                time.sleep(sleep_time)

        global_pbar.close()
    finally:
        # 关闭浏览器
        if driver:
            try:
                log_func("\n正在关闭浏览器...")
                driver.quit()
                # 清理临时目录
                try:
                    import shutil
                    if os.path.exists(temp_user_data):
                        shutil.rmtree(temp_user_data, ignore_errors=True)
                except Exception:
                    pass
            except Exception:
                pass

    if not all_data:
        log_func("本轮没有抓到任何站点数据。")
        return

    df_out = pd.DataFrame(all_data)

    # main_email：直接取官网邮箱第一条
    def pick_main(row):
        site_e = row.get("site_emails") or []
        if site_e:
            return site_e[0]
        return None

    df_out["main_email"] = df_out.apply(pick_main, axis=1)
    df_out["email_count"] = df_out["site_emails"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    # --------- 列名改为中文，并调整顺序，便于查看 ---------
    rename_map = {
        "keyword": "关键词",
        "url": "网址",
        "shop_name": "店铺名",
        "company_name": "公司名称",
        "description": "公司介绍",
        "address": "地址",
        "site_emails": "所有邮箱列表",
        "main_email": "主邮箱",
        "email_count": "邮箱数量",
        "phones": "电话列表",
        "whatsapp": "WhatsApp",
        "social_links": "社交链接",
        "facebook_links": "Facebook",
        "instagram_links": "Instagram",
        "tiktok_links": "TikTok",
        "twitter_links": "Twitter/X",
        "youtube_links": "YouTube",
        "pinterest_links": "Pinterest",
        "status": "抓取状态",
    }

    df_out = df_out.rename(columns=rename_map)

    # 优先显示的列顺序（不存在的列会被自动忽略）
    preferred_order = [
        "关键词",
        "网址",
        "公司名称",
        "店铺名",
        "公司介绍",
        "地址",
        "主邮箱",
        "邮箱数量",
        "所有邮箱列表",
        "电话列表",
        "WhatsApp",
        "Facebook",
        "Instagram",
        "TikTok",
        "Twitter/X",
        "YouTube",
        "Pinterest",
        "社交链接",
        "抓取状态",
    ]

    # 仅对存在的列应用顺序
    existing_cols = [c for c in preferred_order if c in df_out.columns]
    other_cols = [c for c in df_out.columns if c not in existing_cols]
    df_out = df_out[existing_cols + other_cols]

    if not output_path:
        output_path = os.path.abspath(DEFAULT_OUTPUT_ALL)

    try:
        df_out.to_excel(output_path, index=False)
        log_func(f"\n✅ 已保存 {len(df_out)} 条记录到 {output_path}")
    except PermissionError:
        alt_name = f"shop_contacts_all_{int(time.time())}.xlsx"
        alt_path = os.path.abspath(alt_name)
        df_out.to_excel(alt_path, index=False)
        log_func(
            f"\n⚠️ 保存 {output_path} 失败（可能文件被 Excel 打开），已改为保存到 {alt_path}"
        )
        output_path = alt_path

    if not failed_file:
        failed_file = os.path.abspath(DEFAULT_FAILED_FILE)

    if failed:
        try:
            with open(failed_file, "w", encoding="utf-8") as f:
                f.write("\n".join(failed))
            log_func(f"⚠️ {len(failed)} 个站点在抓取时出现异常，已记录到 {failed_file}")
        except Exception as e:
            log_func(f"保存失败记录文件时出错: {e}")

    log_func(f"\n🎉 任务完成！共抓取 {len(df_out)} 条记录")
    log_func(f"📁 结果文件: {output_path}")
    if failed:
        log_func(f"📁 失败记录: {failed_file}")


def main():
    """
    保留一个简单的命令行入口，方便不使用 GUI 时直接运行。
    """
    pages = input("每个关键词搜索页数 (默认 1): ").strip()
    pages = int(pages) if pages.isdigit() else 1
    run_shop_contact_scraper(
        keywords_path=DEFAULT_KEYWORDS_XLSX,
        pages=pages,
        output_path=DEFAULT_OUTPUT_ALL,
        failed_file=DEFAULT_FAILED_FILE,
        headless=False,
    )


if __name__ == "__main__":
    main()
