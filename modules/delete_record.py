"""删除账目 —— 输入 ID → 显示信息 → 二次确认"""

import os

import streamlit as st

from database import get_record_by_id, delete_record
from config import TYPE_INCOME, TYPE_EXPENSE, TYPE_TRANSFER


def run():
    st.title("🗑️ 删除账目")

    record_id = st.number_input("请输入要删除的账目 ID", min_value=1, value=1, step=1)

    if st.button("🔍 查询账目", use_container_width=True):
        rec = get_record_by_id(record_id)

        if not rec:
            st.error(f"未找到 ID 为 {record_id} 的账目")
        else:
            st.divider()
            st.subheader("账目信息")

            type_text = {TYPE_INCOME: "💵 收入", TYPE_EXPENSE: "💰 支出", TYPE_TRANSFER: "🔀 转账"}.get(
                rec["type"], rec["type"])

            info_cols = st.columns(2)
            info_cols[0].write(f"**ID**：{rec['id']}")
            info_cols[0].write(f"**类型**：{type_text}")
            info_cols[0].write(f"**分类**：{rec['category']}")
            info_cols[1].write(f"**金额**：¥{rec['amount']:,.2f}")
            info_cols[1].write(f"**日期**：{rec['date']}")
            info_cols[1].write(f"**备注**：{rec['note'] or '无'}")

            # 显示图片
            if rec.get("image_path") and os.path.isfile(rec["image_path"]):
                st.image(rec["image_path"], width=400, caption="凭证图片")

            st.divider()

            if rec["type"] == TYPE_TRANSFER:
                st.warning("⚠️ 转账记录由系统自动管理，删除后账户余额不会回滚，请谨慎操作")

            if st.button("⚠️ 确认删除此账目", type="primary", use_container_width=True):
                delete_record(record_id)
                st.success(f"已删除 ID={record_id} 的账目")
                st.info("账户余额已自动回滚")
