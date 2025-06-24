
import streamlit as st
import pandas as pd
from datetime import date, datetime, time
from streamlit_calendar import calendar
from datetime import timedelta
import uuid

st.set_page_config(page_title="スケジュール帳（クリック追加）", layout="wide")
st.title("📅 スケジュール帳 - 時間付き予定")

# --- 初期化 ---
if "schedule" not in st.session_state:
    st.session_state.schedule = pd.DataFrame(columns=["日付", "開始時刻", "終了時刻", "タイトル", "メモ"])

if "calendar_key" not in st.session_state:
    st.session_state.calendar_key = str(uuid.uuid4())

if "form_date" not in st.session_state:
    st.session_state.form_date = None  # ← フォームを表示する日付（None なら非表示）

# --- カレンダーイベント整形 ---
def to_calendar_events(df):
    events = []
    for _, row in df.iterrows():
        start_dt = datetime.combine(row["日付"], row["開始時刻"])
        end_dt = datetime.combine(row["日付"], row["終了時刻"])
        events.append({
            "title": row["タイトル"],
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "allDay": False
        })
    return events

# --- 表示切り替え ---
st.subheader("📌 表示形式を選択")
view_mode = st.radio("ビュー形式", ["📅 月表示カレンダー", "📋 登録リスト"], horizontal=True)

# --- カレンダー表示 ---
if view_mode == "📅 月表示カレンダー":
    st.markdown("### 📆 月間予定カレンダー")
    events = to_calendar_events(st.session_state.schedule)

    calendar_result = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "ja",
            "selectable": True,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listWeek"
            },
        },
        key=st.session_state.calendar_key
    )

    # 日付クリック時の補正処理
    if calendar_result and calendar_result.get("dateClick"):
        clicked_date_str = calendar_result["dateClick"]["date"]
        clicked_date = pd.to_datetime(clicked_date_str) + timedelta(hours=9)  # ← 重要
        st.session_state.form_date = clicked_date.date()

# --- 予定一覧表示 ---
if view_mode == "📋 登録リスト":
    st.markdown("### 📖 登録された予定リスト")
    if st.session_state.schedule.empty:
        st.info("まだ予定が登録されていません。")
    else:
        df = st.session_state.schedule.sort_values(["日付", "開始時刻"]).reset_index(drop=True)
        st.dataframe(df, use_container_width=True)

# --- 予定追加フォーム（クリック時のみ表示） ---
if st.session_state.form_date:
    st.markdown("---")
    st.subheader(f"📝 {st.session_state.form_date.strftime('%Y年%m月%d日')} の予定を追加")
    with st.form("add_schedule"):
        title = st.text_input("タイトル", max_chars=100)
        start_time = st.time_input("開始時刻", value=time(9, 0))
        end_time = st.time_input("終了時刻", value=time(10, 0))
        memo = st.text_area("メモ", height=100)
        submitted = st.form_submit_button("追加")

        if submitted:  # ← この if をフォーム内に移動
            if title.strip() == "":
                st.warning("⚠️ タイトルは必須です")
            elif start_time >= end_time:
                st.warning("⚠️ 開始時刻は終了時刻より前にしてください")
            else:
                new_row = {
                    "日付": st.session_state.form_date,
                    "開始時刻": start_time,
                    "終了時刻": end_time,
                    "タイトル": title.strip(),
                    "メモ": memo.strip()
                }
                st.session_state.schedule = pd.concat(
                    [st.session_state.schedule, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.session_state.form_date = None
                st.session_state.calendar_key = str(uuid.uuid4())

                st.rerun()