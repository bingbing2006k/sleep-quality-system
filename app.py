import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("sleep_system.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sleep_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date TEXT NOT NULL UNIQUE,
            sleep_start TEXT NOT NULL,
            wake_time TEXT NOT NULL,
            sleep_hours REAL NOT NULL,
            sleep_quality INTEGER NOT NULL,
            wake_feeling INTEGER NOT NULL,
            night_wake_count INTEGER NOT NULL,
            stress_level INTEGER NOT NULL,
            screen_before_sleep INTEGER NOT NULL,
            caffeine_after_noon INTEGER NOT NULL,
            note TEXT,
            sleep_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DB_PATH)


def calc_sleep_hours(start_time, end_time):
    today = datetime.today().date()
    start = datetime.combine(today, start_time)
    end = datetime.combine(today, end_time)
    if end <= start:
        end += timedelta(days=1)
    return round((end - start).total_seconds() / 3600, 2)


def calc_sleep_score(hours, quality, feeling, wakes, stress, screen, caffeine):
    score = 0
    # 睡眠時數：滿分 35
    if 7 <= hours <= 9:
        score += 35
    elif 6 <= hours < 7 or 9 < hours <= 10:
        score += 25
    elif 5 <= hours < 6 or 10 < hours <= 11:
        score += 15
    else:
        score += 5

    # 主觀睡眠品質：滿分 25
    score += quality * 5

    # 起床精神：滿分 20
    score += feeling * 4

    # 夜醒次數扣分
    score -= min(wakes * 4, 16)

    # 壓力、睡前螢幕、咖啡因扣分
    score -= stress * 2
    if screen:
        score -= 6
    if caffeine:
        score -= 6

    score = max(0, min(100, int(score)))
    if score >= 75:
        risk = "低風險"
    elif score >= 50:
        risk = "中風險"
    else:
        risk = "高風險"
    return score, risk


def load_records():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM sleep_records ORDER BY record_date DESC", conn)
    conn.close()
    return df


