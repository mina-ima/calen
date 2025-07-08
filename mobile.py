import streamlit as st
import pandas as pd
import json
from datetime import datetime, time, timedelta
from streamlit_calendar import calendar
import uuid
import os
import hashlib
from streamlit.components.v1 import html

# ─── ページ設定 ───
st.set_page_config(
    page_title="スケジュール帳",
    layout="wide",
    initial_sidebar_state="expanded"   # PC／モバイルともにサイドバーを展開
)

# ─── 定数 ───
DATA_FILE               = "schedule_data.csv"
ACCOUNT_FILE            = "accounts.json"
VISIBLE_ACCOUNTS_FILE   = "visible_accounts.json"
UPLOAD_DIR              = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

COLOR_POOL = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

# ─── ユーティリティ ───
def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_accounts():
    accounts = load_json(ACCOUNT_FILE, [])
    colors = {acc["account"]: COLOR_POOL[i % len(COLOR_POOL)]
              for i, acc in enumerate(accounts)}
    return accounts, colors

def authenticate(username, password, accounts):
    h = hash_password(password)
    for acc in accounts:
        if acc["username"] == username and acc["password"] == h:
            return acc["account"]
    return None

def verify_account(account, username, password, accounts):
    h = hash_password(password)
    return any(
        acc["account"] == account and
        acc["username"] == username and
        acc["password"] == h
        for acc in accounts
    )

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
        df["日付"]      = pd.to_datetime(df["日付"]).dt.date
        df["開始時刻"]  = pd.to_datetime(df["開始時刻"]).dt.time
        df["終了時刻"]  = pd.to_datetime(df["終了時刻"]).dt.time
        if "アカウント" not in df.columns:
            df["アカウント"] = "default"
        if "ファイルパス" not in df.columns:
            df["ファイルパス"] = ""
        return df
    return pd.DataFrame(columns=[
        "ID","日付","開始時刻","終了時刻",
        "タイトル","メモ","アカウント","ファイルパス"
    ])

def save_schedule(df):
    df.to_csv(DATA_FILE, index=False)

def to_calendar_events(df, colors):
    return [
        {
            "id": row["ID"],
            "title": row["タイトル"],
            "start": datetime.combine(row["日付"], row["開始時刻"]).isoformat(),
            "end":   datetime.combine(row["日付"], row["終了時刻"]).isoformat(),
            "allDay": False,
            "backgroundColor": colors.get(row["アカウント"], "#000"),
            "textColor": "#fff",
            "display": "block",
        }
        for _, row in df.iterrows()
    ]

# ─── セッション初期化 ───
for key, default in {
    "logged_in": False,
    "username": "",
    "account": "",
    "visible_accounts": [],
    "schedule": pd.DataFrame(),
    "calendar_key": str(uuid.uuid4()),
    "form_date": None,
    "eventClick": None
}.items():
    st.session_state.setdefault(key, default)

accounts, ACCOUNT_COLORS = load_accounts()

# ─── ログイン画面 ───
if not st.session_state.logged_in:
    st.title("ログイン")
    tab1, tab2 = st.tabs(["ログイン", "アカウント新規作成"])
    with tab1:
        user = st.text_input("ユーザーID", key="login_user")
        pwd  = st.text_input("パスワード", type="password", key="login_pwd")
        if st.button("ログイン"):
            acc = authenticate(user, pwd, accounts)
            if acc:
                st.session_state.logged_in = True
                st.session_state.username  = user
                st.session_state.account   = acc
                vis = load_json(VISIBLE_ACCOUNTS_FILE, {})
                st.session_state.visible_accounts = vis.get(acc, [acc])
                st.success(f"ようこそ、{acc}さん")
                st.rerun()
            else:
                st.error("認証に失敗しました")
    with tab2:
        na = st.text_input("アカウント名", key="reg_account")
        nu = st.text_input("ユーザーID", key="reg_user")
        npwd = st.text_input("パスワード", type="password", key="reg_pwd")
        if st.button("アカウント作成"):
            if register_account(na, nu, npwd, accounts):
                st.success("アカウント作成完了。ログインしてください。")
            else:
                st.error("重複しています")
    st.stop()

