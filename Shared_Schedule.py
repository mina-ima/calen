import streamlit as st
import pandas as pd
import json
from datetime import datetime, time, timedelta
from streamlit_calendar import calendar
import uuid
import os

st.set_page_config(page_title="スケジュール帳", layout="wide")

DATA_FILE = "schedule_data.csv"
ACCOUNT_FILE = "accounts.json"
VISIBLE_ACCOUNTS_FILE = "visible_accounts.json"

COLOR_POOL = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]
ACCOUNT_COLORS = {}

def load_accounts():
    global ACCOUNT_COLORS
    if os.path.exists(ACCOUNT_FILE):
        with open(ACCOUNT_FILE, 'r') as f:
            accounts = json.load(f)
        assigned_colors = {}
        for i, acc in enumerate(accounts):
            assigned_colors[acc['account']] = COLOR_POOL[i % len(COLOR_POOL)]
        ACCOUNT_COLORS = assigned_colors
        return accounts
    return []

def save_accounts(accounts):
    with open(ACCOUNT_FILE, 'w') as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

def load_visible_accounts():
    if os.path.exists(VISIBLE_ACCOUNTS_FILE):
        with open(VISIBLE_ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_visible_accounts(data):
    with open(VISIBLE_ACCOUNTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def authenticate(username, password):
    accounts = load_accounts()
    for acc in accounts:
        if acc['username'] == username and acc['password'] == password:
            return acc['account']
    return None

def verify_account(account, username, password):
    accounts = load_accounts()
    for acc in accounts:
        if acc['account'] == account and acc['username'] == username and acc['password'] == password:
            return True
    return False

def register_account(new_account, new_username, new_password):
    accounts = load_accounts()
    for acc in accounts:
        if acc['account'] == new_account or acc['username'] == new_username:
            return False
    accounts.append({"account": new_account, "username": new_username, "password": new_password})
    save_accounts(accounts)
    load_accounts()
    return True

def load_schedule():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"]).dt.date
        df["開始時刻"] = pd.to_datetime(df["開始時刻"]).dt.time
        df["終了時刻"] = pd.to_datetime(df["終了時刻"]).dt.time
        if "アカウント" not in df.columns:
            df["アカウント"] = "default"
        return df
    else:
        return pd.DataFrame(columns=["ID", "日付", "開始時刻", "終了時刻", "タイトル", "メモ", "アカウント"])

def save_schedule(df):
    df.to_csv(DATA_FILE, index=False)

def to_calendar_events(df):
    events = []
    for _, row in df.iterrows():
        start_dt = datetime.combine(row["日付"], row["開始時刻"])
        end_dt = datetime.combine(row["日付"], row["終了時刻"])
        color = ACCOUNT_COLORS.get(row["アカウント"], "#000000")
        events.append({
            "id": row["ID"],
            "title": row["タイトル"],
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "allDay": False,
            "backgroundColor": color,
            "textColor": "#ffffff",
            "display": "block",
        })
    return events

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.account = ""
    st.session_state.visible_accounts = []

accounts_data = load_accounts()

if not st.session_state.logged_in:
    st.title("ログイン")
    tab_login, tab_register = st.tabs(["ログイン", "アカウント新規作成"])

    with tab_login:
        username = st.text_input("ユーザーID")
        password = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            account = authenticate(username, password)
            if account:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.account = account
                vis_accs = load_visible_accounts()
                st.session_state.visible_accounts = vis_accs.get(account, [account])
                st.success(f"ようこそ、{account} さん")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが間違っています")

    with tab_register:
        new_account = st.text_input("アカウント名（表示用）")
        new_username = st.text_input("ユーザーID（ログイン用）")
        new_password = st.text_input("パスワード（ログイン用）", type="password")
        if st.button("アカウント作成"):
            if register_account(new_account, new_username, new_password):
                st.success("アカウントを作成しました。ログインしてください。")
            else:
                st.error("そのアカウント名またはユーザーIDは既に使われています。")
    st.stop()

if "schedule" not in st.session_state:
    st.session_state.schedule = load_schedule()
if "calendar_key" not in st.session_state:
    st.session_state.calendar_key = str(uuid.uuid4())
if "form_date" not in st.session_state:
    st.session_state.form_date = None

with st.sidebar:
    st.markdown("### 表示アカウントの追加")
    add_account = st.text_input("アカウント名")
    add_user = st.text_input("ユーザーID", key="add_user")
    add_pass = st.text_input("パスワード", type="password", key="add_pass")
    if st.button("表示アカウントに追加"):
        if verify_account(add_account, add_user, add_pass):
            if add_account not in st.session_state.visible_accounts:
                st.session_state.visible_accounts.append(add_account)
                vis_accs = load_visible_accounts()
                vis_accs[st.session_state.account] = st.session_state.visible_accounts
                save_visible_accounts(vis_accs)
                st.session_state.calendar_key = str(uuid.uuid4())  # ✅ 修正：再描画トリガー
                st.success(f"{add_account} を表示アカウントに追加しました")
                st.rerun()
            else:
                st.info("すでに追加されています")
        else:
            st.error("アカウント名・ID・パスワードが一致しません")
    
    st.markdown("### 表示アカウントの削除")
    acc_to_remove = st.selectbox("削除対象アカウント", options=[a for a in st.session_state.visible_accounts if a != st.session_state.account])
    if st.button("表示から削除"):
        if acc_to_remove in st.session_state.visible_accounts:
            st.session_state.visible_accounts.remove(acc_to_remove)
            vis_accs = load_visible_accounts()
            vis_accs[st.session_state.account] = st.session_state.visible_accounts
            save_visible_accounts(vis_accs)
            st.session_state.calendar_key = str(uuid.uuid4())  # ✅ 修正：再描画トリガー
            st.success(f"{acc_to_remove} を表示アカウントから削除しました")
            st.rerun()

    st.markdown("---")
    st.markdown("#### アカウント凡例")
    for acc in st.session_state.visible_accounts:
        color = ACCOUNT_COLORS.get(acc, "#000000")
        st.markdown(f"<div style='display:flex;align-items:center;'><div style='width:12px;height:12px;background:{color};margin-right:5px;'></div>{acc}</div>", unsafe_allow_html=True)

view_mode = st.radio("ビュー形式", ["月表示カレンダー", "登録リスト"], horizontal=True, label_visibility="collapsed")
filtered_schedule = st.session_state.schedule[st.session_state.schedule["アカウント"].isin(st.session_state.visible_accounts)]

if view_mode == "月表示カレンダー":
    events = to_calendar_events(filtered_schedule)
    calendar_result = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "ja",
            "selectable": True,
            "editable": False,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listWeek"
            },
        },
        key=st.session_state.calendar_key
    )

    if calendar_result and calendar_result.get("dateClick"):
        clicked_date = pd.to_datetime(calendar_result["dateClick"]["date"]) + timedelta(hours=9)
        st.session_state.form_date = clicked_date.date()

    if calendar_result and calendar_result.get("eventClick"):
        clicked_id = calendar_result["eventClick"]["event"]["id"]
        df = st.session_state.schedule
        selected = df[df["ID"] == clicked_id]

        if not selected.empty:
            row = selected.iloc[0]
            editable = (row["アカウント"] in st.session_state.visible_accounts)

            st.markdown("---")
            st.subheader(f"予定詳細 ({'編集可能' if editable else '閲覧のみ'})")
            with st.form("edit_schedule"):
                st.text_input("アカウント", value=row["アカウント"], disabled=True)
                new_title = st.text_input("タイトル", value=row["タイトル"], disabled=not editable)
                new_start = st.time_input("開始時刻", value=row["開始時刻"], disabled=not editable)
                new_end = st.time_input("終了時刻", value=row["終了時刻"], disabled=not editable)
                new_memo = st.text_area("メモ", value=row["メモ"], disabled=not editable)
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("更新", disabled=not editable)
                with col2:
                    deleted = st.form_submit_button("削除", disabled=not editable)

                if submitted:
                    idx = df[df["ID"] == clicked_id].index[0]
                    st.session_state.schedule.at[idx, "タイトル"] = new_title
                    st.session_state.schedule.at[idx, "開始時刻"] = new_start
                    st.session_state.schedule.at[idx, "終了時刻"] = new_end
                    st.session_state.schedule.at[idx, "メモ"] = new_memo
                    save_schedule(st.session_state.schedule)
                    st.success("予定を更新しました")
                    st.rerun()
                if deleted:
                    st.session_state.schedule = df[df["ID"] != clicked_id].reset_index(drop=True)
                    save_schedule(st.session_state.schedule)
                    st.success("予定を削除しました")
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

