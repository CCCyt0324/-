"""个人记账工具 v2 —— 主入口"""

import os
import streamlit as st

from database import init_db
from config import UPLOAD_DIR

# ===== 全局初始化 =====
os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

# ===== 页面配置（必须是第一个 st 调用） =====
st.set_page_config(
    page_title="个人记账本",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== 侧边栏 =====
st.sidebar.title("💰 个人记账本")
st.sidebar.divider()

MENU_ITEMS = [
    "🏠 首页概览",
    "💰 资产管理",
    "➕ 添加账目",
    "📋 账目列表",
    "📅 日历报表",
    "📈 分类统计",
    "🎯 预算分析",
    "🗑️ 删除账目",
]

menu = st.sidebar.radio(
    "导航",
    MENU_ITEMS,
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("数据库：accounting.db")
st.sidebar.caption(f"图片目录：{UPLOAD_DIR}")

# ===== 路由分发 =====
from modules import (
    dashboard, assets, add_record, view_records,
    calendar_view, statistics, budget, delete_record,
)

page_map = {
    "🏠 首页概览": dashboard,
    "💰 资产管理": assets,
    "➕ 添加账目": add_record,
    "📋 账目列表": view_records,
    "📅 日历报表": calendar_view,
    "📈 分类统计": statistics,
    "🎯 预算分析": budget,
    "🗑️ 删除账目": delete_record,
}

page_map[menu].run()
