# =============================================================================
# Medical Physicist Workload & FTE Management System
# app.py — Single-file Streamlit Application (Google Apps Script Backend)
# =============================================================================
#
# ── SETUP INSTRUCTIONS ────────────────────────────────────────────────────────
#
# 1. INSTALL DEPENDENCIES
#    pip install streamlit pandas plotly requests streamlit-calendar
#
# 2. SET YOUR GOOGLE APPS SCRIPT URL BELOW (SCRIPT_URL constant).
#
# 3. RUN THE APP
#    streamlit run app.py
#
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import math
import json
from datetime import datetime, date

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

# ⚠️ วาง Web app URL ที่ได้จาก Google Apps Script ของคุณตรงนี้
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzKjgLJ7yRHLkDpCZejbmWEDBQcvyd-YZmeS7WMMYBVkKkkyhckElmRVoE1NpHNenX7NA/exec"

# FTE Standards (minutes)
MONTHLY_FTE_MINUTES = 8_750
ANNUAL_FTE_MINUTES  = 105_000

# ── TASK LIST (15 items, hardcoded per specification) ─────────────────────────
TASKS = {
    1:  "ควบคุมคุณภาพและจัดทำรายงานการควบคุมคุณภาพเครื่องมือทางรังสีวินิจฉัย รวมถึงติดตาม ควบคุม ประจำวัน สัปดาห์ เดือน ครึ่งปี ปี",
    2:  "ติดตาม ตรวจสอบ ความผิดปกติของเครื่องมือทางรังสีวินิจฉัยร่วมกับนักรังสีการแพทย์ และ วิศวกร",
    3:  "วัดและประเมินปริมาณรังสีกระเจิง และ ปริมาณรังสีรั่วไหล รวมถึงจัดทำรายงาน",
    4:  "จัดทำค่าปริมาณรังสีอ้างอิง (DRL) และจัดทำโปรโตคอลในการกำหนดปริมาณรังสีที่ผู้ป่วยได้รับ",
    5:  "ดำเนินการเกี่ยวกับการวัดปริมาณรังสีส่วนบุคคล (OSL/TLD) บันทึกรายงาน และหาทางรับมือหากรังสีเกินมาตรฐาน",
    6:  "ตรวจสอบคุณภาพอุปกรณ์กำบังรังสี เช่น เสื้อตะกั่ว thyroid shield",
    7:  "คำนวณปริมาณรังสีในผู้ป่วยตั้งครรภ์ รวมถึงผู้ป่วยที่ได้รับปริมาณรังสีสูงเกินขีดจำกัด",
    8:  "ตรวจสอบแรกรับ และประเมินประสิทธิภาพการใช้งานของเครื่องมือทางรังสีหลังการติดตั้ง ซ่อมแซม (Acceptance Test)",
    9:  "จัดทำและเข้าร่วมในการกำหนดรายละเอียดคุณลักษณะเฉพาะ (TOR/Spec) เพื่อการจัดซื้อเครื่องมือ",
    10: "จัดทำแผนการป้องกันอันตรายทางรังสี แผนฉุกเฉิน และแผนอุบัติเหตุทางรังสี",
    11: "ให้คำแนะนำการป้องกันอันตรายจากรังสี รวมถึงแผนฉุกเฉินทางรังสี",
    12: "ศึกษา ค้นคว้า วิเคราะห์ วิจัยทางฟิสิกส์การแพทย์",
    13: "ดำเนินการสอบเทียบมาตรฐานอุปกรณ์ที่ใช้ในการวัดปริมาณรังสี (Calibration)",
    14: "จัดทำรายงานการขออนุญาตการมีไว้ในครอบครองและการใช้งานเครื่องกำเนิดรังสี",
    15: "ตรวจสอบการได้รับรังสีกรณีเกิดเหตุใดๆ กับผู้ป่วยหลังการตรวจ",
}

TASK_LABELS = ["{}. {}…".format(k, v[:60]) if len(v) > 60 else "{}. {}".format(k, v) for k, v in TASKS.items()]
TASK_NO_FROM_LABEL = {label: no for no, label in zip(TASKS.keys(), TASK_LABELS)}

