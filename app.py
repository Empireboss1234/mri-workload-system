# =============================================================================
# Medical Physicist Workload & FTE Management System
# app.py — Single-file Streamlit Application (Google Apps Script Backend)
# =============================================================================
#
# ── SETUP INSTRUCTIONS ────────────────────────────────────────────────────────
#
# 1. INSTALL DEPENDENCIES
#    pip install streamlit pandas plotly requests streamlit-calendar python-docx
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
import io
from datetime import datetime, date, timedelta
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

# ⚠️ วาง Web app URL ที่ได้จาก Google Apps Script ของคุณตรงนี้
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzKjgLJ7yRHLkDpCZejbmWEDBQcvyd-YZmeS7WMMYBVkKkkyhckElmRVoE1NpHNenX7NA/exec"

# FTE Standards (minutes)
MONTHLY_FTE_MINUTES = 8_750
ANNUAL_FTE_MINUTES  = 105_000

# ── TASK LIST ─────────────────────────────────────────────────────────────────
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

TASK_LABELS = [f"{k}. {v[:60]}…" if len(v) > 60 else f"{k}. {v}" for k, v in TASKS.items()]
TASK_NO_FROM_LABEL = {label: no for no, label in zip(TASKS.keys(), TASK_LABELS)}

THAI_MONTHS = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม",
}

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Medical Physicist Workload", page_icon="⚛️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f2027 0%, #203a43 50%, #2c5364 100%); }
    [data-testid="stSidebar"] * { color: #e0f2fe !important; }
    [data-testid="stMetric"] { background: #f0f9ff; border-left: 4px solid #0284c7; border-radius: 8px; padding: 12px 16px; }
    .section-header { background: linear-gradient(90deg, #0284c7, #0ea5e9); color: white !important; padding: 10px 18px; border-radius: 8px; margin: 16px 0 12px 0; font-weight: 700; }
    .fte-box { background: linear-gradient(135deg, #0f2027, #2c5364); color: #bae6fd; padding: 20px 28px; border-radius: 12px; font-size: 1.3rem; font-weight: 600; text-align: center; margin: 12px 0; }
    .fte-box span.big { font-size: 2.2rem; color: #38bdf8; }
    .success-banner { background: #dcfce7; color: #15803d; border-left: 4px solid #16a34a; padding: 10px 16px; border-radius: 6px; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── APPS SCRIPT API HELPERS ───────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner="🔌 กำลังโหลดข้อมูลจาก Google Sheets...")
def fetch_all_data():
    try:
        if "script.google.com" not in SCRIPT_URL:
            return {"logs": [], "staff": [], "error": "กรุณาตั้งค่า SCRIPT_URL"}
        r = requests.get(SCRIPT_URL, timeout=15)
        if r.status_code == 200: return r.json()
        return {"logs": [], "staff": [], "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"logs": [], "staff": [], "error": str(e)}

def post_to_gas(payload: dict) -> bool:
    try:
        r = requests.post(SCRIPT_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code in [200, 302]: return True
        st.error(f"Error HTTP {r.status_code}")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def invalidate_cache():
    fetch_all_data.clear()

def load_workload_logs() -> pd.DataFrame:
    data = fetch_all_data()
    if data.get("error"):
        st.error(f"โหลดข้อมูลภาระงานไม่สำเร็จ: {data['error']}")
        return pd.DataFrame(columns=["Timestamp","Date","Name","Task_No","Task_Name","Details","Minutes","Start_Time","End_Time"])
    logs = data.get("logs", [])
    df = pd.DataFrame(logs) if logs else pd.DataFrame(columns=["Timestamp","Date","Name","Task_No","Task_Name","Details","Minutes","Start_Time","End_Time"])
    if "Start_Time" not in df.columns: df["Start_Time"] = "-"
    if "End_Time" not in df.columns: df["End_Time"] = "-"
    if not df.empty:
        df["Minutes"] = pd.to_numeric(df["Minutes"], errors="coerce").fillna(0)
        df["Task_No"] = pd.to_numeric(df["Task_No"], errors="coerce").fillna(0).astype(int)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

def load_staff_list() -> list:
    return fetch_all_data().get("staff", [])

def append_workload_log(date_val, name, task_no, task_name, details, minutes, start_time, end_time):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {"action": "append_log", "data": [timestamp, str(date_val), name, task_no, task_name, details, minutes, start_time, end_time]}
    if post_to_gas(payload):
        invalidate_cache()
        return True
    return False

def delete_workload_row(row_index):
    if post_to_gas({"action": "delete_log", "row_index": row_index}):
        invalidate_cache()
        return True
    return False

def add_staff(name):
    if post_to_gas({"action": "add_staff", "name": name}):
        invalidate_cache()
        return True
    return False

def delete_staff(name):
    if post_to_gas({"action": "delete_staff", "name": name}):
        invalidate_cache()
        return True
    return False

def calc_fte(total_minutes, standard_minutes):
    return round(total_minutes / standard_minutes, 2) if standard_minutes > 0 else 0.0

def fte_html(total_minutes, fte, period="เดือน"):
    return f'<div class="fte-box">ภาระงานรวม{period} <span class="big">{fte}</span> FTE<br>⏱️ {total_minutes:,.0f} นาที &nbsp;|&nbsp; 👥 ต้องการกำลังคน <span class="big">{math.ceil(fte)}</span> คน</div>'

# ── WORD EXPORT GENERATOR ─────────────────────────────────────────────────────

def generate_word_report(df_report, report_type, period_text):
    doc = Document()
    
    # Title
    heading = doc.add_heading('รายงานสรุปภาระงาน (Workload Report)', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Metadata
    doc.add_paragraph(f"หน่วยงาน: สาขารังสีวินิจฉัย โรงพยาบาลสงขลานครินทร์")
    doc.add_paragraph(f"ประเภทรายงาน: {report_type}")
    doc.add_paragraph(f"ช่วงเวลาที่รายงาน: {period_text}")
    doc.add_paragraph(f"วันที่พิมพ์รายงาน: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    total_mins = df_report["Minutes"].sum()
    if report_type == "รายงานรายปี":
        fte = calc_fte(total_mins, ANNUAL_FTE_MINUTES)
    else:
        fte = calc_fte(total_mins, MONTHLY_FTE_MINUTES)
        
    doc.add_paragraph(f"สรุปผลรวม: ใช้เวลาปฏิบัติงานทั้งหมด {total_mins:,.0f} นาที (คิดเป็น {fte} FTE)")
    doc.add_heading('รายละเอียดการปฏิบัติงาน', level=1)
    
    # Table
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'วันที่'
    hdr_cells[1].text = 'เวลา'
    hdr_cells[2].text = 'ผู้ปฏิบัติงาน'
    hdr_cells[3].text = 'ชื่องาน'
    hdr_cells[4].text = 'นาที'
    
    # Sort by date
    df_report = df_report.sort_values(by="Date")
    
    for _, row in df_report.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else '-'
        time_str = f"{row.get('Start_Time', '-')} - {row.get('End_Time', '-')}"
        row_cells[1].text = time_str if time_str != "- - -" else "-"
        row_cells[2].text = str(row['Name'])
        task_desc = f"{row['Task_No']}. {str(row['Task_Name'])[:40]}..."
        row_cells[3].text = task_desc
        row_cells[4].text = str(row['Minutes'])
        
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚛️ Medical Physicist\n### Workload Manager")
    st.markdown("---")
    tab_choice = st.radio("เลือกเมนู", ["📝 บันทึกภาระงาน", "📅 ประวัติและปฏิทิน", "📊 Dashboard & FTE", "⚙️ จัดการข้อมูล & Export"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("ระบบบริหารภาระงานนักฟิสิกส์การแพทย์\nv1.3 — Word Export Edition")

# ── TAB 1: DATA ENTRY ─────────────────────────────────────────────────────────

if tab_choice == "📝 บันทึกภาระงาน":
    st.markdown('<div class="section-header">📝 บันทึกภาระงาน</div>', unsafe_allow_html=True)
    staff_list = load_staff_list()
    if not staff_list: st.warning("⚠️ ยังไม่มีรายชื่อเจ้าหน้าที่ — กรุณาเพิ่มชื่อในแท็บ 'จัดการข้อมูล & Export' ก่อน")

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("📅 วันที่", value=date.today())
            entry_name = st.selectbox("👤 ชื่อผู้ปฏิบัติงาน", options=staff_list if staff_list else ["— กรุณาเพิ่มชื่อก่อน —"])
            entry_details = st.text_input("📝 รายละเอียดเพิ่มเติม (ถ้ามี)")
        with col2:
            entry_task_label = st.selectbox("📋 งาน", options=TASK_LABELS)
            time_col1, time_col2 = st.columns(2)
            with time_col1: start_time = st.time_input("เวลาเริ่ม", value=datetime.strptime("08:30", "%H:%M").time())
            with time_col2: end_time = st.time_input("เวลาสิ้นสุด", value=datetime.strptime("09:00", "%H:%M").time())
            st.caption("ระบบจะคำนวณจำนวนนาทีให้โดยอัตโนมัติเมื่อกดบันทึกข้อมูล")

        if st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True, type="primary"):
            if not staff_list: st.error("กรุณาเพิ่มชื่อเจ้าหน้าที่ก่อนบันทึก")
            else:
                dt_start, dt_end = datetime.combine(entry_date, start_time), datetime.combine(entry_date, end_time)
                if dt_end < dt_start: dt_end += timedelta(days=1)
                calc_minutes = int((dt_end - dt_start).total_seconds() / 60)
                
                if calc_minutes <= 0: st.error("⚠️ เวลาไม่ถูกต้อง")
                elif append_workload_log(entry_date, entry_name, TASK_NO_FROM_LABEL[entry_task_label], TASKS[TASK_NO_FROM_LABEL[entry_task_label]], entry_details, calc_minutes, start_time.strftime("%H:%M"), end_time.strftime("%H:%M")):
                    st.markdown(f'<div class="success-banner">✅ บันทึกสำเร็จ! ใช้เวลาไป <b>{calc_minutes} นาที</b></div>', unsafe_allow_html=True)

# ── TAB 2: HISTORY & CALENDAR ─────────────────────────────────────────────────

elif tab_choice == "📅 ประวัติและปฏิทิน":
    st.markdown('<div class="section-header">📅 ประวัติภาระงาน</div>', unsafe_allow_html=True)
    df = load_workload_logs()
    if df.empty:
        st.info("ยังไม่มีข้อมูลภาระงาน")
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1: sel_year = st.selectbox("ปี (ค.ศ.)", ["ทั้งหมด"] + sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True))
    with col2: sel_month = st.selectbox("เดือน", ["ทั้งหมด"] + list(range(1, 13)), format_func=lambda x: "ทั้งหมด" if x == "ทั้งหมด" else THAI_MONTHS[x])
    with col3: sel_name = st.selectbox("ชื่อ", ["ทั้งหมด"] + sorted(df["Name"].dropna().unique().tolist()))

    filtered = df.copy()
    if sel_year != "ทั้งหมด": filtered = filtered[filtered["Date"].dt.year == int(sel_year)]
    if sel_month != "ทั้งหมด": filtered = filtered[filtered["Date"].dt.month == int(sel_month)]
    if sel_name != "ทั้งหมด": filtered = filtered[filtered["Name"] == sel_name]

    st.markdown(f"**พบ {len(filtered)} รายการ | รวม {filtered['Minutes'].sum():,} นาที**")
    
    display_df = filtered.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df = display_df[["Timestamp", "Date", "Start_Time", "End_Time", "Name", "Task_No", "Task_Name", "Details", "Minutes"]]
    display_df.columns = ["บันทึกเมื่อ", "วันที่", "เวลาเริ่ม", "เวลาสิ้นสุด", "ชื่อ", "ลำดับงาน", "ชื่องาน", "รายละเอียด", "นาทีรวม"]
    st.dataframe(display_df, use_container_width=True, height=320)

    st.markdown('<div class="section-header">🗑️ ลบรายการ (กรณีบันทึกผิด)</div>', unsafe_allow_html=True)
    filtered_with_idx = filtered.copy()
    filtered_with_idx["_sheet_row"] = filtered_with_idx.index + 2
    row_options = {f"แถว {int(r['_sheet_row'])}: {r['Date'].strftime('%Y-%m-%d')} | {r['Name']} | {str(r['Task_Name'])[:40]}": int(r["_sheet_row"]) for _, r in filtered_with_idx.iterrows() if pd.notnull(r['Date'])}
    
    if row_options:
        selected_row = row_options[st.selectbox("เลือกรายการที่ต้องการลบ", list(row_options.keys()))]
        if st.button("🗑️ ยืนยันการลบ", type="secondary") and delete_workload_row(selected_row):
            st.success("ลบรายการสำเร็จแล้ว กรุณารีเฟรชหน้า")
            st.rerun()

# ── TAB 3: DASHBOARD & FTE ────────────────────────────────────────────────────

elif tab_choice == "📊 Dashboard & FTE":
    st.markdown('<div class="section-header">📊 Dashboard & FTE — การวิเคราะห์กำลังคน</div>', unsafe_allow_html=True)
    df = load_workload_logs()
    if df.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()

    view_type = st.radio("มุมมอง", ["📅 รายเดือน", "📆 รายปี"], horizontal=True)

    if view_type == "📅 รายเดือน":
        col1, col2 = st.columns(2)
        with col1: m_year = st.selectbox("ปี", sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True))
        with col2: m_month = st.selectbox("เดือน", list(range(1, 13)), format_func=lambda x: THAI_MONTHS[x])

        monthly_df = df[(df["Date"].dt.year == m_year) & (df["Date"].dt.month == m_month)]
        total_mins = monthly_df["Minutes"].sum()
        fte_val = calc_fte(total_mins, MONTHLY_FTE_MINUTES)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📋 รายการทั้งหมด", f"{len(monthly_df):,}")
        k2.metric("⏱️ นาทีรวม", f"{total_mins:,}")
        k3.metric("💼 FTE", f"{fte_val:.2f}")
        k4.metric("👥 กำลังคนที่ต้องการ", f"{math.ceil(fte_val)} คน")
        st.markdown(fte_html(total_mins, fte_val, period="เดือนนี้"), unsafe_allow_html=True)

        if not monthly_df.empty:
            by_person = monthly_df.groupby("Name")["Minutes"].sum().reset_index().sort_values("Minutes", ascending=False)
            fig_bar = px.bar(by_person, x="Name", y="Minutes", title=f"ภาระงานรายบุคคล — {THAI_MONTHS[m_month]} {m_year}", color="Name", text="Minutes")
            fig_bar.add_hline(y=MONTHLY_FTE_MINUTES, line_dash="dash", annotation_text="1 FTE", line_color="#ef4444")
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        a_year = st.selectbox("ปี", sorted(df["Date"].dt.year.dropna().unique().astype(int), reverse=True))
        annual_df = df[df["Date"].dt.year == a_year]
        total_mins = annual_df["Minutes"].sum()
        fte_val = calc_fte(total_mins, ANNUAL_FTE_MINUTES)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📋 รายการทั้งหมด", f"{len(annual_df):,}")
        k2.metric("⏱️ นาทีรวม", f"{total_mins:,}")
        k3.metric("💼 FTE รายปี", f"{fte_val:.2f}")
        k4.metric("👥 กำลังคนที่ต้องการ", f"{math.ceil(fte_val)} คน")
        st.markdown(fte_html(total_mins, fte_val, period="รายปี"), unsafe_allow_html=True)

        if not annual_df.empty:
            col_left, col_right = st.columns(2)
            by_task = annual_df.groupby(["Task_No","Task_Name"])["Minutes"].sum().reset_index()
            by_task["Label"] = by_task["Task_No"].astype(str) + ". " + by_task["Task_Name"].str[:30] + "..."
            col_left.plotly_chart(px.pie(by_task, names="Label", values="Minutes", title="สัดส่วนตามงาน"), use_container_width=True)
            col_right.plotly_chart(px.pie(annual_df.groupby("Name")["Minutes"].sum().reset_index(), names="Name", values="Minutes", title="สัดส่วนตามบุคคล"), use_container_width=True)

# ── TAB 4: SETTINGS & EXPORT ─────────────────────────────────────────────────

elif tab_choice == "⚙️ จัดการข้อมูล & Export":
    st.markdown('<div class="section-header">⚙️ จัดการข้อมูล & Export</div>', unsafe_allow_html=True)

    st.subheader("👤 จัดการรายชื่อเจ้าหน้าที่")
    staff_list = load_staff_list()
    st.write("รายชื่อปัจจุบัน:", ", ".join(staff_list) if staff_list else "ยังไม่มีรายชื่อ")

    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("➕ เพิ่มชื่อใหม่", placeholder="กรอกชื่อ-นามสกุล")
        if st.button("เพิ่ม", type="primary"):
            if new_name.strip() in staff_list: st.warning("มีชื่อนี้อยู่แล้ว")
            elif add_staff(new_name.strip()): st.success("เพิ่มสำเร็จ"); st.rerun()

    with col2:
        if staff_list:
            del_name = st.selectbox("🗑️ ลบรายชื่อ", staff_list)
            if st.button("ลบ", type="secondary") and delete_staff(del_name): st.success("ลบสำเร็จ"); st.rerun()

    st.markdown("---")

    # ── WORD EXPORT SECTION ───────────────────────────────────────────────────
    st.subheader("📥 ออกรายงาน (Word Export)")
    st.write("สร้างไฟล์รายงาน .docx สรุปภาระงานสำหรับนำไปพิมพ์หรือรายงานผู้บังคับบัญชา")
    
    df_all = load_workload_logs()
    
    if df_all.empty:
        st.warning("ยังไม่มีข้อมูลภาระงานให้ Export")
    else:
        export_type = st.radio("เลือกรูปแบบรายงาน:", ["รายสัปดาห์ (ระบุวันที่)", "รายเดือน", "รายปี"], horizontal=True)
        
        df_export = pd.DataFrame()
        report_title = ""
        period_str = ""
        
        if export_type == "รายสัปดาห์ (ระบุวันที่)":
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                start_d = st.date_input("ตั้งแต่วันที่", value=date.today() - timedelta(days=7))
            with ex_col2:
                end_d = st.date_input("ถึงวันที่", value=date.today())
                
            df_export = df_all[(df_all['Date'].dt.date >= start_d) & (df_all['Date'].dt.date <= end_d)]
            report_title = "รายงานประจำสัปดาห์/กำหนดช่วงเวลา"
            period_str = f"{start_d.strftime('%d/%m/%Y')} ถึง {end_d.strftime('%d/%m/%Y')}"
            
        elif export_type == "รายเดือน":
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                ex_y = st.selectbox("ปี", sorted(df_all["Date"].dt.year.dropna().unique().astype(int), reverse=True), key="ex_m_y")
            with ex_col2:
                ex_m = st.selectbox("เดือน", list(range(1, 13)), format_func=lambda x: THAI_MONTHS[x], key="ex_m_m")
                
            df_export = df_all[(df_all['Date'].dt.year == ex_y) & (df_all['Date'].dt.month == ex_m)]
            report_title = "รายงานรายเดือน"
            period_str = f"เดือน {THAI_MONTHS[ex_m]} ปี {ex_y}"
            
        elif export_type == "รายปี":
            ex_y2 = st.selectbox("ปี", sorted(df_all["Date"].dt.year.dropna().unique().astype(int), reverse=True), key="ex_y_y")
            df_export = df_all[df_all['Date'].dt.year == ex_y2]
            report_title = "รายงานรายปี"
            period_str = f"ประจำปี {ex_y2}"

        if st.button("📄 สร้างไฟล์รายงาน Word", type="primary"):
            if df_export.empty:
                st.error("ไม่มีข้อมูลในช่วงเวลาที่เลือก")
            else:
                with st.spinner("กำลังสร้างเอกสาร..."):
                    word_bytes = generate_word_report(df_export, report_title, period_str)
                    st.success("สร้างเอกสารสำเร็จ! กรุณากดปุ่มด้านล่างเพื่อดาวน์โหลด")
                    st.download_button(
                        label="📥 ดาวน์โหลดไฟล์ Word (.docx)",
                        data=word_bytes,
                        file_name=f"Workload_Report_{datetime.now().strftime('%Y%m%d')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

    st.markdown("---")
    st.subheader("🔌 ทดสอบการเชื่อมต่อ API")
    if st.button("ทดสอบ"):
        try:
            r = requests.get(SCRIPT_URL, timeout=10)
            if r.status_code == 200 and "logs" in r.json(): st.success("✅ เชื่อมต่อ Google Apps Script สำเร็จ!")
            else: st.error("❌ การตอบกลับไม่ถูกต้อง")
        except Exception as e: st.error(f"Error: {e}")
