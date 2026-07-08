"""查看列表 —— 筛选 + 表格 + 图片缩略 + 行内编辑/删除 + CSV 导出"""

import io
import os
from datetime import datetime

import streamlit as st
import pandas as pd

from config import (
    TYPE_EXPENSE, TYPE_INCOME, TYPE_TRANSFER,
    EXPENSE_CATEGORIES, INCOME_CATEGORIES,
    MIN_AMOUNT, MAX_AMOUNT, MAX_NOTE_LENGTH,
)
from database import (
    query_records, get_record_by_id, update_record, delete_record, get_all_accounts,
)


def run():
    st.title("📋 账目列表")

    # ===== 筛选区 =====
    with st.container(border=True):
        st.caption("筛选条件")
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            month_opts = ["全部"] + sorted(set(
                f"{y}-{m:02d}" for y in range(2024, 2028) for m in range(1, 13)
            ), reverse=True)
            month_filter = st.selectbox("月份", month_opts)

        with c2:
            type_filter = st.selectbox(
                "类型", ["全部", TYPE_EXPENSE, TYPE_INCOME],
                format_func=lambda v: {"全部": "全部", TYPE_EXPENSE: "支出", TYPE_INCOME: "收入"}[v],
            )

        with c3:
            all_cats = list(dict.fromkeys(EXPENSE_CATEGORIES + INCOME_CATEGORIES))
            cat_filter = st.selectbox("分类", ["全部"] + all_cats)

        with c4:
            accounts = get_all_accounts()
            acct_opts = {a["name"]: a["id"] for a in accounts}
            acct_filter = st.selectbox("账户", ["全部"] + list(acct_opts.keys()))

        with c5:
            keyword = st.text_input("关键词", placeholder="搜备注")

    # ===== 排序 =====
    cs1, cs2 = st.columns([1, 1])
    with cs1:
        sort_by = st.selectbox("排序字段", ["date", "amount", "id"],
                               format_func=lambda v: {"date": "日期", "amount": "金额", "id": "ID"}[v])
    with cs2:
        sort_order = st.selectbox("排序方式", ["DESC", "ASC"],
                                  format_func=lambda v: "降序" if v == "DESC" else "升序")

    # ===== 查询 =====
    month_val = "" if month_filter == "全部" else month_filter
    type_val = "" if type_filter == "全部" else type_filter
    cat_val = "" if cat_filter == "全部" else cat_filter
    acct_val = "" if acct_filter == "全部" else str(acct_opts.get(acct_filter, ""))

    records = query_records(
        month=month_val, record_type=type_val, category=cat_val,
        account_id=acct_val, keyword=keyword,
        sort_by=sort_by, sort_order=sort_order,
    )

    # ===== 底部统计 =====
    if records:
        total_income = sum(r["amount"] for r in records if r["type"] == TYPE_INCOME)
        total_expense = sum(r["amount"] for r in records if r["type"] == TYPE_EXPENSE)

        ci, ce, cn = st.columns(3)
        ci.metric("收入合计", f"¥{total_income:,.2f}")
        ce.metric("支出合计", f"¥{total_expense:,.2f}")
        cn.metric("净额", f"¥{total_income - total_expense:,.2f}")

    st.divider()

    # ===== 表格 =====
    if not records:
        st.info("暂无匹配的账目记录")
        return

    # 构建账户 id→name 映射
    acct_name = {a["id"]: a["name"] for a in accounts}

    df = pd.DataFrame(records)
    df_display = df.assign(
        类型=df["type"].map({TYPE_INCOME: "收入", TYPE_EXPENSE: "支出", TYPE_TRANSFER: "转账"}),
        金额=df["amount"].apply(lambda x: f"¥{x:,.2f}"),
        账户=df["account_id"].map(lambda aid: acct_name.get(aid, str(aid))),
        图片=df["image_path"].apply(lambda p: "📎" if p else ""),
    ).rename(columns={
        "id": "ID", "category": "分类", "date": "日期", "note": "备注",
    })

    display_cols = ["ID", "日期", "类型", "分类", "账户", "金额", "图片", "备注"]

    event = st.dataframe(
        df_display[display_cols], use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
    )

    selected_rows = event.selection.rows if event.selection else []

    # ===== 图片预览 =====
    if selected_rows:
        record = records[selected_rows[0]]
        if record.get("image_path") and os.path.isfile(record["image_path"]):
            with st.expander("🖼️ 查看凭证图片", expanded=True):
                st.image(record["image_path"], width=400)

    # ===== 操作按钮 =====
    if selected_rows:
        record = records[selected_rows[0]]
        record_id = record["id"]

        col_edit, col_del, _ = st.columns([1, 1, 6])

        @st.dialog("✏️ 编辑账目")
        def _edit():
            rec = get_record_by_id(record_id)
            if not rec or rec["type"] == TYPE_TRANSFER:
                st.error("转账记录不可编辑")
                return

            c1, c2 = st.columns(2)
            new_type = c1.radio(
                "类型", [TYPE_EXPENSE, TYPE_INCOME],
                format_func=lambda v: "支出" if v == TYPE_EXPENSE else "收入",
                index=0 if rec["type"] == TYPE_EXPENSE else 1,
                horizontal=True,
            )
            cats = EXPENSE_CATEGORIES if new_type == TYPE_EXPENSE else INCOME_CATEGORIES
            cat_idx = cats.index(rec["category"]) if rec["category"] in cats else 0
            new_cat = c2.selectbox("分类", cats, index=cat_idx)

            # 账户
            acct_opts_label = {a["name"]: a["id"] for a in get_all_accounts()}
            cur_acct_name = next((n for n, aid in acct_opts_label.items() if aid == rec["account_id"]), list(acct_opts_label.keys())[0])
            new_acct_label = st.selectbox("账户", list(acct_opts_label.keys()),
                                          index=list(acct_opts_label.keys()).index(cur_acct_name)
                                          if cur_acct_name in acct_opts_label else 0)
            new_acct_id = acct_opts_label[new_acct_label]

            c3, c4 = st.columns(2)
            old_date = datetime.strptime(rec["date"], "%Y-%m-%d").date()
            new_date = c3.date_input("日期", value=old_date)
            new_amount = c4.number_input("金额", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT,
                                         value=float(rec["amount"]))
            new_note = st.text_area("备注", value=rec["note"] or "", max_chars=MAX_NOTE_LENGTH)

            if st.button("💾 保存修改", use_container_width=True):
                update_record(
                    record_id,
                    type=new_type, category=new_cat,
                    account_id=new_acct_id, date=new_date.isoformat(),
                    amount=new_amount, note=new_note.strip(),
                )
                st.success("修改已保存")
                st.rerun()

        @st.dialog("🗑️ 确认删除")
        def _delete():
            rec = get_record_by_id(record_id)
            if not rec:
                st.error("记录不存在")
                return
            items = {
                "ID": rec["id"], "类型": rec["type"], "分类": rec["category"],
                "金额": f"¥{rec['amount']:,.2f}", "日期": rec["date"], "备注": rec["note"],
            }
            for k, v in items.items():
                st.write(f"- {k}：{v}")
            if st.button("⚠️ 确认删除", type="primary", use_container_width=True):
                delete_record(record_id)
                st.success(f"已删除")
                st.rerun()

        if col_edit.button("✏️ 编辑"):
            _edit()
        if col_del.button("🗑️ 删除"):
            _delete()

    # ===== CSV 导出 =====
    st.divider()
    if st.button("📥 导出当前筛选结果为 CSV"):
        csv_df = df[["id", "type", "category", "date", "amount", "account_id", "note"]]
        csv_df.columns = ["ID", "类型", "分类", "日期", "金额", "账户ID", "备注"]
        buf = io.StringIO()
        csv_df.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="点击下载 CSV",
            data=buf.getvalue(),
            file_name=f"账目_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