# ─── データ読み込み ───
if st.session_state.schedule.empty:
    st.session_state.schedule = load_schedule()
visible_df = st.session_state.schedule[
    st.session_state.schedule["アカウント"].isin(st.session_state.visible_accounts)
]

# ─── CSS：ヘッダー余白を詰める ───
st.markdown("""
<style>
.fc .fc-toolbar {margin:0.2em 0; padding:0.2em 0;}
</style>
""", unsafe_allow_html=True)

# ─── 表示モード切替 ───
view_map = {"月": "dayGridMonth", "週": "timeGridWeek", "一覧": "listWeek"}
v_label = st.selectbox("表示モード", list(view_map.keys()), index=0)
initial_view = view_map[v_label]

# ─── カレンダー描画 ───
events = to_calendar_events(visible_df, ACCOUNT_COLORS)
cal_res = calendar(
    events=events,
    options={
        "initialView": initial_view,
        "locale": "ja",
        "selectable": True,
        "editable": False,
        "headerToolbar": {"left":"prev,next today","center":"title","right":""},
        "height": "auto"
    },
    key=st.session_state.calendar_key
)

# ─── カレンダークリックでフォーム状態をセット ───
if cal_res:
    if cal_res.get("dateClick"):
        d = pd.to_datetime(cal_res["dateClick"]["date"]).date()
        st.session_state.form_date   = d
        st.session_state.eventClick  = None
        st.session_state.calendar_key = str(uuid.uuid4())
        st.rerun()
    if cal_res.get("eventClick"):
        st.session_state.eventClick  = cal_res["eventClick"]["event"]["id"]
        st.session_state.form_date   = None
        st.session_state.calendar_key = str(uuid.uuid4())
        st.rerun()

# ─── モバイルでフォーム発生時にサイドバー自動展開 ───
if (st.session_state.form_date or st.session_state.eventClick):
    html("""
    <script>
      if (window.innerWidth < 600) {
        const btn = document.querySelector('button[data-testid="stSidebarToggleButton"]');
        if (btn) btn.click();
      }
    </script>
    """, height=0)

