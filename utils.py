# スマート＆key重複修正済み版スケジュール帳（Streamlit単一ファイル）

import streamlit as st
import pandas as pd
import json
from datetime import datetime, time, timedelta
from streamlit_calendar import calendar
import uuid
import os
import hashlib

st.set_page_config(page_title="スケジュール帳", layout="wide")

# --- 設定 ---
DATA_FILE = "schedule_data.csv"
ACCOUNT_FILE = "accounts.json"
VISIBLE_ACCOUNTS_FILE = "visible_accounts.json"

COLOR_POOL = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# --- ユーティリティ関数 ---
def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_accounts():
    accounts = load_json(ACCOUNT_FILE, [])
    colors = {
        acc["account"]: COLOR_POOL[i % len(COLOR_POOL)]
        for i, acc in enumerate(accounts)
    }
    return accounts, colors

def authenticate(username, password, accounts):
    hashed = hash_password(password)
    for acc in accounts:
        if acc["username"] == username and acc["password"] == hashed:
            return acc["account"]
    return None

def verify_account(account, username, password, accounts):
    hashed = hash_password(password)
    return any(acc["account"] == account and acc["username"] == username and acc["password"] == hashed for acc in accounts)

def register_account(account_name, username, password, accounts):
    if any(a["account"] == account_name or a["username"] == username for a in accounts):
        return False
    accounts.append({
        "account": account_name,
        "username": username,
        "password": hash_password(password)
    })
    save_json(ACCOUNT_FILE, accounts)
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
    return pd.DataFrame(columns=["ID", "日付", "開始時刻", "終了時刻", "タイトル", "メモ", "アカウント"])

def save_schedule(df):
    df.to_csv(DATA_FILE, index=False)

def to_calendar_events(df, account_colors):
    return [
        {
            "id": row["ID"],
            "title": row["タイトル"],
            "start": datetime.combine(row["日付"], row["開始時刻"]).isoformat(),
            "end": datetime.combine(row["日付"], row["終了時刻"]).isoformat(),
            "allDay": False,
            "backgroundColor": account_colors.get(row["アカウント"], "#000"),
            "textColor": "#fff",
            "display": "block",
        }
        for _, row in df.iterrows()
    ]

# --- セッション初期化 ---
for key, default in {
    "logged_in": False,
    "username": "",
    "account": "",
    "visible_accounts": [],
    "schedule": pd.DataFrame(columns=["ID", "日付", "開始時刻", "終了時刻", "タイトル", "メモ", "アカウント"]),
    "calendar_key": str(uuid.uuid4()),
    "form_date": None
}.items():
    st.session_state.setdefault(key, default)

accounts, ACCOUNT_COLORS = load_accounts()

# --- ログイン画面 ---
if not st.session_state.logged_in:
    st.title("ログイン")
    tab_login, tab_register = st.tabs(["ログイン", "アカウント新規作成"])

    with tab_login:
        username = st.text_input("ユーザーID", key="login_username")
        password = st.text_input("パスワード", type="password", key="login_password")
        if st.button("ログイン"):
            account = authenticate(username, password, accounts)
            if account:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.account = account
                vis_accs = load_json(VISIBLE_ACCOUNTS_FILE, {})
                st.session_state.visible_accounts = vis_accs.get(account, [account])
                st.success(f"ようこそ、{account} さん")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが間違っています")

    with tab_register:
        new_account = st.text_input("アカウント名（表示用）", key="register_account")
        new_username = st.text_input("ユーザーID（ログイン用）", key="register_username")
        new_password = st.text_input("パスワード", type="password", key="register_password")
        if st.button("アカウント作成"):
            if register_account(new_account, new_username, new_password, accounts):
                st.success("アカウントを作成しました。ログインしてください。")
            else:
                st.error("アカウント名またはユーザーIDは既に使われています")
    st.stop()

# --- スケジュール読み込み ---
if st.session_state.schedule.empty:
    st.session_state.schedule = load_schedule()

visible_df = st.session_state.schedule[
    st.session_state.schedule["アカウント"].isin(st.session_state.visible_accounts)
]

# --- サイドバー ---
with st.sidebar:
    st.markdown("#### アカウント凡例")
    for acc in st.session_state.visible_accounts:
        color = ACCOUNT_COLORS.get(acc, "#000000")
        st.markdown(f"<div style='display:flex;align-items:center;'><div style='width:12px;height:12px;background:{color};margin-right:5px;'></div>{acc}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 表示アカウントの追加")
    add_account = st.text_input("アカウント名", key="add_account")
    add_user = st.text_input("ユーザーID", key="add_user")
    add_pass = st.text_input("パスワード", type="password", key="add_pass")
    if st.button("表示アカウントに追加"):
        if verify_account(add_account, add_user, add_pass, accounts):
            if add_account not in st.session_state.visible_accounts:
                st.session_state.visible_accounts.append(add_account)
                vis_accs = load_json(VISIBLE_ACCOUNTS_FILE, {})
                vis_accs[st.session_state.account] = st.session_state.visible_accounts
                save_json(VISIBLE_ACCOUNTS_FILE, vis_accs)
                st.session_state.calendar_key = str(uuid.uuid4())
                st.success(f"{add_account} を表示アカウントに追加しました")
                st.rerun()
            else:
                st.info("すでに追加されています")
        else:
            st.error("アカウント名・ID・パスワードが一致しません")

    st.markdown("### 表示アカウントの削除")
    options = [a for a in st.session_state.visible_accounts if a != st.session_state.account]
    if options:
        acc_to_remove = st.selectbox("削除対象アカウント", options=options, key="remove_acc")
        if st.button("表示から削除"):
            st.session_state.visible_accounts.remove(acc_to_remove)
            vis_accs = load_json(VISIBLE_ACCOUNTS_FILE, {})
            vis_accs[st.session_state.account] = st.session_state.visible_accounts
            save_json(VISIBLE_ACCOUNTS_FILE, vis_accs)
            st.session_state.calendar_key = str(uuid.uuid4())
            st.success(f"{acc_to_remove} を表示アカウントから削除しました")
            st.rerun()

