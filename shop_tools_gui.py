import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from shopify_partners_scraper_auto import scrape_shopify_partners
from shop_contact_scraper_google_login_v7_7 import run_shop_contact_scraper
from data_cleaner import clean_data


class CardFrame(ttk.Frame):
    """苹果风格卡片容器"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style="Card.TFrame")
        self._create_card_style()

    def _create_card_style(self):
        style = ttk.Style()
        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shop 工具合集")
        self.geometry("1100x700")
        
        # 苹果风格配色
        self.colors = {
            "bg": "#F5F5F7",  # 浅灰背景
            "card": "#FFFFFF",  # 白色卡片
            "text": "#1D1D1F",  # 深色文字
            "text_secondary": "#86868B",  # 次要文字
            "accent": "#007AFF",  # 苹果蓝
            "accent_hover": "#0051D5",
            "border": "#E5E5EA",  # 边框
            "success": "#34C759",  # 绿色
            "warning": "#FF9500",  # 橙色
        }
        
        self.configure(bg=self.colors["bg"])
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        """配置苹果风格样式"""
        style = ttk.Style()
        
        # 配置主题
        style.theme_use("clam")
        
        # 卡片样式
        style.configure("Card.TFrame", 
                       background=self.colors["card"],
                       relief="flat")
        
        # 标题样式
        style.configure("Title.TLabel",
                       background=self.colors["card"],
                       foreground=self.colors["text"],
                       font=("SF Pro Display", 20, "bold"))
        
        style.configure("Subtitle.TLabel",
                       background=self.colors["card"],
                       foreground=self.colors["text_secondary"],
                       font=("SF Pro Display", 13))
        
        style.configure("Label.TLabel",
                       background=self.colors["card"],
                       foreground=self.colors["text"],
                       font=("SF Pro Display", 12))
        
        # 主要按钮样式
        style.configure("Primary.TButton",
                       background=self.colors["accent"],
                       foreground="#FFFFFF",
                       font=("SF Pro Display", 13, "bold"),
                       padding=(20, 10),
                       borderwidth=0,
                       focuscolor="none")
        
        style.map("Primary.TButton",
                 background=[("active", self.colors["accent_hover"]),
                           ("pressed", self.colors["accent_hover"])])
        
        # 次要按钮样式
        style.configure("Secondary.TButton",
                       background="#F2F2F7",
                       foreground=self.colors["text"],
                       font=("SF Pro Display", 12),
                       padding=(12, 8),
                       borderwidth=0)
        
        style.map("Secondary.TButton",
                 background=[("active", "#E5E5EA")])
        
        # 输入框样式
        style.configure("Card.TEntry",
                       fieldbackground="#F2F2F7",
                       borderwidth=1,
                       relief="flat",
                       padding=8,
                       font=("SF Pro Display", 11))
        
        # Combobox样式
        style.configure("Card.TCombobox",
                       fieldbackground="#F2F2F7",
                       borderwidth=1,
                       relief="flat",
                       padding=8,
                       font=("SF Pro Display", 11))
        
        # Checkbutton样式
        style.configure("Card.TCheckbutton",
                       background=self.colors["card"],
                       foreground=self.colors["text"],
                       font=("SF Pro Display", 11))
        
        # Progressbar样式 - 简化配置以提高兼容性
        try:
            # 先复制默认布局
            style.layout("Card.TProgressbar", style.layout("Horizontal.TProgressbar"))
            # 然后配置颜色
            style.configure("Card.TProgressbar",
                           background=self.colors["accent"],
                           troughcolor="#E5E5EA",
                           borderwidth=0)
        except Exception:
            # 如果配置失败，使用默认样式
            pass

    # --------------- UI 构建 ---------------
    def _build_ui(self):
        # 主容器
        main_container = tk.Frame(self, bg=self.colors["bg"])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        main_container.columnconfigure(0, weight=0)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # 左侧操作区域（卡片式Tab）
        left_card = CardFrame(main_container)
        left_card.pack(side="left", fill="both", padx=(0, 15))
        left_card.configure(width=420)

        # Tab容器
        notebook = ttk.Notebook(left_card, style="Card.TNotebook")
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        self._build_shopify_tab(notebook)
        self._build_contact_tab(notebook)
        self._build_data_cleaner_tab(notebook)

        # 右侧日志区域（卡片式）
        right_card = CardFrame(main_container)
        right_card.pack(side="right", fill="both", expand=True)
        
        right_container = ttk.Frame(right_card, style="Card.TFrame")
        right_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 日志标题栏
        log_header = ttk.Frame(right_container, style="Card.TFrame")
        log_header.pack(fill="x", pady=(0, 15))

        ttk.Label(log_header, text="运行日志", style="Title.TLabel").pack(side="left")
        
        ttk.Button(log_header, text="导出日志", command=self._export_log,
                  style="Secondary.TButton").pack(side="right", padx=(10, 0))

        # 日志文本框
        log_frame = ttk.Frame(right_container, style="Card.TFrame")
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            state="disabled",
            bg="#1D1D1F",
            fg="#E5E5EA",
            font=("SF Mono", 10),
            insertbackground="#E5E5EA",
            selectbackground=self.colors["accent"],
            borderwidth=0,
            relief="flat",
            padx=15,
            pady=15
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

    def _create_card_section(self, parent, title=None):
        """创建卡片区域"""
        section = ttk.Frame(parent, style="Card.TFrame")
        if title:
            ttk.Label(section, text=title, style="Subtitle.TLabel").pack(anchor="w", pady=(0, 12))
        return section

    def _build_shopify_tab(self, notebook: ttk.Notebook):
        frame = CardFrame(notebook)
        notebook.add(frame, text="Shopify 合作伙伴")

        container = ttk.Frame(frame, style="Card.TFrame")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        ttk.Label(container, text="Shopify 合作伙伴抓取", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(container, text="从 Shopify 合作伙伴目录抓取联系信息", 
                 style="Subtitle.TLabel").pack(anchor="w", pady=(0, 25))

        # 国家选择卡片区域
        country_section = self._create_card_section(container, "选择国家")
        country_section.pack(fill="x", pady=(0, 20))

        ttk.Label(country_section, text="国家", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        
        self.country_var = tk.StringVar()
        country_options = [
            ("加拿大 (Canada)", "canada"),
            ("美国 (United States)", "united-states"),
            ("墨西哥 (Mexico)", "mexico"),
            ("澳大利亚 (Australia)", "australia"),
            ("新西兰 (New Zealand)", "new-zealand"),
            ("英国 (United Kingdom)", "united-kingdom"),
            ("比利时 (Belgium)", "belgium"),
            ("法国 (France)", "france"),
            ("德国 (Germany)", "germany"),
            ("西班牙 (Spain)", "spain"),
            ("葡萄牙 (Portugal)", "portugal"),
            ("丹麦 (Denmark)", "denmark"),
            ("爱尔兰 (Ireland)", "ireland"),
            ("瑞士 (Switzerland)", "switzerland"),
            ("意大利 (Italy)", "italy"),
            ("拉脱维亚 (Latvia)", "latvia"),
            ("立陶宛 (Lithuania)", "lithuania"),
            ("罗马尼亚 (Romania)", "romania"),
            ("乌克兰 (Ukraine)", "ukraine"),
            ("荷兰 (Netherlands)", "netherlands"),
            ("瑞典 (Sweden)", "sweden"),
            ("斯洛伐克 (Slovakia)", "slovakia"),
            ("捷克 (Czechia)", "czechia"),
            ("芬兰 (Finland)", "finland"),
            ("保加利亚 (Bulgaria)", "bulgaria"),
            ("波兰 (Poland)", "poland"),
            ("土耳其 (Türkiye)", "turkiye"),
            ("爱沙尼亚 (Estonia)", "estonia"),
            ("塞浦路斯 (Cyprus)", "cyprus"),
            ("希腊 (Greece)", "greece"),
            ("塞尔维亚 (Serbia)", "serbia"),
            ("奥地利 (Austria)", "austria"),
            ("克罗地亚 (Croatia)", "croatia"),
            ("匈牙利 (Hungary)", "hungary"),
            ("波斯尼亚和黑塞哥维那 (Bosnia & Herzegovina)", "bosnia-and-herzegovina"),
            ("挪威 (Norway)", "norway"),
            ("新加坡 (Singapore)", "singapore"),
            ("中国香港 (Hong Kong SAR)", "hong-kong-sar"),
            ("泰国 (Thailand)", "thailand"),
            ("印度 (India)", "india"),
            ("印度尼西亚 (Indonesia)", "indonesia"),
            ("日本 (Japan)", "japan"),
            ("巴基斯坦 (Pakistan)", "pakistan"),
            ("以色列 (Israel)", "israel"),
            ("俄罗斯 (Russia)", "russia"),
            ("阿联酋 (United Arab Emirates)", "united-arab-emirates"),
            ("越南 (Vietnam)", "vietnam"),
            ("马来西亚 (Malaysia)", "malaysia"),
            ("孟加拉国 (Bangladesh)", "bangladesh"),
            ("斯里兰卡 (Sri Lanka)", "sri-lanka"),
            ("中国 (China)", "china"),
            ("尼泊尔 (Nepal)", "nepal"),
            ("黎巴嫩 (Lebanon)", "lebanon"),
            ("菲律宾 (Philippines)", "philippines"),
            ("韩国 (South Korea)", "south-korea"),
            ("中国台湾 (Taiwan)", "taiwan"),
            ("科威特 (Kuwait)", "kuwait"),
            ("南非 (South Africa)", "south-africa"),
            ("尼日利亚 (Nigeria)", "nigeria"),
            ("埃及 (Egypt)", "egypt"),
            ("摩洛哥 (Morocco)", "morocco"),
            ("阿根廷 (Argentina)", "argentina"),
            ("智利 (Chile)", "chile"),
            ("巴西 (Brazil)", "brazil"),
            ("哥伦比亚 (Colombia)", "colombia"),
            ("秘鲁 (Peru)", "peru"),
            ("巴拿马 (Panama)", "panama"),
            ("危地马拉 (Guatemala)", "guatemala"),
        ]
        self.country_display_to_code = {display: code for display, code in country_options}
        displays = [d for d, _ in country_options]
        if displays:
            self.country_var.set(displays[0])
        
        country_combo = ttk.Combobox(country_section, textvariable=self.country_var,
                                    values=displays, state="readonly", style="Card.TCombobox",
                                    width=40)
        country_combo.pack(fill="x", pady=(0, 0))

        # 设置卡片区域
        settings_section = self._create_card_section(container, "设置")
        settings_section.pack(fill="x", pady=(0, 20))

        # 最大页数
        pages_frame = ttk.Frame(settings_section, style="Card.TFrame")
        pages_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(pages_frame, text="最大翻页数", style="Label.TLabel").pack(side="left", padx=(0, 15))
        self.max_pages_var = tk.IntVar(value=400)
        pages_entry = ttk.Entry(pages_frame, textvariable=self.max_pages_var, width=15,
                               style="Card.TEntry")
        pages_entry.pack(side="left")

        # 浏览器可见性
        self.visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_section, text="显示浏览器窗口",
                       variable=self.visible_var, style="Card.TCheckbutton").pack(anchor="w")

        # 输出文件卡片区域
        output_section = self._create_card_section(container, "输出文件")
        output_section.pack(fill="x", pady=(0, 20))

        self.shopify_output_var = tk.StringVar(value=os.path.abspath("shopify_partners.xlsx"))
        
        output_frame = ttk.Frame(output_section, style="Card.TFrame")
        output_frame.pack(fill="x", pady=(0, 8))
        output_entry = ttk.Entry(output_frame, textvariable=self.shopify_output_var,
                                style="Card.TEntry")
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(output_frame, text="选择", command=self._choose_shopify_output,
                  style="Secondary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(output_frame, text="打开文件夹",
                  command=lambda: self._open_in_explorer(self.shopify_output_var.get()),
                  style="Secondary.TButton").pack(side="left")

        # 进度条
        progress_section = ttk.Frame(container, style="Card.TFrame")
        progress_section.pack(fill="x", pady=(0, 20))
        ttk.Label(progress_section, text="任务进度", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        try:
            self.shopify_progress = ttk.Progressbar(progress_section, mode="indeterminate",
                                                   style="Card.TProgressbar", length=100)
        except Exception:
            # 如果自定义样式失败，使用默认样式
            self.shopify_progress = ttk.Progressbar(progress_section, mode="indeterminate", length=100)
        self.shopify_progress.pack(fill="x")

        # 运行按钮
        ttk.Button(container, text="开始抓取", command=self._run_shopify_thread,
                  style="Primary.TButton").pack(fill="x", pady=(10, 0))

    def _build_contact_tab(self, notebook: ttk.Notebook):
        frame = CardFrame(notebook)
        notebook.add(frame, text="站点邮箱抓取")

        # 创建主容器，使用grid布局确保按钮在底部
        main_container = ttk.Frame(frame, style="Card.TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)  # 按钮行不扩展
        
        # 内容区域（可滚动）
        container = ttk.Frame(main_container, style="Card.TFrame")
        container.grid(row=0, column=0, sticky="nsew")

        # 标题
        ttk.Label(container, text="Shop 站点邮箱抓取", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(container, text="通过 Google 搜索抓取 Shopify 站点联系信息",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(0, 25))

        # 关键词文件卡片区域
        kw_section = self._create_card_section(container, "关键词文件")
        kw_section.pack(fill="x", pady=(0, 20))

        self.kw_file_var = tk.StringVar(value=os.path.abspath("keywords.xlsx"))
        kw_frame = ttk.Frame(kw_section, style="Card.TFrame")
        kw_frame.pack(fill="x", pady=(0, 8))
        kw_entry = ttk.Entry(kw_frame, textvariable=self.kw_file_var, style="Card.TEntry")
        kw_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(kw_frame, text="选择", command=self._choose_kw_file,
                  style="Secondary.TButton").pack(side="left")

        # 设置卡片区域
        settings_section = self._create_card_section(container, "设置")
        settings_section.pack(fill="x", pady=(0, 20))

        # 搜索页数
        pages_frame = ttk.Frame(settings_section, style="Card.TFrame")
        pages_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(pages_frame, text="每个关键词页数", style="Label.TLabel").pack(side="left", padx=(0, 15))
        self.pages_var = tk.IntVar(value=1)
        pages_entry = ttk.Entry(pages_frame, textvariable=self.pages_var, width=15,
                               style="Card.TEntry")
        pages_entry.pack(side="left")

        # 浏览器可见性（默认打勾显示浏览器）
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_section, text="显示 Google 浏览器窗口",
                       variable=self.headless_var, style="Card.TCheckbutton").pack(anchor="w")

        # 输出文件卡片区域
        output_section = self._create_card_section(container, "输出文件")
        output_section.pack(fill="x", pady=(0, 20))

        # 结果Excel
        ttk.Label(output_section, text="结果 Excel", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        self.contact_output_var = tk.StringVar(value=os.path.abspath("shop_contacts_all.xlsx"))
        output_frame1 = ttk.Frame(output_section, style="Card.TFrame")
        output_frame1.pack(fill="x", pady=(0, 12))
        output_entry1 = ttk.Entry(output_frame1, textvariable=self.contact_output_var,
                                 style="Card.TEntry")
        output_entry1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(output_frame1, text="选择", command=self._choose_contact_output,
                  style="Secondary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(output_frame1, text="打开文件夹",
                  command=lambda: self._open_in_explorer(self.contact_output_var.get()),
                  style="Secondary.TButton").pack(side="left")

        # 失败记录txt
        ttk.Label(output_section, text="失败记录", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        self.failed_file_var = tk.StringVar(value=os.path.abspath("failed_keywords.txt"))
        output_frame2 = ttk.Frame(output_section, style="Card.TFrame")
        output_frame2.pack(fill="x", pady=(0, 0))
        output_entry2 = ttk.Entry(output_frame2, textvariable=self.failed_file_var,
                                 style="Card.TEntry")
        output_entry2.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(output_frame2, text="选择", command=self._choose_failed_file,
                  style="Secondary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(output_frame2, text="打开文件夹",
                  command=lambda: self._open_in_explorer(self.failed_file_var.get()),
                  style="Secondary.TButton").pack(side="left")

        # 进度条
        progress_section = ttk.Frame(container, style="Card.TFrame")
        progress_section.pack(fill="x", pady=(0, 20))
        ttk.Label(progress_section, text="任务进度", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        try:
            self.contact_progress = ttk.Progressbar(progress_section, mode="indeterminate",
                                                   style="Card.TProgressbar", length=100)
        except Exception:
            # 如果自定义样式失败，使用默认样式
            self.contact_progress = ttk.Progressbar(progress_section, mode="indeterminate", length=100)
        self.contact_progress.pack(fill="x")

        # 运行按钮（固定在底部，确保始终可见）
        button_frame = ttk.Frame(main_container, style="Card.TFrame")
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(button_frame, text="开始抓取", command=self._run_contact_thread,
                  style="Primary.TButton").pack(fill="x")

    def _build_data_cleaner_tab(self, notebook: ttk.Notebook):
        frame = CardFrame(notebook)
        notebook.add(frame, text="数据清洗")

        # 创建主容器，使用grid布局确保按钮在底部
        main_container = ttk.Frame(frame, style="Card.TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=0)  # 按钮行不扩展
        
        # 内容区域（可滚动）
        container = ttk.Frame(main_container, style="Card.TFrame")
        container.grid(row=0, column=0, sticky="nsew")

        # 标题
        ttk.Label(container, text="数据清洗工具", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(container, text="验证邮箱和WhatsApp号码有效性，支持列表形式数据",
                 style="Subtitle.TLabel").pack(anchor="w", pady=(0, 25))

        # 输入文件卡片区域
        input_section = self._create_card_section(container, "输入文件")
        input_section.pack(fill="x", pady=(0, 20))

        self.cleaner_input_var = tk.StringVar()
        input_frame = ttk.Frame(input_section, style="Card.TFrame")
        input_frame.pack(fill="x", pady=(0, 8))
        input_entry = ttk.Entry(input_frame, textvariable=self.cleaner_input_var, style="Card.TEntry")
        input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(input_frame, text="选择", command=self._choose_cleaner_input,
                  style="Secondary.TButton").pack(side="left")

        # 输出文件卡片区域
        output_section = self._create_card_section(container, "输出文件")
        output_section.pack(fill="x", pady=(0, 20))

        self.cleaner_output_var = tk.StringVar(value=os.path.abspath("cleaned_data.xlsx"))
        output_frame = ttk.Frame(output_section, style="Card.TFrame")
        output_frame.pack(fill="x", pady=(0, 8))
        output_entry = ttk.Entry(output_frame, textvariable=self.cleaner_output_var, style="Card.TEntry")
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(output_frame, text="选择", command=self._choose_cleaner_output,
                  style="Secondary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(output_frame, text="打开文件夹",
                  command=lambda: self._open_in_explorer(self.cleaner_output_var.get()),
                  style="Secondary.TButton").pack(side="left")

        # 列名设置卡片区域（可选）
        columns_section = self._create_card_section(container, "列名设置（可选）")
        columns_section.pack(fill="x", pady=(0, 20))

        ttk.Label(columns_section, text="邮箱列名（留空则自动检测，多个用逗号分隔）", 
                 style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        self.cleaner_email_cols_var = tk.StringVar()
        email_cols_entry = ttk.Entry(columns_section, textvariable=self.cleaner_email_cols_var,
                                    style="Card.TEntry")
        email_cols_entry.pack(fill="x", pady=(0, 12))

        ttk.Label(columns_section, text="WhatsApp列名（留空则自动检测，多个用逗号分隔）", 
                 style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        self.cleaner_whatsapp_cols_var = tk.StringVar()
        whatsapp_cols_entry = ttk.Entry(columns_section, textvariable=self.cleaner_whatsapp_cols_var,
                                       style="Card.TEntry")
        whatsapp_cols_entry.pack(fill="x")

        # 验证选项卡片区域
        options_section = self._create_card_section(container, "验证选项")
        options_section.pack(fill="x", pady=(0, 20))

        self.cleaner_check_mx_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_section, text="检查邮箱MX记录（验证域名是否有邮件服务器）",
                       variable=self.cleaner_check_mx_var, style="Card.TCheckbutton").pack(anchor="w", pady=(0, 8))

        self.cleaner_check_smtp_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_section, text="进行SMTP验证（较慢但更准确，验证邮箱是否存在）",
                       variable=self.cleaner_check_smtp_var, style="Card.TCheckbutton").pack(anchor="w", pady=(0, 8))

        self.cleaner_check_wa_online_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_section, text="在线验证WhatsApp（需要API，暂未实现）",
                       variable=self.cleaner_check_wa_online_var, style="Card.TCheckbutton").pack(anchor="w")

        # 进度条
        progress_section = ttk.Frame(container, style="Card.TFrame")
        progress_section.pack(fill="x", pady=(0, 20))
        ttk.Label(progress_section, text="任务进度", style="Label.TLabel").pack(anchor="w", pady=(0, 8))
        try:
            self.cleaner_progress = ttk.Progressbar(progress_section, mode="indeterminate",
                                                   style="Card.TProgressbar", length=100)
        except Exception:
            # 如果自定义样式失败，使用默认样式
            self.cleaner_progress = ttk.Progressbar(progress_section, mode="indeterminate", length=100)
        self.cleaner_progress.pack(fill="x")

        # 运行按钮（固定在底部，确保始终可见）
        button_frame = ttk.Frame(main_container, style="Card.TFrame")
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(button_frame, text="开始清洗", command=self._run_cleaner_thread,
                  style="Primary.TButton").pack(fill="x")

    # --------------- 文件选择 ---------------
    def _choose_shopify_output(self):
        path = filedialog.asksaveasfilename(
            title="选择保存路径",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if path:
            self.shopify_output_var.set(path)

    def _choose_kw_file(self):
        path = filedialog.askopenfilename(
            title="选择关键词 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if path:
            self.kw_file_var.set(path)

    def _choose_contact_output(self):
        path = filedialog.asksaveasfilename(
            title="选择结果 Excel 保存路径",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if path:
            self.contact_output_var.set(path)

    def _choose_failed_file(self):
        path = filedialog.asksaveasfilename(
            title="选择失败记录 txt 保存路径",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if path:
            self.failed_file_var.set(path)

    def _choose_cleaner_input(self):
        path = filedialog.askopenfilename(
            title="选择要清洗的数据文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if path:
            self.cleaner_input_var.set(path)
            # 自动设置输出文件名
            base_name = os.path.splitext(path)[0]
            self.cleaner_output_var.set(f"{base_name}_cleaned.xlsx")

    def _choose_cleaner_output(self):
        path = filedialog.asksaveasfilename(
            title="选择清洗结果保存路径",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if path:
            self.cleaner_output_var.set(path)

    def _export_log(self):
        """导出右侧日志为 txt 文件"""
        content = self.log_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "当前日志为空，无需导出。")
            return

        path = filedialog.asksaveasfilename(
            title="选择日志保存路径",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("成功", f"日志已保存到：\n{path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存日志失败：{e}")

    def _open_in_explorer(self, path: str):
        """在资源管理器中打开文件所在文件夹"""
        path = (path or "").strip()
        if not path:
            messagebox.showwarning("提示", "路径为空，无法打开文件夹。")
            return

        dir_path = path
        if not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)

        if not dir_path or not os.path.exists(dir_path):
            messagebox.showwarning("提示", f"路径不存在：{dir_path}")
            return

        try:
            os.startfile(dir_path)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败：{e}")

    # --------------- 日志输出 ---------------
    def log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    # --------------- 运行逻辑（线程） ---------------
    def _run_shopify_thread(self):
        display = self.country_var.get().strip()
        country = self.country_display_to_code.get(display, display)
        if not country:
            messagebox.showwarning("提示", "请选择国家")
            return

        try:
            max_pages = int(self.max_pages_var.get())
        except Exception:
            messagebox.showwarning("提示", "最大翻页数必须是整数")
            return

        output_path = self.shopify_output_var.get().strip()
        if not output_path:
            messagebox.showwarning("提示", "请设置保存文件路径")
            return

        self.log(f"\n=== Shopify 合作伙伴抓取开始（{country}）===\n")

        self.shopify_progress.start(10)

        t = threading.Thread(
            target=self._run_shopify, args=(country, max_pages, output_path), daemon=True
        )
        t.start()

    def _run_shopify(self, country, max_pages, output_path):
        try:
            scrape_shopify_partners(
                country=country,
                visible=self.visible_var.get(),
                max_pages=max_pages,
                output_path=output_path,
                log_func=self.log,
            )
        except Exception as e:
            self.log(f"运行出错：{e}")
            messagebox.showerror("错误", f"Shopify 抓取出错：{e}")
        finally:
            def _finish():
                self.shopify_progress.stop()
                try:
                    if os.path.exists(os.path.dirname(output_path) or "."):
                        msg = f"Shopify 合作伙伴抓取完成！\n结果文件：\n{output_path}"
                    else:
                        msg = "Shopify 合作伙伴抓取完成！"
                    messagebox.showinfo("完成", msg)
                except Exception:
                    pass

            self.after(0, _finish)

    def _run_contact_thread(self):
        kw_path = self.kw_file_var.get().strip()
        if not kw_path:
            messagebox.showwarning("提示", "请先选择关键词 Excel 文件")
            return

        try:
            pages = int(self.pages_var.get())
        except Exception:
            messagebox.showwarning("提示", "页数必须是整数")
            return

        output_path = self.contact_output_var.get().strip()
        if not output_path:
            messagebox.showwarning("提示", "请设置结果 Excel 路径")
            return

        failed_file = self.failed_file_var.get().strip()
        if not failed_file:
            messagebox.showwarning("提示", "请设置失败记录 txt 路径")
            return

        self.log("\n=== Shop 站点邮箱抓取开始 ===\n")

        self.contact_progress.start(10)

        t = threading.Thread(
            target=self._run_contact,
            args=(kw_path, pages, output_path, failed_file),
            daemon=True,
        )
        t.start()

    def _run_contact(self, kw_path, pages, output_path, failed_file):
        try:
            run_shop_contact_scraper(
                keywords_path=kw_path,
                pages=pages,
                output_path=output_path,
                failed_file=failed_file,
                headless=not self.headless_var.get(),
                log_func=self.log,
            )
        except Exception as e:
            self.log(f"运行出错：{e}")
            messagebox.showerror("错误", f"站点邮箱抓取出错：{e}")
        finally:
            def _finish():
                self.contact_progress.stop()
                try:
                    msg = (
                        "站点邮箱抓取完成！\n"
                        f"结果文件：\n{output_path}\n\n"
                        f"失败记录（如有）：\n{failed_file}"
                    )
                    messagebox.showinfo("完成", msg)
                except Exception:
                    pass

            self.after(0, _finish)

    def _run_cleaner_thread(self):
        input_path = self.cleaner_input_var.get().strip()
        if not input_path:
            messagebox.showwarning("提示", "请先选择要清洗的数据文件")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("错误", f"文件不存在：{input_path}")
            return

        output_path = self.cleaner_output_var.get().strip()
        if not output_path:
            messagebox.showwarning("提示", "请设置输出文件路径")
            return

        # 解析列名
        email_cols = None
        email_cols_str = self.cleaner_email_cols_var.get().strip()
        if email_cols_str:
            email_cols = [col.strip() for col in email_cols_str.split(',') if col.strip()]

        whatsapp_cols = None
        whatsapp_cols_str = self.cleaner_whatsapp_cols_var.get().strip()
        if whatsapp_cols_str:
            whatsapp_cols = [col.strip() for col in whatsapp_cols_str.split(',') if col.strip()]

        self.log("\n=== 数据清洗开始 ===\n")
        self.log(f"输入文件: {input_path}")
        self.log(f"输出文件: {output_path}")

        self.cleaner_progress.start(10)

        t = threading.Thread(
            target=self._run_cleaner,
            args=(input_path, output_path, email_cols, whatsapp_cols),
            daemon=True,
        )
        t.start()

    def _run_cleaner(self, input_path, output_path, email_cols, whatsapp_cols):
        try:
            stats = clean_data(
                input_file=input_path,
                output_file=output_path,
                email_columns=email_cols,
                whatsapp_columns=whatsapp_cols,
                check_email_mx=self.cleaner_check_mx_var.get(),
                check_email_smtp=self.cleaner_check_smtp_var.get(),
                check_whatsapp_online=self.cleaner_check_wa_online_var.get(),
                progress_callback=self.log,
            )

            # 输出统计信息
            self.log("\n=== 数据清洗完成 ===\n")
            self.log(f"总行数: {stats['total_rows']}")
            self.log(f"有效行数: {stats['valid_rows']}")
            self.log(f"无效行数: {stats['invalid_rows']}")

            if stats['email_stats']:
                self.log("\n📧 邮箱验证统计:")
                for col, stat in stats['email_stats'].items():
                    self.log(f"  {col}: 总数={stat['total']}, 有效={stat['valid']}, 无效={stat['invalid']}")

            if stats['whatsapp_stats']:
                self.log("\n📱 WhatsApp验证统计:")
                for col, stat in stats['whatsapp_stats'].items():
                    self.log(f"  {col}: 总数={stat['total']}, 有效={stat['valid']}, 无效={stat['invalid']}")

            self.log(f"\n结果已保存到: {output_path}")

        except Exception as e:
            self.log(f"运行出错：{e}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("错误", f"数据清洗出错：{e}")
        finally:
            def _finish():
                self.cleaner_progress.stop()
                try:
                    msg = (
                        "数据清洗完成！\n"
                        f"结果文件：\n{output_path}"
                    )
                    messagebox.showinfo("完成", msg)
                except Exception:
                    pass

            self.after(0, _finish)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
