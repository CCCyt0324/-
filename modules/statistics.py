"""分类统计 —— 柱状图 + 占比明细表"""

from datetime import datetime

import streamlit as st
import plotly.express as px
import pandas as pd

from config import TYPE_EXPENSE, TYPE_INCOME
from database import get_monthly_stats


def run():
    st.title("📈 分类统计")

    today = datetime.now()

    c1, c2 = st.columns(2)
    with c1:
        month = st.selectbox(
            "月份",
            [f"{y}-{m:02d}" for y in range(2024, 2028) for m in range(1, 13)],
            index=(today.year - 2024) * 12 + today.month - 1,
        )
    with c2:
        record_type = st.selectbox(
            "类型", [TYPE_EXPENSE, TYPE_INCOME],
            format_func=lambda v: "💰 支出" if v == TYPE_EXPENSE else "💵 收入",
        )

    stats = get_monthly_stats(month, record_type)

    if not stats:
        type_text = "支出" if record_type == TYPE_EXPENSE else "收入"
        st.info(f"{month} 暂无{type_text}数据")
        return

    categories, amounts = zip(*stats)
    total = sum(amounts)

    # ===== 柱状图 =====
    st.subheader("📊 分类金额对比")
    fig = px.bar(
        x=list(categories), y=list(amounts),
        labels={"x": "分类", "y": "金额（元）"},
        color=list(categories),
        color_discrete_sequence=px.colors.qualitative.Set2,
        text_auto=".2f",
    )
    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=400)
    st.plotly_chart(fig, use_container_width=True)

    # ===== 明细表 =====
    st.subheader("📋 分类统计明细")
    df = pd.DataFrame({
        "分类": list(categories),
        "金额": [f"¥{a:,.2f}" for a in amounts],
        "占比": [f"{a / total * 100:.1f}%" for a in amounts],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("总计", f"¥{total:,.2f}")