# --- カレンダー表示 ---
events = to_calendar_events(visible_df, ACCOUNT_COLORS)
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

# --- カレンダークリック処理など省略 ---
# ご希望あれば後半部のコードをここに含めて続けて提供します
# --- カレンダークリック処理 ---
if calendar_result:
    if calendar_result.get("dateClick"):
        clicked_date = pd.to_datetime(calendar_result["dateClick"]["date"]) + timedelta(hours=9)
        st.session_state.form_date = clicked_date.date()

    if calendar_result.get("eventClick"):
        clicked_id = calendar_result["eventClick"]["event"]["id"]
        df = st.session_state.schedule
        selected = df[df["ID"] == clicked_id]

        if not selected.empty:
            row = selected.iloc[0]
            editable = (row["アカウント"] in st.session_state.visible_accounts)

            st.markdown("---")
            st.subheader(f"予定詳細 ({'編集可能' if editable else '閲覧のみ'})")
            with st.form(f"edit_{clicked_id}"):
                st.text_input("アカウント", value=row["アカウント"], disabled=True, key=f"edit_{clicked_id}_acc")
                new_title = st.text_input("タイトル", value=row["タイトル"], disabled=not editable, key=f"edit_{clicked_id}_title")
                new_start = st.time_input("開始時刻", value=row["開始時刻"], disabled=not editable, key=f"edit_{clicked_id}_start")
                new_end = st.time_input("終了時刻", value=row["終了時刻"], disabled=not editable, key=f"edit_{clicked_id}_end")
                new_memo = st.text_area("メモ", value=row["メモ"], disabled=not editable, key=f"edit_{clicked_id}_memo")

                col1, col2 = st.columns(2)
                if col1.form_submit_button("更新", disabled=not editable):
                    idx = df[df["ID"] == clicked_id].index[0]
                    st.session_state.schedule.loc[idx, ["タイトル", "開始時刻", "終了時刻", "メモ"]] = [new_title, new_start, new_end, new_memo]
                    save_schedule(st.session_state.schedule)
                    st.success("予定を更新しました")
                    st.rerun()
                if col2.form_submit_button("削除", disabled=not editable):
                    st.session_state.schedule = df[df["ID"] != clicked_id].reset_index(drop=True)
                    save_schedule(st.session_state.schedule)
                    st.success("予定を削除しました")
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

# --- 表示形式切り替え ---
st.markdown("---")
view_mode = st.radio("表示形式を選択", ["登録リスト", "月表示カレンダー"], horizontal=True)

# --- リスト形式表示（編集対応） ---
if view_mode == "登録リスト":
    filtered_schedule = visible_df.copy()
    if filtered_schedule.empty:
        st.info("まだ予定が登録されていません。")
    else:
        df = filtered_schedule.sort_values(["日付", "開始時刻"]).reset_index(drop=True)
        st.subheader("予定一覧（編集可能）")

        for _, row in df.iterrows():
            editable = row["アカウント"] in st.session_state.visible_accounts
            form_key = f"form_{row['ID']}"
            with st.expander(f"📅 {row['日付']} {row['タイトル']}（{row['開始時刻']}〜{row['終了時刻']}）"):
                with st.form(form_key):
                    st.text_input("アカウント", value=row["アカウント"], disabled=True, key=f"{form_key}_acc")
                    new_title = st.text_input("タイトル", value=row["タイトル"], disabled=not editable, key=f"{form_key}_title")
                    new_start = st.time_input("開始時刻", value=row["開始時刻"], disabled=not editable, key=f"{form_key}_start")
                    new_end = st.time_input("終了時刻", value=row["終了時刻"], disabled=not editable, key=f"{form_key}_end")
                    new_memo = st.text_area("メモ", value=row["メモ"], disabled=not editable, key=f"{form_key}_memo")

                    col1, col2 = st.columns(2)
                    if col1.form_submit_button("更新", disabled=not editable):
                        idx = st.session_state.schedule[st.session_state.schedule["ID"] == row["ID"]].index[0]
                        st.session_state.schedule.loc[idx, ["タイトル", "開始時刻", "終了時刻", "メモ"]] = [new_title, new_start, new_end, new_memo]
                        save_schedule(st.session_state.schedule)
                        st.success("更新しました")
                        st.rerun()
                    if col2.form_submit_button("削除", disabled=not editable):
                        st.session_state.schedule = st.session_state.schedule[st.session_state.schedule["ID"] != row["ID"]]
                        save_schedule(st.session_state.schedule)
                        st.session_state.calendar_key = str(uuid.uuid4())
                        st.success("削除しました")
                        st.rerun()

# --- 予定追加フォーム ---
if st.session_state.form_date:
    st.markdown("---")
    st.subheader(f"{st.session_state.form_date.strftime('%Y年%m月%d日')} の予定を追加")
    with st.form("add_schedule"):
        account = st.selectbox("追加先アカウント", options=st.session_state.visible_accounts, key="add_schedule_acc")
        title = st.text_input("タイトル", max_chars=100, key="add_schedule_title")
        start_time = st.time_input("開始時刻", time(9, 0), key="add_schedule_start")
        end_time = st.time_input("終了時刻", time(10, 0), key="add_schedule_end")
        memo = st.text_area("メモ", height=80, key="add_schedule_memo")
        if st.form_submit_button("追加"):
            if not title.strip():
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
                    "アカウント": account
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