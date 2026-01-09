"""
数据清洗脚本
功能：
1. 读取Excel/CSV文件
2. 验证邮箱有效性（格式验证和可选的SMTP验证）
3. 验证WhatsApp号码有效性
4. 处理列表形式的号码和邮箱
5. 保存验证结果到新表格
"""

import os
import sys
import re
import ast
import subprocess
import smtplib
import time
from typing import List, Dict, Tuple, Optional

# ---------- 自动安装依赖 ----------
required = ["pandas", "openpyxl", "dnspython", "phonenumbers"]
for pkg in required:
    try:
        if pkg == "dnspython":
            __import__("dns")
        elif pkg == "phonenumbers":
            __import__("phonenumbers")
        else:
            __import__(pkg.replace("-", "_"))
    except ImportError:
        try:
            print(f"[安装] 未检测到 {pkg}，正在安装...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except Exception as e:
            print(f"[警告] 安装 {pkg} 失败: {e}")
            pass

import pandas as pd

# 尝试导入 dns.resolver，如果失败则使用备用方案
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    # 如果没有 dnspython，MX 和 SMTP 验证将不可用

# 尝试导入 phonenumbers，如果失败则使用备用方案
try:
    import phonenumbers
    from phonenumbers import NumberParseException, PhoneNumberType
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False
    # 如果没有 phonenumbers，使用简单的验证方法


class EmailValidator:
    """邮箱验证器"""
    
    # 邮箱格式正则表达式
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def __init__(self, check_smtp: bool = False, check_mx: bool = False):
        """
        初始化邮箱验证器
        - check_smtp: 是否进行SMTP验证（较慢但更准确）
        - check_mx: 是否检查MX记录（检查域名是否存在邮件服务器）
        """
        self.check_smtp = check_smtp
        self.check_mx = check_mx
    
    def validate_format(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email or not isinstance(email, str):
            return False
        email = email.strip()
        return bool(self.EMAIL_REGEX.match(email))
    
    def validate_mx_record(self, email: str) -> bool:
        """验证邮箱域名的MX记录是否存在"""
        if not DNS_AVAILABLE:
            return False
        try:
            domain = email.split('@')[1]
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except Exception:
            return False
    
    def validate_smtp(self, email: str, timeout: int = 5) -> bool:
        """通过SMTP验证邮箱是否存在（不发送邮件）"""
        if not DNS_AVAILABLE:
            return False
        try:
            domain = email.split('@')[1]
            # 获取MX记录
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                return False
            
            # 连接到邮件服务器
            mx_host = str(mx_records[0].exchange)
            server = smtplib.SMTP(timeout=timeout)
            server.set_debuglevel(0)
            server.connect(mx_host, 25)
            server.helo(server.local_hostname)
            server.mail('test@example.com')
            code, message = server.rcpt(email)
            server.quit()
            
            return code == 250
        except Exception:
            return False
    
    def validate(self, email: str) -> Tuple[bool, str]:
        """
        验证邮箱
        返回: (是否有效, 验证结果说明)
        """
        if not email or pd.isna(email):
            return False, "空值"
        
        email = str(email).strip()
        
        # 格式验证
        if not self.validate_format(email):
            return False, "格式无效"
        
        # MX记录验证（可选）
        if self.check_mx:
            if not self.validate_mx_record(email):
                return False, "域名无MX记录"
        
        # SMTP验证（可选，较慢）
        if self.check_smtp:
            if not self.validate_smtp(email):
                return False, "SMTP验证失败"
        
        return True, "有效"


class WhatsAppValidator:
    """WhatsApp号码验证器"""
    
    def __init__(self, check_online: bool = False, mobile_only: bool = True):
        """
        初始化WhatsApp验证器
        - check_online: 是否在线验证（需要API，默认False）
        - mobile_only: 是否只接受移动号码（WhatsApp主要支持移动号，默认True）
        """
        self.check_online = check_online
        self.mobile_only = mobile_only
    
    def normalize_phone(self, phone: str) -> str:
        """标准化电话号码（移除空格、横线等）"""
        if not phone or pd.isna(phone):
            return ""
        phone = str(phone).strip()
        # 移除所有非数字字符（除了+号）
        phone = re.sub(r'[^\d+]', '', phone)
        return phone
    
    def validate_format_simple(self, phone: str) -> Tuple[bool, str]:
        """
        简单验证WhatsApp号码格式（备用方案，当phonenumbers不可用时）
        返回: (是否有效, 标准化后的号码)
        """
        if not phone or pd.isna(phone):
            return False, ""
        
        phone = self.normalize_phone(phone)
        
        if not phone:
            return False, ""
        
        # WhatsApp号码规则：
        # 1. 必须以+开头（国际格式）
        # 2. 长度通常在7-15位（不包括+号）
        # 3. 只包含数字
        
        if not phone.startswith('+'):
            # 如果没有+号，尝试添加（假设是国际号码）
            if phone.isdigit() and len(phone) >= 7:
                phone = '+' + phone
            else:
                return False, ""
        
        # 移除+号后检查长度
        digits = phone[1:]
        if not digits.isdigit():
            return False, ""
        
        if len(digits) < 7 or len(digits) > 15:
            return False, ""
        
        return True, phone
    
    def validate_format(self, phone: str) -> Tuple[bool, str]:
        """
        验证WhatsApp号码格式
        返回: (是否有效, 标准化后的号码)
        """
        if not phone or pd.isna(phone):
            return False, ""
        
        # 如果phonenumbers库可用，使用更准确的验证
        if PHONENUMBERS_AVAILABLE:
            try:
                # 尝试解析号码（自动检测国家代码）
                parsed_number = phonenumbers.parse(phone, None)
                
                # 检查号码是否有效
                if not phonenumbers.is_valid_number(parsed_number):
                    return False, ""
                
                # 如果只接受移动号码，检查号码类型
                if self.mobile_only:
                    number_type = phonenumbers.number_type(parsed_number)
                    # WhatsApp主要支持移动号码
                    if number_type not in [PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE]:
                        return False, ""
                
                # 格式化为E.164标准格式（+国家代码+号码）
                normalized = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                return True, normalized
                
            except NumberParseException:
                # 解析失败，尝试简单验证
                return self.validate_format_simple(phone)
            except Exception:
                # 其他错误，回退到简单验证
                return self.validate_format_simple(phone)
        else:
            # phonenumbers不可用，使用简单验证
            return self.validate_format_simple(phone)
    
    def validate(self, phone: str) -> Tuple[bool, str, str]:
        """
        验证WhatsApp号码
        返回: (是否有效, 标准化号码, 验证结果说明)
        """
        is_valid, normalized = self.validate_format(phone)
        
        if not is_valid:
            return False, "", "格式无效"
        
        # 如果使用phonenumbers库，可以提供更详细的验证信息
        if PHONENUMBERS_AVAILABLE and is_valid:
            try:
                parsed_number = phonenumbers.parse(normalized, None)
                number_type = phonenumbers.number_type(parsed_number)
                
                if number_type == PhoneNumberType.MOBILE:
                    return True, normalized, "有效（移动号码）"
                elif number_type == PhoneNumberType.FIXED_LINE_OR_MOBILE:
                    return True, normalized, "有效（移动/固话）"
                else:
                    return True, normalized, "有效"
            except Exception:
                pass
        
        # 在线验证（需要API，这里只做占位）
        if self.check_online:
            # TODO: 集成WhatsApp API进行在线验证
            pass
        
        return True, normalized, "有效"


def parse_list_field(value) -> List[str]:
    """
    解析列表形式的字段值
    支持格式：
    - Python列表字符串: "['a@example.com', 'b@example.com']"
    - 逗号分隔: "a@example.com, b@example.com"
    - 分号分隔: "a@example.com; b@example.com"
    - 换行分隔: "a@example.com\nb@example.com"
    
    同时会：
    - 过滤掉图片链接（.png, .jpg, .jpeg, .gif等）
    - 清理方括号等符号
    """
    if pd.isna(value) or not value:
        return []
    
    value = str(value).strip()
    if not value:
        return []
    
    # 清理方括号等符号
    value = re.sub(r'[\[\]]', '', value)  # 移除方括号
    value = value.strip()
    
    # 尝试解析为Python列表
    if value.startswith('[') and value.endswith(']'):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                items = [str(item).strip() for item in parsed if item]
            else:
                items = []
        except:
            items = []
    else:
        # 尝试其他分隔符
        items = []
        separators = [',', ';', '\n', '|']
        for sep in separators:
            if sep in value:
                items = [item.strip() for item in value.split(sep) if item.strip()]
                if len(items) > 1:
                    break
        
        # 如果没有找到分隔符，使用单个值
        if not items:
            items = [value]
    
    # 过滤掉图片链接、文件链接和空值
    filtered_items = []
    # 文件扩展名列表（包括各种图片、视频、文档、脚本等）
    file_extensions = [
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.avif',
        '.js', '.css', '.html', '.htm', '.xml', '.json',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.7z', '.tar', '.gz',
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
        '.mp3', '.wav', '.flac', '.aac',
        '.mp', '.m4a', '.m4v',  # 添加.mp等
        '.exe', '.dll', '.so', '.dylib',
        '.ttf', '.woff', '.woff2', '.eot', '.otf',
        '.compressed'  # 添加.compressed
    ]
    # 匹配文件扩展名的正则表达式模式（包括@2x等格式）
    # 这些模式会匹配包含文件扩展名的任何字符串
    file_patterns = [
        # 匹配 @2x.compressed-xxx.avif 这种复杂格式
        r'@\d+x\.compressed-[a-zA-Z0-9]+\.(avif|png|jpg|jpeg|webp|svg|gif)',
        r'@\d+x\.(png|jpg|jpeg|gif|webp|svg|avif|mp)',  # @2x.png, @2x.mp等
        r'\.(png|jpg|jpeg|gif|webp|svg|avif|mp)@\d+x',  # .png@2x等
        # 匹配以文件扩展名结尾的字符串（包括.compressed-xxx.avif格式）
        r'\.compressed-[a-zA-Z0-9]+\.(avif|png|jpg|jpeg|webp|svg|gif)(\s|$|,|;|\||\[|\])',
        r'\.(avif|css|js|mp)(\s|$|,|;|\||@|\[|\])',  # .avif, .css, .js, .mp等（后面跟空格、结束、逗号、分号、竖线、@或方括号）
        r'\.(png|jpg|jpeg|gif|bmp|webp|svg)(\s|$|,|;|\||\[|\])',  # .png, .jpg等
        r'\.(html|htm|xml|json|pdf|doc|docx|xls|xlsx|ppt|pptx)(\s|$|,|;|\||\[|\])',  # 其他文档格式
        r'\.(zip|rar|7z|tar|gz|mp4|avi|mov|wmv|flv|mkv|mp3|wav|flac|aac)(\s|$|,|;|\||\[|\])',  # 其他文件格式
        # 匹配文件名.扩展名格式（包括复杂文件名）
        r'[a-zA-Z0-9_@.-]+\.(avif|css|js|mp)(\s|$|,|;|\||@|\[|\])',  # 文件名.扩展名格式，如 ecom-swiper@11.0.5.js
        # 匹配包含.compressed的文件
        r'\.compressed',
    ]
    
    for item in items:
        item_original = item
        item = item.strip()
        if not item:
            continue
        
        # 检查是否包含文件链接模式
        is_file = False
        item_lower = item.lower()
        
        # 检查是否以文件扩展名结尾
        for ext in file_extensions:
            if item_lower.endswith(ext):
                is_file = True
                break
        
        # 检查是否包含文件扩展名模式（包括@2x等格式和中间包含扩展名的情况）
        if not is_file:
            for pattern in file_patterns:
                if re.search(pattern, item_lower):
                    is_file = True
                    break
        
        # 特别检查：如果数据中包含类似 "xxx.css", "xxx.js", "xxx.avif", "xxx.mp" 的模式
        # 或者包含 .compressed 的文件
        if not is_file:
            # 检查是否包含文件名.扩展名的模式（如 ecom-swiper@11.0.5.js 或 ai-category-card-video-gen@2x.compressed-xxx.avif）
            if re.search(r'[a-zA-Z0-9_@.-]+\.(avif|css|js|mp|compressed)', item_lower):
                is_file = True
        
        # 如果整个项看起来就是一个文件链接或包含文件扩展名，直接过滤掉
        if is_file:
            continue
        
        # 再次清理可能的符号
        item = re.sub(r'[\[\](){}"\']', '', item).strip()
        if item:
            filtered_items.append(item)
    
    return filtered_items


def validate_emails_in_field(
    value, 
    validator: EmailValidator
) -> Tuple[List[str], List[str], List[str]]:
    """
    验证字段中的邮箱（可能是列表形式）
    返回: (有效邮箱列表, 无效邮箱列表, 验证结果列表)
    """
    emails = parse_list_field(value)
    valid_emails = []
    invalid_emails = []
    results = []
    
    for email in emails:
        is_valid, reason = validator.validate(email)
        if is_valid:
            valid_emails.append(email)
            results.append(f"{email} - {reason}")
        else:
            invalid_emails.append(email)
            results.append(f"{email} - {reason}")
    
    return valid_emails, invalid_emails, results


def validate_whatsapp_in_field(
    value,
    validator: WhatsAppValidator
) -> Tuple[List[str], List[str], List[str]]:
    """
    验证字段中的WhatsApp号码（可能是列表形式）
    返回: (有效号码列表, 无效号码列表, 验证结果列表)
    """
    phones = parse_list_field(value)
    valid_phones = []
    invalid_phones = []
    results = []
    
    for phone in phones:
        is_valid, normalized, reason = validator.validate(phone)
        if is_valid:
            valid_phones.append(normalized)
            results.append(f"{normalized} - {reason}")
        else:
            invalid_phones.append(phone)
            results.append(f"{phone} - {reason}")
    
    return valid_phones, invalid_phones, results


def clean_data_batch(
    input_files: List[str],
    output_dir: Optional[str] = None,
    email_columns: Optional[List[str]] = None,
    whatsapp_columns: Optional[List[str]] = None,
    check_email_mx: bool = False,
    check_email_smtp: bool = False,
    check_whatsapp_online: bool = False,
    progress_callback=None
) -> Dict:
    """
    批量处理多个文件
    
    参数:
    - input_files: 输入文件路径列表
    - output_dir: 输出目录，如果为None则使用输入文件所在目录
    - 其他参数同 clean_data
    
    返回: 统计信息字典
    """
    if not input_files:
        raise ValueError("输入文件列表不能为空")
    
    if progress_callback:
        progress_callback(f"开始批量处理 {len(input_files)} 个文件...")
    
    all_stats = {
        'total_files': len(input_files),
        'successful_files': 0,
        'failed_files': 0,
        'file_results': []
    }
    
    for idx, input_file in enumerate(input_files, 1):
        if progress_callback:
            progress_callback(f"\n[{idx}/{len(input_files)}] 处理文件: {os.path.basename(input_file)}")
        
        try:
            # 生成输出文件名
            if output_dir:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(output_dir, f"{base_name}_已清洗.xlsx")
            else:
                input_dir = os.path.dirname(input_file) or "."
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_file = os.path.join(input_dir, f"{base_name}_已清洗.xlsx")
            
            # 处理单个文件
            stats = clean_data(
                input_file=input_file,
                output_file=output_file,
                email_columns=email_columns,
                whatsapp_columns=whatsapp_columns,
                check_email_mx=check_email_mx,
                check_email_smtp=check_email_smtp,
                check_whatsapp_online=check_whatsapp_online,
                progress_callback=lambda msg: progress_callback(f"  {msg}") if progress_callback else None
            )
            
            all_stats['successful_files'] += 1
            all_stats['file_results'].append({
                'file': input_file,
                'output': output_file,
                'status': 'success',
                'stats': stats
            })
            
            if progress_callback:
                progress_callback(f"  ✓ 完成: {os.path.basename(output_file)}")
                
        except Exception as e:
            all_stats['failed_files'] += 1
            all_stats['file_results'].append({
                'file': input_file,
                'output': None,
                'status': 'failed',
                'error': str(e)
            })
            if progress_callback:
                progress_callback(f"  ✗ 失败: {e}")
    
    if progress_callback:
        progress_callback(f"\n批量处理完成: 成功 {all_stats['successful_files']}/{all_stats['total_files']}, 失败 {all_stats['failed_files']}/{all_stats['total_files']}")
    
    return all_stats


def clean_data(
    input_file: str,
    output_file: str,
    email_columns: Optional[List[str]] = None,
    whatsapp_columns: Optional[List[str]] = None,
    check_email_mx: bool = False,
    check_email_smtp: bool = False,
    check_whatsapp_online: bool = False,
    progress_callback=None
) -> Dict:
    """
    数据清洗主函数
    
    参数:
    - input_file: 输入文件路径（支持.xlsx, .xls, .csv）
    - output_file: 输出文件路径
    - email_columns: 邮箱列名列表，如果为None则自动检测
    - whatsapp_columns: WhatsApp列名列表，如果为None则自动检测
    - check_email_mx: 是否检查邮箱MX记录
    - check_email_smtp: 是否进行SMTP验证
    - check_whatsapp_online: 是否在线验证WhatsApp
    - progress_callback: 进度回调函数
    
    返回: 统计信息字典
    """
    # 读取文件
    if progress_callback:
        progress_callback("正在读取文件...")
    
    file_ext = os.path.splitext(input_file)[1].lower()
    if file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(input_file)
    elif file_ext == '.csv':
        df = pd.read_csv(input_file, encoding='utf-8-sig')
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")
    
    if progress_callback:
        progress_callback(f"已读取 {len(df)} 行数据，{len(df.columns)} 列")
    
    # 自动检测邮箱和WhatsApp列
    if email_columns is None:
        email_columns = [col for col in df.columns 
                        if any(keyword in col.lower() for keyword in ['email', '邮箱', 'mail', 'e-mail'])]
    
    if whatsapp_columns is None:
        whatsapp_columns = [col for col in df.columns 
                           if any(keyword in col.lower() for keyword in ['whatsapp', 'wa', 'phone', '电话', '号码', 'mobile'])]
    
    if progress_callback:
        progress_callback(f"检测到邮箱列: {email_columns}")
        progress_callback(f"检测到WhatsApp列: {whatsapp_columns}")
    
    # 初始化验证器
    email_validator = EmailValidator(check_smtp=check_email_smtp, check_mx=check_email_mx)
    whatsapp_validator = WhatsAppValidator(check_online=check_whatsapp_online)
    
    # 创建结果DataFrame
    result_df = df.copy()
    
    # 统计信息
    stats = {
        'total_rows': len(df),
        'email_stats': {},
        'whatsapp_stats': {},
        'valid_rows': 0,
        'invalid_rows': 0
    }
    
    # 处理邮箱列 - 收集所有邮箱数据
    all_valid_emails = []  # 每行一个列表，包含所有有效邮箱
    all_invalid_emails = []  # 每行一个列表，包含所有无效邮箱
    
    # 初始化所有行的列表
    for _ in range(len(df)):
        all_valid_emails.append([])
        all_invalid_emails.append([])
    
    for col in email_columns:
        if col not in df.columns:
            continue
        
        col_total = 0
        col_valid = 0
        col_invalid = 0
        
        for idx, value in enumerate(df[col]):
            if progress_callback and idx % 10 == 0:
                progress_callback(f"正在验证邮箱列 '{col}': {idx}/{len(df)}")
            
            valid_emails, invalid_emails, _ = validate_emails_in_field(value, email_validator)
            
            # 统计当前列的邮箱数量
            col_total += len(valid_emails) + len(invalid_emails)
            col_valid += len(valid_emails)
            col_invalid += len(invalid_emails)
            
            # 合并邮箱（去重）
            for email in valid_emails:
                if email and email not in all_valid_emails[idx]:
                    all_valid_emails[idx].append(email)
            for email in invalid_emails:
                if email and email not in all_invalid_emails[idx]:
                    all_invalid_emails[idx].append(email)
        
        stats['email_stats'][col] = {
            'total': col_total,
            'valid': col_valid,
            'invalid': col_invalid
        }
    
    # 找到最大邮箱数量，用于创建列
    max_valid_emails = max(len(emails) for emails in all_valid_emails) if all_valid_emails else 0
    max_invalid_emails = max(len(emails) for emails in all_invalid_emails) if all_invalid_emails else 0
    
    # 创建有效邮箱列（每个邮箱一列）
    for i in range(max_valid_emails):
        col_name = f"有效邮箱_{i+1}"
        result_df[col_name] = [emails[i] if i < len(emails) else '' for emails in all_valid_emails]
    
    # 创建无效邮箱列（每个邮箱一列）
    for i in range(max_invalid_emails):
        col_name = f"无效邮箱_{i+1}"
        result_df[col_name] = [emails[i] if i < len(emails) else '' for emails in all_invalid_emails]
    
    # 处理WhatsApp列 - 收集所有号码数据
    all_valid_phones = []  # 每行一个列表，包含所有有效号码
    all_invalid_phones = []  # 每行一个列表，包含所有无效号码
    
    # 初始化所有行的列表
    for _ in range(len(df)):
        all_valid_phones.append([])
        all_invalid_phones.append([])
    
    for col in whatsapp_columns:
        if col not in df.columns:
            continue
        
        col_total = 0
        col_valid = 0
        col_invalid = 0
        
        for idx, value in enumerate(df[col]):
            if progress_callback and idx % 10 == 0:
                progress_callback(f"正在验证WhatsApp列 '{col}': {idx}/{len(df)}")
            
            valid_phones, invalid_phones, _ = validate_whatsapp_in_field(value, whatsapp_validator)
            
            # 统计当前列的号码数量
            col_total += len(valid_phones) + len(invalid_phones)
            col_valid += len(valid_phones)
            col_invalid += len(invalid_phones)
            
            # 合并号码（去重）
            for phone in valid_phones:
                if phone and phone not in all_valid_phones[idx]:
                    all_valid_phones[idx].append(phone)
            for phone in invalid_phones:
                if phone and phone not in all_invalid_phones[idx]:
                    all_invalid_phones[idx].append(phone)
        
        stats['whatsapp_stats'][col] = {
            'total': col_total,
            'valid': col_valid,
            'invalid': col_invalid
        }
    
    # 找到最大号码数量，用于创建列
    max_valid_phones = max(len(phones) for phones in all_valid_phones) if all_valid_phones else 0
    max_invalid_phones = max(len(phones) for phones in all_invalid_phones) if all_invalid_phones else 0
    
    # 创建有效WhatsApp列（每个号码一列）
    for i in range(max_valid_phones):
        col_name = f"有效WhatsApp_{i+1}"
        result_df[col_name] = [phones[i] if i < len(phones) else '' for phones in all_valid_phones]
    
    # 创建无效WhatsApp列（每个号码一列）
    for i in range(max_invalid_phones):
        col_name = f"无效WhatsApp_{i+1}"
        result_df[col_name] = [phones[i] if i < len(phones) else '' for phones in all_invalid_phones]
    
    # 计算有效行数（至少有一个有效邮箱或WhatsApp）
    for idx in range(len(result_df)):
        has_valid = False
        # 检查有效邮箱
        if idx < len(all_valid_emails) and all_valid_emails[idx]:
            has_valid = True
        # 检查有效WhatsApp
        if not has_valid and idx < len(all_valid_phones) and all_valid_phones[idx]:
            has_valid = True
        
        if has_valid:
            stats['valid_rows'] += 1
        else:
            stats['invalid_rows'] += 1
    
    # 保存结果
    if progress_callback:
        progress_callback("正在保存结果...")
    
    output_ext = os.path.splitext(output_file)[1].lower()
    if output_ext in ['.xlsx', '.xls']:
        result_df.to_excel(output_file, index=False)
    elif output_ext == '.csv':
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    else:
        # 默认保存为Excel
        if not output_file.endswith('.xlsx'):
            output_file = output_file + '.xlsx'
        result_df.to_excel(output_file, index=False)
    
    if progress_callback:
        progress_callback(f"结果已保存到: {output_file}")
    
    return stats


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据清洗工具 - 验证邮箱和WhatsApp号码')
    parser.add_argument('input', help='输入文件路径（支持.xlsx, .xls, .csv）')
    parser.add_argument('-o', '--output', help='输出文件路径（默认：输入文件名_cleaned.xlsx）')
    parser.add_argument('--email-cols', nargs='+', help='邮箱列名（多个用空格分隔，不指定则自动检测）')
    parser.add_argument('--whatsapp-cols', nargs='+', help='WhatsApp列名（多个用空格分隔，不指定则自动检测）')
    parser.add_argument('--check-mx', action='store_true', help='检查邮箱MX记录')
    parser.add_argument('--check-smtp', action='store_true', help='进行SMTP验证（较慢）')
    parser.add_argument('--check-wa-online', action='store_true', help='在线验证WhatsApp（需要API）')
    
    args = parser.parse_args()
    
    input_file = args.input
    if not os.path.exists(input_file):
        print(f"❌ 错误：文件不存在: {input_file}")
        return
    
    output_file = args.output
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_cleaned.xlsx"
    
    def progress(msg):
        print(f"📊 {msg}")
    
    try:
        print("=" * 60)
        print("🚀 开始数据清洗...")
        print("=" * 60)
        
        stats = clean_data(
            input_file=input_file,
            output_file=output_file,
            email_columns=args.email_cols,
            whatsapp_columns=args.whatsapp_cols,
            check_email_mx=args.check_mx,
            check_email_smtp=args.check_smtp,
            check_whatsapp_online=args.check_wa_online,
            progress_callback=progress
        )
        
        print("\n" + "=" * 60)
        print("✅ 数据清洗完成！")
        print("=" * 60)
        print(f"📊 总行数: {stats['total_rows']}")
        print(f"✅ 有效行数: {stats['valid_rows']}")
        print(f"❌ 无效行数: {stats['invalid_rows']}")
        
        if stats['email_stats']:
            print("\n📧 邮箱验证统计:")
            for col, stat in stats['email_stats'].items():
                print(f"  {col}:")
                print(f"    总数: {stat['total']}")
                print(f"    有效: {stat['valid']}")
                print(f"    无效: {stat['invalid']}")
        
        if stats['whatsapp_stats']:
            print("\n📱 WhatsApp验证统计:")
            for col, stat in stats['whatsapp_stats'].items():
                print(f"  {col}:")
                print(f"    总数: {stat['total']}")
                print(f"    有效: {stat['valid']}")
                print(f"    无效: {stat['invalid']}")
        
        print(f"\n📁 结果文件: {output_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
