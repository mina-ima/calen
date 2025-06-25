import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from streamlit_calendar import calendar
import uuid
import os
import hashlib

st.set_page_config(page_title="マルチユーザー対応スケジュール帳", layout="wide")

ACCOUNT_FILE = "accounts.csv"
DATA_FILE = "schedule_data.csv"

ACCOUNT_COLORS = {
    "個人": "#1f77b4",
    "会社": "#ff7f0e",
    "家族": "#2ca02c",
    "user4": "#d62728",
    "user5": "#9467bd",
}

# --- パスワードハッシュ ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- アカウント読み込み/保存 ---
def load_accounts():
    if os.path.exists(ACCOUNT_FILE):
        return pd.read_csv(ACCOUNT_FILE)
    else:
        return pd.DataFrame(columns=["アカウント名", "ユーザーID", "パスワードハッシュ"])

def save_accounts(df):
    df.to_csv(ACCOUNT_FILE, index=False)

# --- スケジュール読み込み/保存 ---
def load_schedule():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"]).dt.date
        df["開始時刻"] = pd.to_datetime(df["開始時刻"]).dt.time
        df["終了時刻"] = pd.to_datetime(df["終了時刻"]).dt.time

        # ← ここを追加（重要）
        if "アカウント名" not in df.columns:
            df["アカウント名"] = ""

        return df
    else:
        return pd.DataFrame(columns=["ID", "日付", "開始時刻", "終了時刻", "タイトル", "メモ", "アカウント名"])

def save_schedule(df):
    df.to_csv(DATA_FILE, index=False)

# --- 初期状態 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "known_accounts" not in st.session_state:
    st.session_state.known_accounts = []

# --- ログイン画面 ---
def login_screen():
    st.title("ログイン / アカウント登録")

    tabs = st.tabs(["ログイン", "新規登録"])

    with tabs[0]:
        id_input = st.text_input("ユーザーID")
        pw_input = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            df = load_accounts()
            user = df[(df["ユーザーID"] == id_input) & (df["パスワードハッシュ"] == hash_password(pw_input))]
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_id = id_input
                st.session_state.known_accounts = user["アカウント名"].iloc[0].split(";")
                st.success("ログイン成功")
                st.rerun()
            else:
                st.error("IDまたはパスワードが正しくありません")

    with tabs[1]:
        account_name = st.text_input("アカウント名")
        new_id = st.text_input("ユーザーID（登録）")
        new_pw = st.text_input("パスワード（登録）", type="password")
        if st.button("アカウント登録"):
            if account_name and new_id and new_pw:
                df = load_accounts()
                if new_id in df["ユーザーID"].values:
                    st.warning("このユーザーIDは既に存在します")
                else:
                    new_row = {
                        "アカウント名": account_name,
                        "ユーザーID": new_id,
                        "パスワードハッシュ": hash_password(new_pw)
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_accounts(df)
                    st.success("アカウントを登録しました。ログインしてください。")
            else:
                st.warning("すべての項目を入力してください")

# --- カレンダーイベント変換 ---
def to_calendar_events(df):
    events = []
    for _, row in df.iterrows():
        start_dt = datetime.combine(row["日付"], row["開始時刻"])
        end_dt = datetime.combine(row["日付"], row["終了時刻"])
        color = ACCOUNT_COLORS.get(row["アカウント名"], "#999999")
        events.append({
            "id": row["ID"],
            "title": row["タイトル"],
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "allDay": False,
            "backgroundColor": color,
            "textColor": "#ffffff",
            "display": "block"
        })
    return events

# --- ログイン済みの場合の画面 ---
def main_screen():
    st.sidebar.write(f"ログイン中：{st.session_state.user_id}")
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.known_accounts = []
        st.rerun()

    df = load_schedule()
    view_mode = st.radio("ビュー形式", ["カレンダー", "リスト"], horizontal=True, label_visibility="collapsed")

    st.markdown("### アカウント凡例")
    legend = ""
    for account, color in ACCOUNT_COLORS.items():
        legend += f'<span style="color:{color}; font-weight:bold; margin-right: 20px;">● {account}</span>'
    st.markdown(legend, unsafe_allow_html=True)

    if view_mode == "カレンダー":
        filtered = df[df["アカウント名"].isin(st.session_state.known_accounts)]
        events = to_calendar_events(filtered)
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
        )

        if calendar_result and calendar_result.get("dateClick"):
            clicked_date = pd.to_datetime(calendar_result["dateClick"]["date"]).date()
            with st.form("add_event"):
                st.markdown(f"#### {clicked_date.strftime('%Y-%m-%d')} の予定追加")
                account = st.selectbox("アカウント選択", st.session_state.known_accounts)
                title = st.text_input("タイトル")
                start_time = st.time_input("開始", time(9, 0))
                end_time = st.time_input("終了", time(10, 0))
                memo = st.text_area("メモ")
                if st.form_submit_button("追加"):
                    if title.strip() == "" or start_time >= end_time:
                        st.warning("タイトルが空、または時間設定が不正です")
                    else:
                        new_row = {
                            "ID": str(uuid.uuid4()),
                            "日付": clicked_date,
                            "開始時刻": start_time,
                            "終了時刻": end_time,
                            "タイトル": title,
                            "メモ": memo,
                            "アカウント名": account
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_schedule(df)
                        st.success("予定を追加しました")
                        st.rerun()

    elif view_mode == "リスト":
        filtered = df[df["アカウント名"].isin(st.session_state.known_accounts)]
        if filtered.empty:
            st.info("表示可能な予定がありません。")
        else:
            st.dataframe(filtered.drop("ID", axis=1).sort_values(["日付", "開始時刻"]), use_container_width=True)

# --- アプリ本体 ---
if not st.session_state.logged_in:
    login_screen()
else:
    main_screen()