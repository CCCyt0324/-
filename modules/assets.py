"""资产管理 —— 账户列表 + 添加/编辑/删除 + 转账"""

import streamlit as st
import pandas as pd

from config import ACCOUNT_TYPES, TYPE_TRANSFER
from database import (
    get_all_accounts, get_account_by_id, create_account,
    update_account, delete_account, get_total_balance,
    get_balance_by_type, transfer,
)


def _account_type_display(atype):
    return ACCOUNT_TYPES.get(atype, atype)


def run():
    st.title("💰 资产管理")

    # ===== 总资产 + 分类小计 =====
    total = get_total_balance()
    by_type = get_balance_by_type()

    st.metric("💰 总资产", f"¥{total:,.2f}")

    if by_type:
        cols = st.columns(len(by_type))
        for (atype, bal), col in zip(by_type, cols):
            col.metric(_account_type_display(atype), f"¥{bal:,.2f}")

    st.divider()

    # ===== 账户列表表格 =====
    st.subheader("📋 账户列表")
    accounts = get_all_accounts()
    if accounts:
        df = pd.DataFrame([{
            "ID": a["id"],
            "名称": a["name"],
            "类型": _account_type_display(a["type"]),
            "余额": f"¥{a['balance']:,.2f}",
            "备注": a["note"] or "",
        } for a in accounts])
        event = st.dataframe(
            df, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row",
        )
        selected_idx = event.selection.rows[0] if event.selection.rows else None
    else:
        st.info("暂无账户")
        selected_idx = None

    # ===== 操作按钮行 =====
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("➕ 添加账户", use_container_width=True):
        _add_dialog()
    if c2.button("✏️ 编辑选中", use_container_width=True, disabled=selected_idx is None):
        _edit_dialog(accounts[selected_idx]["id"])
    if c3.button("🗑️ 删除选中", use_container_width=True, disabled=selected_idx is None):
        _delete_dialog(accounts[selected_idx]["id"])
    if c4.button("🔀 转账", use_container_width=True):
        _transfer_dialog()


# ===== 弹窗函数 =====

@st.dialog("➕ 添加账户")
def _add_dialog():
    name = st.text_input("账户名称", placeholder="例如：建行储蓄卡")
    atype = st.selectbox(
        "账户类型",
        list(ACCOUNT_TYPES.keys()),
        format_func=lambda k: ACCOUNT_TYPES[k],
    )
    balance = st.number_input("初始余额", min_value=0.0, value=0.0, step=100.0)
    note = st.text_input("备注（可选）")

    if st.button("✅ 确认添加", use_container_width=True):
        if not name.strip():
            st.error("账户名称不能为空")
        else:
            create_account(name.strip(), atype, balance, note.strip())
            st.success(f"已添加账户「{name}」")
            st.rerun()


@st.dialog("✏️ 编辑账户")
def _edit_dialog(account_id):
    acc = get_account_by_id(account_id)
    if not acc:
        st.error("账户不存在")
        return

    name = st.text_input("账户名称", value=acc["name"])
    keys = list(ACCOUNT_TYPES.keys())
    atype = st.selectbox(
        "账户类型", keys,
        index=keys.index(acc["type"]) if acc["type"] in keys else 0,
        format_func=lambda k: ACCOUNT_TYPES[k],
    )
    balance = st.number_input("余额", min_value=0.0, value=float(acc["balance"]), step=100.0)
    note = st.text_input("备注", value=acc["note"] or "")

    if st.button("💾 保存修改", use_container_width=True):
        update_account(account_id, name=name.strip(), type=atype, balance=balance, note=note.strip())
        st.success("已保存")
        st.rerun()


@st.dialog("🗑️ 确认删除")
def _delete_dialog(account_id):
    acc = get_account_by_id(account_id)
    if not acc:
        st.error("账户不存在")
        return
    st.write(f"确定删除账户「**{acc['name']}**」吗？")
    st.caption(f"类型：{_account_type_display(acc['type'])}　余额：¥{acc['balance']:,.2f}")
    if acc["balance"] > 0:
        st.warning("该账户余额不为 0，请先将余额转出或清零")
    else:
        if st.button("⚠️ 确认删除", type="primary", use_container_width=True):
            try:
                delete_account(account_id)
                st.success("已删除")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


@st.dialog("🔀 账户转账")
def _transfer_dialog():
    accounts = get_all_accounts()
    if len(accounts) < 2:
        st.error("至少需要 2 个账户才能转账")
        return

    opts = {f"{a['name']}（¥{a['balance']:,.2f}）": a["id"] for a in accounts}
    from_label = st.selectbox("转出账户", list(opts.keys()), key="from")
    to_label = st.selectbox("转入账户", list(opts.keys()), key="to")
    amount = st.number_input("转账金额", min_value=0.01, value=0.0, step=100.0)
    date = st.date_input("日期")
    note = st.text_input("备注（可选）")

    if opts[from_label] == opts[to_label]:
        st.error("转出和转入不能是同一个账户")
        return

    from_acc = next(a for a in accounts if a["id"] == opts[from_label])
    if amount > from_acc["balance"]:
        st.error(f"转出账户余额不足（当前余额 ¥{from_acc['balance']:,.2f}）")
        return

    if st.button("✅ 确认转账", use_container_width=True):
        transfer(opts[from_label], opts[to_label], amount, date.isoformat(), note.strip())
        st.success(f"转账 ¥{amount:,.2f} 成功")
        st.rerun()
