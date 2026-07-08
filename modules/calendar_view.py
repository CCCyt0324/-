"""日历报表 —— 真实日历布局 + 支出热力色 + 点击日期查看明细"""

import calendar
import os
from datetime import datetime

import streamlit as st
import pandas as pd

from config import TYPE_INCOME, TYPE_EXPENSE
from database import get_daily_stats, get_records_by_date, get_all_accounts


def _amount_bg(amount, max_amount):
    """根据金额返回背景色 —— 5 档"""
    if max_amount == 0 or amount <= 0:
        return "#f2f2f2"
    ratio = min(amount / max_amount, 1.0)
    if ratio < 0.2:
        return "#e8f5e9"
    elif ratio < 0.4:
        return "#fff9c4"
    elif ratio < 0.7:
        return "#ffcc80"
    elif ratio < 0.9:
        return "#ef6c00"
    else:
        return "#c62828"


def run():
    st.title("📅 日历报表")

    today = datetime.now()

    # ---- 选中状态 ----
    if "cal_day" not in st.session_state:
        st.session_state.cal_day = None
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = ""

    # ---- 月份选择 ----
    all_months = [f"{y}-{m:02d}" for y in range(2024, 2028) for m in range(1, 13)]
    default_idx = (today.year - 2024) * 12 + today.month - 1
    month_str = st.selectbox("月份", all_months, index=default_idx, key="cal_month_sel")
    year, month = int(month_str[:4]), int(month_str[5:7])

    month_names = [
        "", "一月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月",
    ]

    # ---- 日历 ----
    st.subheader("📆 支出日历")
    st.caption(f"### {year}年 {month_names[month]}")

    daily_data = get_daily_stats(month_str)
    max_val = max(daily_data.values()) if daily_data else 0

    cal = calendar.monthcalendar(year, month)
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]

    # ---- 表头 ----
    hcols = st.columns(7, gap="small")
    for i, wd in enumerate(weekdays):
        c = "#e57373" if wd in ("六", "日") else "#666"
        hcols[i].markdown(
            f"<p style='text-align:center;color:{c};font-weight:600;"
            f"font-size:13px;margin:0;padding:4px 0;'>{wd}</p>",
            unsafe_allow_html=True,
        )

    # ---- 日期按钮网格 ----
    for week in cal:
        cols = st.columns(7, gap="small")
        for i, day in enumerate(week):
            cell = cols[i].container(border=False)
            if day == 0:
                continue  # 空白格

            amount = daily_data.get(day, 0)
            bg = _amount_bg(amount, max_val)
            tc = "#fff" if amount > 0 and max_val > 0 and amount / max_val >= 0.9 else "#333"

            is_today = (year, month, day) == (today.year, today.month, today.day)
            is_selected = (
                day == st.session_state.cal_day
                and month_str == st.session_state.cal_month
            )

            # 标签：日期 + 金额
            if amount > 0:
                label = f"{day}\n¥{amount:.0f}"
            else:
                label = str(day)

            # 按钮样式前缀
            prefix = ""
            if is_selected:
                prefix = "● "
            elif is_today:
                prefix = "◉ "

            btn_key = f"calbtn_{year}_{month:02d}_{day}"

            # 用 colored button 表情间接表达，用 st.button type 表达状态
            if is_selected:
                btn_type = "primary"
            elif is_today:
                btn_type = "secondary"
            else:
                btn_type = "tertiary"

            if cell.button(prefix + label, key=btn_key, type=btn_type, use_container_width=True):
                if is_selected:
                    st.session_state.cal_day = None
                    st.session_state.cal_month = ""
                else:
                    st.session_state.cal_day = day
                    st.session_state.cal_month = month_str
                st.rerun()

    # ---- 图例 ----
    st.divider()
    lc = st.columns(8)
    items = [
        ("🟢 低", "#e8f5e9"), ("🟡", "#fff9c4"), ("🟠 中", "#ffcc80"),
        ("🟤", "#ef6c00"), ("🔴 高", "#c62828"),
        ("", ""), ("◉ 今日", ""), ("● 已选", ""),
    ]
    for col, (label, _) in zip(lc, items):
        if label:
            col.caption(label)

    # ---- 清除选中 ----
    selected_day = st.session_state.cal_day
    selected_month = st.session_state.cal_month

    if selected_day and selected_month == month_str:
        c1, c2 = st.columns([1, 5])
        c1.caption(f"当前选中：**{month_str}-{selected_day:02d}**")
        if c2.button("✕ 清除选中"):
            st.session_state.cal_day = None
            st.session_state.cal_month = ""
            st.rerun()

    st.divider()

    # ---- 当日明细 ----
    if selected_day and selected_month == month_str:
        date_str = f"{month_str}-{selected_day:02d}"
        st.subheader(f"📋 {date_str} 明细")

        records = get_records_by_date(date_str)
        if records:
            day_income = sum(r["amount"] for r in records if r["type"] == TYPE_INCOME)
            day_expense = sum(r["amount"] for r in records if r["type"] == TYPE_EXPENSE)

            ci, ce = st.columns(2)
            ci.metric("当日收入", f"¥{day_income:,.2f}")
            ce.metric("当日支出", f"¥{day_expense:,.2f}")

            acct_name = {a["id"]: a["name"] for a in get_all_accounts()}
            rows = []
            for r in records:
                rows.append({
                    "ID": r["id"],
                    "类型": "收入" if r["type"] == TYPE_INCOME else "支出",
                    "分类": r["category"],
                    "账户": acct_name.get(r["account_id"], ""),
                    "金额": f"¥{r['amount']:,.2f}",
                    "备注": r["note"],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            for r in records:
                if r.get("image_path") and os.path.isfile(r["image_path"]):
                    with st.expander(f"🖼️ ID{r['id']} 凭证图片"):
                        st.image(r["image_path"], width=400)
        else:
            st.info(f"{date_str} 暂无账目记录")
    else:
        st.info("👆 点击日历中的日期，下方会显示当日明细")
