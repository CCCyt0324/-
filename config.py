"""配置常量 —— 所有分类、路径、校验参数集中管理"""

import os

# ===== 路径 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "accounting.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# ===== 收支类型 =====
TYPE_EXPENSE = "expense"
TYPE_INCOME = "income"
TYPE_TRANSFER = "transfer"

# ===== 预设分类 =====
EXPENSE_CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "其他"]
INCOME_CATEGORIES = ["工资", "奖金", "理财", "其他"]

# ===== 账户类型 =====
ACCOUNT_TYPES = {
    "cash": "💵 现金",
    "bank": "🏦 银行卡",
    "alipay": "💚 支付宝",
    "wechat": "💬 微信",
    "other": "📦 其他",
}

# 首次运行自动创建的默认账户（名称, 类型key, 初始余额）
DEFAULT_ACCOUNTS = [
    ("现金", "cash", 0),
    ("支付宝", "alipay", 0),
    ("微信", "wechat", 0),
    ("银行卡", "bank", 0),
]

# ===== 数据校验 =====
MIN_AMOUNT = 0.01
MAX_AMOUNT = 999_999_999.99
MAX_NOTE_LENGTH = 200
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png"]
