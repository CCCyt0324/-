"""添加账目 —— 表单 + 图片上传 + 自动同步账户余额"""

from datetime import date

import streamlit as st

from config import (
    TYPE_EXPENSE, TYPE_INCOME,
    EXPENSE_CATEGORIES, INCOME_CATEGORIES,
    MIN_AMOUNT, MAX_AMOUNT, MAX_NOTE_LENGTH, MAX_IMAGE_SIZE,
)
from database import add_record, get_all_accounts
from utils.image_helper import save_image


def run():
    st.title("➕ 添加账目")

    # ---- 账户选择 ----
    accounts = get_all_accounts()
    if not accounts:
        st.warning("请先在「资产管理」页面添加账户")
        return

    # ---- 表单重置计数器：每次 "再添加一笔" 时 +1，
    #      所有控件 key 带上这个后缀，Streamlit 就会渲染全新控件 ----
    if "add_form_counter" not in st.session_state:
        st.session_state.add_form_counter = 0
    if "add_success" not in st.session_state:
        st.session_state.add_success = False

    suffix = st.session_state.add_form_counter

    # ===== 表单 =====
    with st.container(border=True):
        account_opts = {f"{a['name']}（¥{a['balance']:,.2f}）": a["id"] for a in accounts}
        account_label = st.selectbox(
            "账户", list(account_opts.keys()), key=f"add_account_{suffix}",
        )
        account_id = account_opts[account_label]

        c1, c2 = st.columns(2)
        record_type = c1.radio(
            "类型", [TYPE_EXPENSE, TYPE_INCOME],
            format_func=lambda v: "💰 支出" if v == TYPE_EXPENSE else "💵 收入",
            horizontal=True, key=f"add_type_{suffix}",
        )
        categories = EXPENSE_CATEGORIES if record_type == TYPE_EXPENSE else INCOME_CATEGORIES
        category = c2.selectbox("分类", categories, key=f"add_category_{suffix}")

        c3, c4 = st.columns(2)
        record_date = c3.date_input("日期", value=date.today(), key=f"add_date_{suffix}")
        amount = c4.number_input(
            "金额", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT,
            value=MIN_AMOUNT, step=1.0, format="%.2f", key=f"add_amount_{suffix}",
        )

        note = st.text_area(
            "备注（可选）", max_chars=MAX_NOTE_LENGTH,
            placeholder="例如：午餐外卖", key=f"add_note_{suffix}",
        )

        uploaded = st.file_uploader(
            "📎 凭证图片（可选，jpg/png，最大 5MB）",
            type=["jpg", "jpeg", "png"], key=f"add_image_{suffix}",
        )
        if uploaded is not None:
            st.caption(f"文件名：{uploaded.name}　大小：{uploaded.size / 1024:.0f} KB")

        # 提交按钮
        if st.button("✅ 添加账目", type="primary", use_container_width=True):
            errors = []
            if amount < MIN_AMOUNT:
                errors.append("金额必须大于 0")
            if len(note) > MAX_NOTE_LENGTH:
                errors.append(f"备注不能超过 {MAX_NOTE_LENGTH} 字")
            if uploaded is not None and uploaded.size > MAX_IMAGE_SIZE:
                errors.append("图片不能超过 5MB")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    img_path = save_image(uploaded) if uploaded else ""
                except ValueError as e:
                    st.error(str(e))
                    return

                add_record(
                    record_type=record_type,
                    amount=amount,
                    category=category,
                    account_id=account_id,
                    date=record_date.isoformat(),
                    note=note.strip(),
                    image_path=img_path,
                )
                st.session_state.add_success = True
                st.rerun()

    # ===== 成功提示 + "再添加一笔" =====
    if st.session_state.add_success:
        st.success("添加成功！")
        st.balloons()
        if st.button("📝 再添加一笔新账单", type="secondary", use_container_width=True):
            st.session_state.add_success = False
            st.session_state.add_form_counter += 1
            st.rerun()