if view_mode == "登録リスト":
    if filtered_schedule.empty:
        st.info("まだ予定が登録されていません。")
    else:
        df = filtered_schedule.sort_values(["日付", "開始時刻"]).reset_index(drop=True)
        st.dataframe(df.drop("ID", axis=1), use_container_width=True)

if st.session_state.form_date:
    st.markdown("---")
    st.subheader(f"{st.session_state.form_date.strftime('%Y年%m月%d日')} の予定を追加")
    with st.form("add_schedule"):
        new_account = st.selectbox("追加するアカウント", options=st.session_state.visible_accounts)
        title = st.text_input("タイトル", max_chars=100)
        start_time = st.time_input("開始時刻", value=time(9, 0))
        end_time = st.time_input("終了時刻", value=time(10, 0))
        memo = st.text_area("メモ", height=100)
        submitted = st.form_submit_button("追加")

        if submitted:
            if title.strip() == "":
                st.warning("タイトルは必須です")
            elif start_time >= end_time:
                st.warning("開始時刻は終了時刻より前にしてください")
            else:
                new_row = {
                    "ID": str(uuid.uuid4()),
                    "日付": st.session_state.form_date,
                    "開始時刻": start_time,
                    "終了時刻": end_time,
                    "タイトル": title.strip(),
                    "メモ": memo.strip(),
                    "アカウント": new_account
                }
                st.session_state.schedule = pd.concat(
                    [st.session_state.schedule, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                save_schedule(st.session_state.schedule)
                st.session_state.form_date = None
                st.session_state.calendar_key = str(uuid.uuid4())
                st.success("予定を追加しました")
                st.rerun()