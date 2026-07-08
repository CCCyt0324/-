"""首页概览 —— 总资产卡片 + 月收支 + 超支预警 + 饼图 + 最近流水"""

from datetime import datetime

import streamlit as st
import plotly.express as px

from config import TYPE_EXPENSE, TYPE_INCOME, EXPENSE_CATEGORIES
from database import (
    get_total_balance, get_monthly_summary, get_monthly_stats,
    get_recent_records, get_budget_progress,
)


def run():
    st.title("🏠 首页概览")

    today = datetime.now()
    month = today.strftime("%Y-%m")

    # ===== 总资产 =====
    total_balance = get_total_balance()
    c_total, _, _ = st.columns([1, 1, 1])
    c_total.metric("💰 总资产", f"¥{total_balance:,.2f}")

    st.divider()

    # ===== 本月三卡片 =====
    summary = get_monthly_summary(month)
    income = summary["income"]
    expense = summary["expense"]
    balance = income - expense

    c1, c2, c3 = st.columns(3)
    c1.metric("📈 本月收入", f"¥{income:,.2f}")
    c2.metric("📉 本月支出", f"¥{expense:,.2f}")
    c3.metric("📊 本月结余", f"¥{balance:,.2f}",
              delta=f"{'盈余' if balance >= 0 else '超支'} {abs(balance):,.2f}")

    # ===== 超支预警 =====
    progress_list = get_budget_progress(month)
    over_budget = [(cat, budget, spent, pct) for cat, budget, spent, pct in progress_list
                   if pct >= 100]
    if over_budget:
        st.divider()
        st.subheader("⚠️ 超支提醒")
        for cat, budget, spent, pct in over_budget:
            st.error(
                f"**{cat}**：预算 ¥{budget:,.0f}，已花 ¥{spent:,.0f}（{pct:.0f}%）"
            )

    st.divider()

    # ===== 支出分类饼图 =====
    st.subheader("📊 本月支出分类占比")
    stats = get_monthly_stats(month, TYPE_EXPENSE)
    if stats:
        labels, values = zip(*stats)
        fig = px.pie(
            names=labels, values=values, hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无本月支出数据，去添加一笔账目吧")

    st.divider()

    # ===== 最近 10 条流水 =====
    st.subheader("📋 最近 10 条流水")
    records = get_recent_records(10)
    if records:
        rows = []
        for r in records:
            rows.append({
                "ID": r["id"],
                "类型": "收入" if r["type"] == TYPE_INCOME else "支出",
                "分类": r["category"],
                "金额": f"¥{r['amount']:,.2f}",
                "日期": r["date"],
                "备注": r["note"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("还没有任何账目，去「添加账目」页面开始记账吧")
