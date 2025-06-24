import streamlit as st
import pandas as pd
from datetime import date, datetime, time, timedelta
from streamlit_calendar import calendar
import uuid

st.set_page_config(page_title="スケジュール帳", layout="wide")

# --- 初期化 ---
if "schedule" not in st.session_state:
    st.session_state.schedule = pd.DataFrame(columns=["ID", "日付", "開始時刻", "終了時刻", "タイトル", "メモ"])

if "calendar_key" not in st.session_state:
    st.session_state.calendar_key = str(uuid.uuid4())

if "form_date" not in st.session_state:
    st.session_state.form_date = None

# --- カレンダーイベント整形 ---
def to_calendar_events(df):
    events = []
    for _, row in df.iterrows():
        start_dt = datetime.combine(row["日付"], row["開始時刻"])
        end_dt = datetime.combine(row["日付"], row["終了時刻"])
        events.append({
            "id": row["ID"],
            "title": row["タイトル"],
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "allDay": False
        })
    return events

# --- 表示切り替え（見出しなし） ---
view_mode = st.radio("ビュー形式", ["月表示カレンダー", "登録リスト"], horizontal=True, label_visibility="collapsed")

# --- カレンダー表示 ---
if view_mode == "月表示カレンダー":
    events = to_calendar_events(st.session_state.schedule)

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

    # 日付クリック → 予定追加
    if calendar_result and calendar_result.get("dateClick"):
        clicked_date_str = calendar_result["dateClick"]["date"]
        clicked_date = pd.to_datetime(clicked_date_str) + timedelta(hours=9)
        st.session_state.form_date = clicked_date.date()

    # 予定クリック → 編集・削除
    if calendar_result and calendar_result.get("eventClick"):
        clicked_id = calendar_result["eventClick"]["event"]["id"]
        df = st.session_state.schedule
        selected = df[df["ID"] == clicked_id]

        if not selected.empty:
            st.markdown("---")
            row = selected.iloc[0]

            with st.form("edit_schedule"):
                new_title = st.text_input("タイトル", row["タイトル"])
                new_start = st.time_input("開始時刻", row["開始時刻"])
                new_end = st.time_input("終了時刻", row["終了時刻"])
                new_memo = st.text_area("メモ", row["メモ"])
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("更新")
                with col2:
                    deleted = st.form_submit_button("削除")

                if submitted:
                    idx = df[df["ID"] == clicked_id].index[0]
                    st.session_state.schedule.at[idx, "タイトル"] = new_title
                    st.session_state.schedule.at[idx, "開始時刻"] = new_start
                    st.session_state.schedule.at[idx, "終了時刻"] = new_end
                    st.session_state.schedule.at[idx, "メモ"] = new_memo
                    st.success("予定を更新しました")
                    st.rerun()

                if deleted:
                    st.session_state.schedule = df[df["ID"] != clicked_id].reset_index(drop=True)
                    st.success("予定を削除しました")
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

# --- 予定リスト表示 ---
if view_mode == "登録リスト":
    if st.session_state.schedule.empty:
        st.info("まだ予定が登録されていません。")
    else:
        df = st.session_state.schedule.sort_values(["日付", "開始時刻"]).reset_index(drop=True)
        st.dataframe(df.drop("ID", axis=1), use_container_width=True)

# --- 新規予定フォーム ---
if st.session_state.form_date:
    st.markdown("---")
    st.subheader(f"{st.session_state.form_date.strftime('%Y年%m月%d日')} の予定を追加")
    with st.form("add_schedule"):
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
                    "メモ": memo.strip()
                }
                st.session_state.schedule = pd.concat(
                    [st.session_state.schedule, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.session_state.form_date = None
                st.session_state.calendar_key = str(uuid.uuid4())
                st.success("予定を追加しました")
                st.rerun()