def save_record(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO sleep_records (
            record_date, sleep_start, wake_time, sleep_hours, sleep_quality,
            wake_feeling, night_wake_count, stress_level, screen_before_sleep,
            caffeine_after_noon, note, sleep_score, risk_level, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        data,
    )
    conn.commit()
    conn.close()


def delete_record(record_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sleep_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def suggestion(score, hours, stress, screen, caffeine, wakes):
    tips = []
    if hours < 6:
        tips.append("睡眠時數偏少，建議先把目標放在每天多睡 30 分鐘。")
    if wakes >= 2:
        tips.append("夜醒次數偏多，可以記錄睡前飲水、壓力與環境光線。")
    if stress >= 4:
        tips.append("睡前壓力偏高，建議睡前 10 分鐘做放鬆呼吸或整理明日待辦。")
    if screen:
        tips.append("睡前有使用螢幕，建議睡前 30 分鐘降低亮度或暫停滑手機。")
    if caffeine:
        tips.append("下午後有攝取咖啡因，可能影響入睡品質。")
    if score >= 75 and not tips:
        tips.append("目前睡眠狀態穩定，可以維持固定作息。")
    return tips


st.set_page_config(page_title="睡眠品質追蹤系統", page_icon="🌙", layout="wide")
init_db()

st.title("🌙 睡眠品質追蹤系統")
st.caption("專注於睡眠，不做人體電池；用每天睡眠紀錄分析睡眠分數、疲勞風險與改善建議。")

menu = st.sidebar.radio("功能選單", ["新增睡眠紀錄", "睡眠儀表板", "歷史資料", "系統說明"])

if menu == "新增睡眠紀錄":
    st.header("新增睡眠紀錄")
    with st.form("sleep_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            record_date = st.date_input("紀錄日期", value=date.today())
            sleep_start = st.time_input("入睡時間")
            wake_time = st.time_input("起床時間")
        with col2:
            sleep_quality = st.slider("主觀睡眠品質 1~5", 1, 5, 3)
            wake_feeling = st.slider("起床精神 1~5", 1, 5, 3)
            night_wake_count = st.number_input("夜醒次數", min_value=0, max_value=20, value=0)
        with col3:
            stress_level = st.slider("睡前壓力 1~5", 1, 5, 3)
            screen_before_sleep = st.checkbox("睡前 30 分鐘有使用手機/電腦")
            caffeine_after_noon = st.checkbox("中午後有喝咖啡/茶/能量飲")
        note = st.text_area("備註", placeholder="例如：考試壓力、運動、晚餐太晚吃、房間太熱……")
        submitted = st.form_submit_button("儲存紀錄")

    if submitted:
        hours = calc_sleep_hours(sleep_start, wake_time)
        score, risk = calc_sleep_score(
            hours,
            sleep_quality,
            wake_feeling,
            night_wake_count,
            stress_level,
            int(screen_before_sleep),
            int(caffeine_after_noon),
        )
        save_record(
            (
                str(record_date),
                sleep_start.strftime("%H:%M"),
                wake_time.strftime("%H:%M"),
                hours,
                sleep_quality,
                wake_feeling,
                night_wake_count,
                stress_level,
                int(screen_before_sleep),
                int(caffeine_after_noon),
                note,
                score,
                risk,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        st.success(f"已儲存！睡眠時數 {hours} 小時，睡眠分數 {score} 分，疲勞風險：{risk}")
        for tip in suggestion(score, hours, stress_level, int(screen_before_sleep), int(caffeine_after_noon), night_wake_count):
            st.info(tip)

elif menu == "睡眠儀表板":
    st.header("睡眠儀表板")
    df = load_records()
    if df.empty:
        st.warning("目前還沒有資料，請先新增睡眠紀錄。")
    else:
        df["record_date"] = pd.to_datetime(df["record_date"])
        latest = df.sort_values("record_date").iloc[-1]
        recent7 = df.sort_values("record_date").tail(7)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新睡眠分數", f"{latest['sleep_score']} 分")
        c2.metric("最新疲勞風險", latest["risk_level"])
        c3.metric("最新睡眠時數", f"{latest['sleep_hours']} 小時")
        c4.metric("近 7 筆平均分數", f"{recent7['sleep_score'].mean():.1f} 分")

        chart_df = df.sort_values("record_date")[["record_date", "sleep_score", "sleep_hours"]].set_index("record_date")
        st.subheader("睡眠分數趨勢")
        st.line_chart(chart_df[["sleep_score"]])
        st.subheader("睡眠時數趨勢")
        st.line_chart(chart_df[["sleep_hours"]])

        st.subheader("最新建議")
        for tip in suggestion(
            latest["sleep_score"],
            latest["sleep_hours"],
            latest["stress_level"],
            latest["screen_before_sleep"],
            latest["caffeine_after_noon"],
            latest["night_wake_count"],
        ):
            st.info(tip)

elif menu == "歷史資料":
    st.header("歷史資料")
    df = load_records()
    if df.empty:
        st.warning("目前還沒有資料。")
    else:
        show_df = df.rename(
            columns={
                "record_date": "日期",
                "sleep_start": "入睡時間",
                "wake_time": "起床時間",
                "sleep_hours": "睡眠時數",
                "sleep_quality": "睡眠品質",
                "wake_feeling": "起床精神",
                "night_wake_count": "夜醒次數",
                "stress_level": "壓力",
                "screen_before_sleep": "睡前螢幕",
                "caffeine_after_noon": "下午咖啡因",
                "note": "備註",
                "sleep_score": "睡眠分數",
                "risk_level": "風險等級",
            }
        )
        st.dataframe(show_df[["id", "日期", "入睡時間", "起床時間", "睡眠時數", "睡眠分數", "風險等級", "備註"]], use_container_width=True)

        with st.expander("刪除資料"):
            record_id = st.number_input("輸入要刪除的 id", min_value=1, step=1)
            if st.button("刪除"):
                delete_record(record_id)
                st.success("已刪除，請重新整理或切換頁面查看。")

elif menu == "系統說明":
    st.header("系統說明")
    st.markdown(
        """
        ### 系統定位
        本系統為一套「睡眠品質分析與疲勞風險預警系統」，透過每日睡眠紀錄，協助使用者了解自身睡眠狀況，並根據睡眠時數、夜醒次數、睡前習慣與壓力程度，評估隔日可能產生的疲勞風險。
        
        ### 主要功能
        1. 記錄每日入睡時間、起床時間、睡眠品質與夜醒次數  
        2. 自動計算睡眠時數與睡眠分數  
        3. 判斷低／中／高疲勞風險  
        4. 顯示睡眠分數與睡眠時數趨勢圖  
        5. 根據睡前螢幕、咖啡因、壓力等因素給改善建議  

        ### 資料庫
        使用 SQLite，會自動產生 `sleep_system.db`。
        """
    )