# ─── サイドバー：アカウント一覧とフォーム ───
with st.sidebar:
    st.subheader("アカウント一覧")
    for acc in st.session_state.visible_accounts:
        col = ACCOUNT_COLORS.get(acc, "#000")
        st.markdown(
            f"<div style='display:flex;align-items:center;margin-bottom:4px;'>"
            f"<div style='width:12px;height:12px;background:{col};margin-right:5px;'></div>{acc}</div>",
            unsafe_allow_html=True
        )

    # — 予定追加フォーム —
    if st.session_state.form_date and not st.session_state.eventClick:
        st.markdown("---")
        st.subheader(f"{st.session_state.form_date.strftime('%Y年%m月%d日')} の予定を追加")
        with st.form("add_form"):
            acct    = st.selectbox("アカウント", st.session_state.visible_accounts)
            title   = st.text_input("タイトル")
            stime   = st.time_input("開始時刻", value=time(9,0))
            etime   = st.time_input("終了時刻", value=time(10,0))
            memo    = st.text_area("メモ", height=80)
            upfile  = st.file_uploader("添付ファイル")
            if st.form_submit_button("追加"):
                if not title.strip():
                    st.warning("タイトル必須")
                elif stime >= etime:
                    st.warning("開始時刻は終了時刻より前に")
                else:
                    path = ""
                    if upfile:
                        ext = os.path.splitext(upfile.name)[1]
                        fn  = f"{uuid.uuid4()}{ext}"
                        path = os.path.join(UPLOAD_DIR, fn)
                        with open(path,"wb") as f:
                            f.write(upfile.getbuffer())
                    new = {
                        "ID": str(uuid.uuid4()),
                        "日付": st.session_state.form_date,
                        "開始時刻": stime,
                        "終了時刻": etime,
                        "タイトル": title.strip(),
                        "メモ": memo.strip(),
                        "アカウント": acct,
                        "ファイルパス": path
                    }
                    st.session_state.schedule = pd.concat(
                        [st.session_state.schedule, pd.DataFrame([new])],
                        ignore_index=True
                    )
                    save_schedule(st.session_state.schedule)
                    st.success("追加完了")
                    st.session_state.form_date   = None
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

    # — 予定編集フォーム —
    if st.session_state.eventClick:
        eid = st.session_state.eventClick
        df  = st.session_state.schedule
        sel = df[df["ID"] == eid]
        if not sel.empty:
            row      = sel.iloc[0]
            editable = row["アカウント"] in st.session_state.visible_accounts
            st.markdown("---")
            st.subheader("予定編集")
            with st.form(f"edit_form_{eid}"):
                st.text_input("アカウント", value=row["アカウント"], disabled=True)
                nt = st.text_input("タイトル", value=row["タイトル"], disabled=not editable)
                stt= st.time_input("開始時刻", value=row["開始時刻"], disabled=not editable)
                ent= st.time_input("終了時刻", value=row["終了時刻"], disabled=not editable)
                mm = st.text_area("メモ", value=row["メモ"], disabled=not editable)
                nf = st.file_uploader("添付変更", type=None)
                upd= st.form_submit_button("更新", disabled=not editable)
                dl = st.form_submit_button("削除", disabled=not editable)

                if upd:
                    path = row["ファイルパス"]
                    if nf:
                        ext = os.path.splitext(nf.name)[1]
                        fn  = f"{uuid.uuid4()}{ext}"
                        path = os.path.join(UPLOAD_DIR, fn)
                        with open(path,"wb") as f:
                            f.write(nf.getbuffer())
                    idx = df[df["ID"] == eid].index[0]
                    for col, val in [
                        ("タイトル", nt),
                        ("開始時刻", stt),
                        ("終了時刻", ent),
                        ("メモ", mm),
                        ("ファイルパス", path)
                    ]:
                        st.session_state.schedule.at[idx, col] = val
                    save_schedule(st.session_state.schedule)
                    st.success("更新完了")
                    st.session_state.eventClick  = None
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

                if dl:
                    st.session_state.schedule = df[df["ID"] != eid].reset_index(drop=True)
                    save_schedule(st.session_state.schedule)
                    st.success("削除完了")
                    st.session_state.eventClick  = None
                    st.session_state.calendar_key = str(uuid.uuid4())
                    st.rerun()

# ─── メイン最下部：アカウント管理 ───
st.markdown("---")
st.subheader("表示アカウントの管理")
with st.expander("追加／削除"):
    a1 = st.text_input("アカウント名", key="mg_acc")
    u1 = st.text_input("ユーザーID", key="mg_user")
    p1 = st.text_input("パスワード", type="password", key="mg_pwd")
    if st.button("追加アカウント"):
        if verify_account(a1, u1, p1, accounts):
            if a1 not in st.session_state.visible_accounts:
                st.session_state.visible_accounts.append(a1)
                vis = load_json(VISIBLE_ACCOUNTS_FILE, {})
                vis[st.session_state.account] = st.session_state.visible_accounts
                save_json(VISIBLE_ACCOUNTS_FILE, vis)
                st.success("追加完了")
                st.rerun()
            else:
                st.info("既に表示中")
        else:
            st.error("認証失敗")
    opts = [x for x in st.session_state.visible_accounts if x != st.session_state.account]
    if opts:
        rem = st.selectbox("削除対象", opts, key="mg_rem")
        if st.button("削除アカウント"):
            st.session_state.visible_accounts.remove(rem)
            vis = load_json(VISIBLE_ACCOUNTS_FILE, {})
            vis[st.session_state.account] = st.session_state.visible_accounts
            save_json(VISIBLE_ACCOUNTS_FILE, vis)
            st.success("削除完了")
            st.rerun()