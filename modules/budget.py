"""预算分析 —— 进度条 + 设置预算 + 复制上月"""

from datetime import datetime

import streamlit as st
import pandas as pd

from config import EXPENSE_CATEGORIES
from database import get_budget_progress, set_budget, get_budgets, copy_budget


def _bar_color(pct):
    """根据百分比返回颜色"""
    if pct >= 100:
        return "#d32f2f"  # 红色：超支
    elif pct >= 80:
        return "#ff9800"  # 橙色：接近预算
    else:
        return "#4caf50"  # 绿色：安全


def run():
    st.title("🎯 预算分析")

    today = datetime.now()

    # 月份选择
    c1, c2, c3 = st.columns([1, 1, 2])
    month = c1.selectbox(
        "月份",
        [f"{y}-{m:02d}" for y in range(2024, 2028) for m in range(1, 13)],
        index=(today.year - 2024) * 12 + today.month - 1,
        key="budget_month",
    )

    # ===== 预算进度 =====
    progress_list = get_budget_progress(month)

    if progress_list:
        st.subheader("📊 预算执行进度")

        # 总计条
        total_budget = sum(b for _, b, _, _ in progress_list)
        total_spent = sum(s for _, _, s, _ in progress_list)
        total_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0

        st.write(f"**总预算**：¥{total_budget:,.0f}　｜　**已支出**：¥{total_spent:,.0f}　｜　**剩余**：¥{max(total_budget - total_spent, 0):,.0f}")
        st.progress(min(total_pct / 100, 1.0), text=f"总进度 {total_pct:.1f}%")

        st.divider()

        # 各分类进度条
        for cat, budget, spent, pct in sorted(progress_list, key=lambda x: x[3], reverse=True):
            color = _bar_color(pct)
            label = f"{'🔴' if pct >= 100 else '🟡' if pct >= 80 else '🟢'} **{cat}**"
            remain = f"剩余 ¥{max(budget - spent, 0):,.0f}" if budget > spent else "已超支！"
            st.write(f"{label}　预算 ¥{budget:,.0f}　已花 ¥{spent:,.0f}　{remain}")

            # 用 markdown 的 html 实现彩色进度条
            bar_width = min(pct, 100) if pct <= 120 else 100
            over_width = max(pct - 100, 0) if pct > 100 else 0
            html = f"""
            <div style="background:#e0e0e0;border-radius:4px;height:18px;overflow:hidden;margin:4px 0 12px 0;">
              <div style="background:{color};width:{bar_width}%;height:100%;float:left;"></div>
            </div>
            <div style="font-size:12px;color:#666;">{pct:.1f}%</div>
            """
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("本月尚未设置预算，请在下方设置")

    st.divider()

    # ===== 设置预算 =====
    st.subheader("⚙️ 设置预算")
    st.caption(f"为 {month} 设置各分类的月度预算")

    existing = get_budgets(month)

    cats = EXPENSE_CATEGORIES
    cols = st.columns(3)
    new_budgets = {}
    for i, cat in enumerate(cats):
        default_val = existing.get(cat, 0.0)
        new_budgets[cat] = cols[i % 3].number_input(
            f"{cat}", min_value=0.0, value=float(default_val), step=100.0,
            key=f"budget_{cat}",
        )

    cb1, cb2 = st.columns([1, 3])
    if cb1.button("💾 保存预算", type="primary", use_container_width=True):
        for cat, val in new_budgets.items():
            set_budget(month, cat, val)
        st.success("预算已保存")
        st.rerun()

    # 一键复制上月
    prev_month = f"{today.year}-{today.month - 1:02d}" if today.month > 1 else f"{today.year - 1}-12"
    if cb2.button(f"📋 从 {prev_month} 复制预算", use_container_width=True):
        n = copy_budget(prev_month, month)
        if n > 0:
            st.success(f"已从 {prev_month} 复制 {n} 个分类预算")
        else:
            st.warning(f"{prev_month} 没有预算数据")
        st.rerun()