THAI_MONTHS = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม",
}

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Medical Physicist Workload",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&family=IBM+Plex+Sans+Thai:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sarabun', 'IBM Plex Sans Thai', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    }
    [data-testid="stSidebar"] * { color: #e0f2fe !important; }
    [data-testid="stSidebar"] .stRadio label { font-size: 1rem; padding: 6px 0; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #f0f9ff;
        border-left: 4px solid #0284c7;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #0284c7, #0ea5e9);
        color: white !important;
        padding: 10px 18px;
        border-radius: 8px;
        margin: 16px 0 12px 0;
        font-weight: 700;
        font-size: 1.05rem;
    }

    /* FTE highlight box */
    .fte-box {
        background: linear-gradient(135deg, #0f2027, #2c5364);
        color: #bae6fd;
        padding: 20px 28px;
        border-radius: 12px;
        font-size: 1.3rem;
        font-weight: 600;
        text-align: center;
        margin: 12px 0;
    }
    .fte-box span.big { font-size: 2.2rem; color: #38bdf8; }

    /* Success/error banners */
    .success-banner {
        background: #dcfce7; color: #15803d;
        border-left: 4px solid #16a34a;
        padding: 10px 16px; border-radius: 6px;
    }
    .error-banner {
        background: #fee2e2; color: #b91c1c;
        border-left: 4px solid #dc2626;
        padding: 10px 16px; border-radius: 6px;
    }

    /* Hide Streamlit branding */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE INITIALISATION ──────────────────────────────────────────────

if "line_token" not in st.session_state:
    st.session_state.line_token = ""

# ── APPS SCRIPT API HELPERS ───────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner="🔌 กำลังโหลดข้อมูลจาก Google Sheets...")
def fetch_all_data():
    """Fetch both logs and staff list in one GET request from GAS."""
    try:
        if "script.google.com" not in SCRIPT_URL:
            return {"logs": [], "staff": [], "error": "กรุณาตั้งค่า SCRIPT_URL ในแอปพลิเคชัน"}
            
        r = requests.get(SCRIPT_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
        return {"logs": [], "staff": [], "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"logs": [], "staff": [], "error": str(e)}

def post_to_gas(payload: dict) -> bool:
    """Send a POST request to GAS with the given JSON payload."""
    try:
        r = requests.post(SCRIPT_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code in [200, 302]:  # GAS typically redirects POST to a 302 GET, requests handles this.
            return True
        st.error(f"Error HTTP {r.status_code}")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def invalidate_cache():
    """Clear cached data so the UI refreshes on next rerun."""
    fetch_all_data.clear()

# ── DATA READING ──────────────────────────────────────────────────────────────

def load_workload_logs() -> pd.DataFrame:
    """Load all rows from Workload_Logs and return as a typed DataFrame."""
    data = fetch_all_data()
    if data.get("error"):
        st.error(f"โหลดข้อมูลภาระงานไม่สำเร็จ: {data['error']}")
        return pd.DataFrame(columns=["Timestamp","Date","Name","Task_No","Task_Name","Details","Minutes"])
        
    logs = data.get("logs", [])
    if not logs:
        return pd.DataFrame(columns=["Timestamp","Date","Name","Task_No","Task_Name","Details","Minutes"])
        
    df = pd.DataFrame(logs)
    df["Minutes"] = pd.to_numeric(df["Minutes"], errors="coerce").fillna(0)
    df["Task_No"] = pd.to_numeric(df["Task_No"], errors="coerce").fillna(0).astype(int)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

def load_staff_list() -> list:
    """Load staff names from Staff_List tab."""
    data = fetch_all_data()
    if data.get("error"):
        return []
    return data.get("staff", [])


# ── DATA WRITING ──────────────────────────────────────────────────────────────

def append_workload_log(date_val: date, name: str, task_no: int, task_name: str,
                        details: str, minutes: int) -> bool:
    """Append one row to Workload_Logs. Returns True on success."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "action": "append_log",
        "data": [timestamp, str(date_val), name, task_no, task_name, details, minutes]
    }
    if post_to_gas(payload):
        invalidate_cache()
        return True
    return False

def delete_workload_row(row_index: int) -> bool:
    """Delete a data row by 1-based sheet row index."""
    payload = {
        "action": "delete_log",
        "row_index": row_index
    }
    if post_to_gas(payload):
        invalidate_cache()
        return True
    return False

def add_staff(name: str) -> bool:
    """Add a name to Staff_List."""
    payload = {
        "action": "add_staff",
        "name": name
    }
    if post_to_gas(payload):
        invalidate_cache()
        return True
    return False

def delete_staff(name: str) -> bool:
    """Remove a name from Staff_List by searching for it."""
    payload = {
        "action": "delete_staff",
        "name": name
    }
    if post_to_gas(payload):
        invalidate_cache()
        return True
    return False


# ── LINE NOTIFY ───────────────────────────────────────────────────────────────

def send_line_notify(token: str, message: str) -> bool:
    """Send a message via LINE Notify. Returns True on HTTP 200."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload  = {"message": message}
        r = requests.post("https://notify-api.line.me/api/notify",
                          headers=headers, data=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        st.error(f"ส่ง LINE Notify ไม่สำเร็จ: {e}")
        return False


# ── FTE HELPERS ───────────────────────────────────────────────────────────────

def calc_fte(total_minutes: float, standard_minutes: float) -> float:
    if standard_minutes == 0:
        return 0.0
    return round(total_minutes / standard_minutes, 2)

def fte_html(total_minutes: float, fte: float, period: str = "เดือน") -> str:
    staff_needed = math.ceil(fte)
    return (
        '<div class="fte-box">'
        f'ภาระงานรวม{period} <span class="big">{fte}</span> FTE<br>'
        f'⏱️ {total_minutes:,.0f} นาที &nbsp;|&nbsp; '
        f'👥 ต้องการกำลังคน <span class="big">{staff_needed}</span> คน'
        '</div>'
    )


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚛️ Medical Physicist\n### Workload Manager")
    st.markdown("---")
    tab_choice = st.radio(
        "เลือกเมนู",
        options=[
            "📝 บันทึกภาระงาน",
            "📅 ประวัติและปฏิทิน",
            "📊 Dashboard & FTE",
            "⚙️ จัดการข้อมูล & Export",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("ระบบบริหารภาระงานนักฟิสิกส์การแพทย์\nv1.1 — Google Apps Script Backend")

# ── TAB 1: DATA ENTRY ─────────────────────────────────────────────────────────

if tab_choice == "📝 บันทึกภาระงาน":
    st.markdown('<div class="section-header">📝 บันทึกภาระงาน</div>', unsafe_allow_html=True)

    staff_list = load_staff_list()
    if not staff_list:
        st.warning("⚠️ ยังไม่มีรายชื่อเจ้าหน้าที่ — กรุณาเพิ่มชื่อในแท็บ 'จัดการข้อมูล & Export' ก่อน")

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("📅 วันที่", value=date.today(), key="entry_date")
            entry_name = st.selectbox(
                "👤 ชื่อผู้ปฏิบัติงาน",
                options=staff_list if staff_list else ["— กรุณาเพิ่มชื่อก่อน —"],
                key="entry_name",
            )
        with col2:
            entry_task_label = st.selectbox("📋 งาน", options=TASK_LABELS, key="entry_task")
            entry_minutes = st.number_input(
                "⏱️ เวลาที่ใช้ (นาที)", min_value=1, max_value=1440, value=30, step=5, key="entry_mins"
            )
        entry_details = st.text_input("📝 รายละเอียดเพิ่มเติม (ถ้ามี)", key="entry_details")

        submitted = st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True, type="primary")

    if submitted:
        if not staff_list:
            st.error("กรุณาเพิ่มชื่อเจ้าหน้าที่ก่อนบันทึก")
        else:
            task_no = TASK_NO_FROM_LABEL[entry_task_label]
            task_name = TASKS[task_no]
            ok = append_workload_log(
                entry_date, entry_name, task_no, task_name, entry_details, int(entry_minutes)
            )
            if ok:
                st.markdown(
                    '<div class="success-banner">✅ บันทึกข้อมูลสำเร็จแล้ว!</div>',
                    unsafe_allow_html=True,
                )

# ── TAB 2: HISTORY & CALENDAR ─────────────────────────────────────────────────

elif tab_choice == "📅 ประวัติและปฏิทิน":
    st.markdown('<div class="section-header">📅 ประวัติภาระงาน</div>', unsafe_allow_html=True)

    df = load_workload_logs()

    if df.empty:
        st.info("ยังไม่มีข้อมูลภาระงาน")
        st.stop()

    # ── Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        years_available = sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True)
        sel_year = st.selectbox("ปี (ค.ศ.)", options=["ทั้งหมด"] + years_available)
    with col2:
        sel_month = st.selectbox("เดือน", options=["ทั้งหมด"] + list(range(1, 13)),
                                 format_func=lambda x: "ทั้งหมด" if x == "ทั้งหมด" else THAI_MONTHS[x])
    with col3:
        names_available = ["ทั้งหมด"] + sorted(df["Name"].dropna().unique().tolist())
        sel_name = st.selectbox("ชื่อ", options=names_available)

    # Apply filters
    filtered = df.copy()
    if sel_year != "ทั้งหมด":
        filtered = filtered[filtered["Date"].dt.year == int(sel_year)]
    if sel_month != "ทั้งหมด":
        filtered = filtered[filtered["Date"].dt.month == int(sel_month)]
    if sel_name != "ทั้งหมด":
        filtered = filtered[filtered["Name"] == sel_name]

    st.markdown(f"**พบ {len(filtered)} รายการ | รวม {filtered['Minutes'].sum():,} นาที**")

    # ── Table display
    display_df = filtered.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df = display_df[["Timestamp","Date","Name","Task_No","Task_Name","Details","Minutes"]]
    display_df.columns = ["บันทึกเมื่อ","วันที่","ชื่อ","ลำดับงาน","ชื่องาน","รายละเอียด","นาที"]

    st.dataframe(display_df, use_container_width=True, height=320)

    # ── Calendar View (using streamlit-calendar)
    st.markdown('<div class="section-header">📆 ปฏิทินภาระงาน</div>', unsafe_allow_html=True)
    try:
        from streamlit_calendar import calendar  # type: ignore

        events = []
        for _, row in filtered.iterrows():
            if pd.notnull(row["Date"]):
                events.append({
                    "title": f"{row['Name']}: {str(row['Task_Name'])[:30]}… ({row['Minutes']}m)",
                    "start": row["Date"].strftime("%Y-%m-%d"),
                    "end":   row["Date"].strftime("%Y-%m-%d"),
                    "color": "#0284c7",
                })

        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left":  "prev,next today",
                "center":"title",
                "right": "dayGridMonth,listMonth",
            },
            "locale": "th",
            "height": 500,
        }
        calendar(events=events, options=calendar_options, key="workload_calendar")

    except ImportError:
        st.warning(
            "ติดตั้ง `streamlit-calendar` เพื่อดูปฏิทิน: `pip install streamlit-calendar`\n\n"
            "แสดงกราฟแท่งแทน:"
        )
        if not filtered.empty:
            daily = filtered.groupby(filtered["Date"].dt.date)["Minutes"].sum().reset_index()
            daily.columns = ["วันที่", "นาที"]
            fig = px.bar(daily, x="วันที่", y="นาที", title="ภาระงานรายวัน", color_discrete_sequence=["#0284c7"])
            st.plotly_chart(fig, use_container_width=True)

    # ── Delete record
    st.markdown('<div class="section-header">🗑️ ลบรายการ (กรณีบันทึกผิด)</div>', unsafe_allow_html=True)
    st.warning("⚠️ การลบข้อมูลไม่สามารถย้อนกลับได้")

    # Rebuild with original sheet row index (header = 1, data from 2)
    filtered_with_idx = filtered.copy()
    filtered_with_idx["_sheet_row"] = filtered_with_idx.index + 2  # +2: 1-based + header row

    row_options = {
        f"แถว {int(r['_sheet_row'])}: {r['Date'].strftime('%Y-%m-%d') if pd.notnull(r['Date']) else '?'} | {r['Name']} | {str(r['Task_Name'])[:40]}": int(r["_sheet_row"])
        for _, r in filtered_with_idx.iterrows()
    }

    if row_options:
        selected_label = st.selectbox("เลือกรายการที่ต้องการลบ", options=list(row_options.keys()))
        selected_row   = row_options[selected_label]
        if st.button("🗑️ ยืนยันการลบ", type="secondary"):
            if delete_workload_row(selected_row):
                st.success("ลบรายการสำเร็จแล้ว กรุณารีเฟรชหน้า")
                st.rerun()
    else:
        st.info("ไม่มีรายการที่สามารถลบได้ในขอบเขตการกรองปัจจุบัน")

# ── TAB 3: DASHBOARD & FTE ────────────────────────────────────────────────────

elif tab_choice == "📊 Dashboard & FTE":
    st.markdown('<div class="section-header">📊 Dashboard & FTE — การวิเคราะห์กำลังคน</div>',
                unsafe_allow_html=True)

    df = load_workload_logs()

    if df.empty:
        st.info("ยังไม่มีข้อมูลภาระงาน")
        st.stop()

    view_type = st.radio("มุมมอง", ["📅 รายเดือน", "📆 รายปี"], horizontal=True)

    # ── MONTHLY VIEW ──────────────────────────────────────────────────────────
    if view_type == "📅 รายเดือน":
        col1, col2 = st.columns(2)
        with col1:
            years_avail = sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True)
            m_year  = st.selectbox("ปี", options=years_avail, key="dash_year")
        with col2:
            m_month = st.selectbox("เดือน", options=list(range(1, 13)),
                                   format_func=lambda x: THAI_MONTHS[x], key="dash_month")

        monthly_df = df[(df["Date"].dt.year == m_year) & (df["Date"].dt.month == m_month)]
        total_mins = monthly_df["Minutes"].sum()
        fte_val    = calc_fte(total_mins, MONTHLY_FTE_MINUTES)

        # KPI row
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📋 รายการทั้งหมด", f"{len(monthly_df):,}")
        k2.metric("⏱️ นาทีรวม", f"{total_mins:,}")
        k3.metric("💼 FTE", f"{fte_val:.2f}")
        k4.metric("👥 กำลังคนที่ต้องการ", f"{math.ceil(fte_val)} คน")

        st.markdown(fte_html(total_mins, fte_val, period="เดือนนี้"), unsafe_allow_html=True)

        if monthly_df.empty:
            st.info("ไม่มีข้อมูลในเดือนที่เลือก")
        else:
            # Bar chart — workload by person
            by_person = (
                monthly_df.groupby("Name")["Minutes"].sum().reset_index()
                .sort_values("Minutes", ascending=False)
            )
            by_person["FTE"] = by_person["Minutes"].apply(lambda m: calc_fte(m, MONTHLY_FTE_MINUTES))

            fig_bar = px.bar(
                by_person, x="Name", y="Minutes",
                title=f"ภาระงานรายบุคคล — {THAI_MONTHS[m_month]} {m_year}",
                color="Name",
                text="Minutes",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_bar.add_hline(y=MONTHLY_FTE_MINUTES, line_dash="dash",
                              annotation_text="1 FTE (8,750 น.)", line_color="#ef4444")
            fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_bar.update_layout(showlegend=False, height=380)
            st.plotly_chart(fig_bar, use_container_width=True)

            # Bar chart — workload by task
            by_task = (
                monthly_df.groupby(["Task_No","Task_Name"])["Minutes"].sum().reset_index()
                .sort_values("Minutes", ascending=False)
            )
            by_task["Task_Short"] = by_task["Task_No"].astype(str) + ". " + by_task["Task_Name"].str[:35] + "..."
            fig_task = px.bar(
                by_task, x="Minutes", y="Task_Short", orientation="h",
                title="ภาระงานแยกตามประเภทงาน",
                color="Minutes",
                color_continuous_scale="Blues",
                text="Minutes",
            )
            fig_task.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_task.update_layout(yaxis=dict(autorange="reversed"), height=460, showlegend=False)
            st.plotly_chart(fig_task, use_container_width=True)

            # Per-person FTE table
            st.markdown("**ตารางสรุป FTE รายบุคคล**")
            by_person["FTE"] = by_person["FTE"].map(lambda x: f"{x:.3f}")
            by_person.columns = ["ชื่อ", "นาที", "FTE"]
            st.dataframe(by_person, use_container_width=True, hide_index=True)

    # ── ANNUAL VIEW ───────────────────────────────────────────────────────────
    else:
        years_avail = sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True)
        a_year = st.selectbox("ปี", options=years_avail, key="dash_anual_year")

        annual_df  = df[df["Date"].dt.year == a_year]
        total_mins = annual_df["Minutes"].sum()
        fte_val    = calc_fte(total_mins, ANNUAL_FTE_MINUTES)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📋 รายการทั้งหมด", f"{len(annual_df):,}")
        k2.metric("⏱️ นาทีรวม", f"{total_mins:,}")
        k3.metric("💼 FTE รายปี", f"{fte_val:.2f}")
        k4.metric("👥 กำลังคนที่ต้องการ", f"{math.ceil(fte_val)} คน")

        st.markdown(fte_html(total_mins, fte_val, period="รายปี"), unsafe_allow_html=True)

        if annual_df.empty:
            st.info("ไม่มีข้อมูลในปีที่เลือก")
        else:
            col_left, col_right = st.columns(2)

            # Pie — time by task
            by_task = (
                annual_df.groupby(["Task_No","Task_Name"])["Minutes"].sum().reset_index()
                .sort_values("Minutes", ascending=False)
            )
            by_task["Label"] = by_task["Task_No"].astype(str) + ". " + by_task["Task_Name"].str[:30] + "..."
            fig_pie = px.pie(
                by_task, names="Label", values="Minutes",
                title=f"สัดส่วนเวลาตามประเภทงาน ปี {a_year}",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(height=480, showlegend=False)
            col_left.plotly_chart(fig_pie, use_container_width=True)

            # Pie — by person
            by_person = (
                annual_df.groupby("Name")["Minutes"].sum().reset_index()
                .sort_values("Minutes", ascending=False)
            )
            fig_pie2 = px.pie(
                by_person, names="Name", values="Minutes",
                title=f"สัดส่วนเวลาตามบุคคล ปี {a_year}",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_pie2.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie2.update_layout(height=480)
            col_right.plotly_chart(fig_pie2, use_container_width=True)

            # Monthly trend
            monthly_trend = (
                annual_df.groupby(annual_df["Date"].dt.month)["Minutes"]
                .sum().reset_index()
            )
            monthly_trend.columns = ["Month", "Minutes"]
            monthly_trend["Month_Name"] = monthly_trend["Month"].map(THAI_MONTHS)
            monthly_trend["FTE"] = monthly_trend["Minutes"].apply(lambda m: calc_fte(m, MONTHLY_FTE_MINUTES))

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=monthly_trend["Month_Name"], y=monthly_trend["Minutes"],
                name="นาที", marker_color="#7dd3fc",
                yaxis="y1",
            ))
            fig_trend.add_trace(go.Scatter(
                x=monthly_trend["Month_Name"], y=monthly_trend["FTE"],
                name="FTE", mode="lines+markers",
                marker=dict(color="#f97316", size=8),
                line=dict(color="#f97316", width=2),
                yaxis="y2",
            ))
            fig_trend.update_layout(
                title=f"แนวโน้มภาระงานรายเดือน ปี {a_year}",
                yaxis=dict(title="นาที"),
                yaxis2=dict(title="FTE", overlaying="y", side="right", showgrid=False),
                legend=dict(x=0, y=1),
                height=360,
            )
            st.plotly_chart(fig_trend, use_container_width=True)

# ── TAB 4: SETTINGS & EXPORT ─────────────────────────────────────────────────

elif tab_choice == "⚙️ จัดการข้อมูล & Export":
    st.markdown('<div class="section-header">⚙️ จัดการข้อมูล & Export</div>', unsafe_allow_html=True)

    # ── Staff Management
    st.subheader("👤 จัดการรายชื่อเจ้าหน้าที่")
    staff_list = load_staff_list()
    st.write("รายชื่อปัจจุบัน:", ", ".join(staff_list) if staff_list else "ยังไม่มีรายชื่อ")

    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("➕ เพิ่มชื่อใหม่", placeholder="กรอกชื่อ-นามสกุล")
        if st.button("เพิ่ม", type="primary"):
            if new_name.strip():
                if new_name.strip() in staff_list:
                    st.warning(f"มีชื่อ '{new_name.strip()}' อยู่แล้ว")
                else:
                    if add_staff(new_name.strip()):
                        st.success(f"เพิ่ม '{new_name.strip()}' สำเร็จ")
                        st.rerun()
            else:
                st.error("กรุณากรอกชื่อ")

    with col2:
        if staff_list:
            del_name = st.selectbox("🗑️ ลบรายชื่อ", options=staff_list, key="del_staff")
            if st.button("ลบ", type="secondary"):
                if delete_staff(del_name):
                    st.success(f"ลบ '{del_name}' สำเร็จ")
                    st.rerun()
        else:
            st.info("ไม่มีรายชื่อให้ลบ")

    st.markdown("---")

    # ── LINE Notify Settings
    st.subheader("🔔 ตั้งค่า LINE Notify")
    line_token_input = st.text_input(
        "LINE Notify Token",
        value=st.session_state.line_token,
        type="password",
        help="สร้าง Token ได้ที่ https://notify-bot.line.me/my/",
    )
    if st.button("💾 บันทึก Token"):
        st.session_state.line_token = line_token_input.strip()
        st.success("บันทึก Token ลงใน Session แล้ว (จะหายเมื่อปิดแอป)")

    st.markdown("---")

    # ── LINE Export
    st.subheader("📤 ส่งรายงานไปยัง LINE")

    df = load_workload_logs()
    col1, col2 = st.columns(2)
    with col1:
        years_avail_e = sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True) if not df.empty else [datetime.now().year]
        exp_year  = st.selectbox("ปี", options=years_avail_e, key="exp_year")
    with col2:
        exp_month = st.selectbox("เดือน", options=list(range(1, 13)),
                                 format_func=lambda x: THAI_MONTHS[x], key="exp_month")

    if st.button("📤 ส่งรายงานไป LINE", type="primary", disabled=not st.session_state.line_token):
        if df.empty:
            st.error("ไม่มีข้อมูลภาระงาน")
        else:
            monthly_exp = df[(df["Date"].dt.year == exp_year) & (df["Date"].dt.month == exp_month)]
            total_mins  = int(monthly_exp["Minutes"].sum())
            fte_val     = calc_fte(total_mins, MONTHLY_FTE_MINUTES)
            staff_used  = ", ".join(sorted(monthly_exp["Name"].dropna().unique().tolist())) or "ไม่มีข้อมูล"
            staff_count = math.ceil(fte_val)

            message = (
                f"\n📊 รายงานภาระงานเดือน {THAI_MONTHS[exp_month]} {exp_year}\n"
                f"👥 ผู้ปฏิบัติงาน: {staff_used}\n"
                f"⏱️ เวลารวม: {total_mins:,} นาที\n"
                f"💡 คิดเป็น: {fte_val:.2f} FTE\n"
                f"📌 จำนวนคนที่เหมาะสม: {staff_count} คน"
            )

            st.code(message, language=None)
            ok = send_line_notify(st.session_state.line_token, message)
            if ok:
                st.success("✅ ส่งรายงานไป LINE สำเร็จแล้ว!")
            else:
                st.error("❌ ส่งไม่สำเร็จ กรุณาตรวจสอบ Token")

    if not st.session_state.line_token:
        st.caption("⚠️ กรุณาบันทึก LINE Notify Token ก่อนส่งรายงาน")

    st.markdown("---")

    # ── Connection Test
    st.subheader("🔌 ทดสอบการเชื่อมต่อ Google Apps Script API")
    if st.button("ทดสอบการเชื่อมต่อ"):
        try:
            r = requests.get(SCRIPT_URL, timeout=10)
            if r.status_code == 200 and "logs" in r.json():
                st.success("✅ เชื่อมต่อ Google Apps Script สำเร็จ! สามารถอ่านและเขียนข้อมูลได้")
            else:
                st.error("❌ เชื่อมต่อสำเร็จแต่รูปแบบข้อมูลที่ตอบกลับมาไม่ถูกต้อง ตรวจสอบ SCRIPT_URL อีกครั้ง")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")

    # ── Refresh cache button
    if st.button("🔄 รีเฟรชข้อมูล (ล้าง Cache)"):
        invalidate_cache()
        st.success("ล้าง Cache แล้ว — รีเฟรชหน้าเพื่อโหลดข้อมูลใหม่")
        st.rerun()