import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import math
import io
import json
from datetime import datetime, date, timedelta
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

# ⚠️ วาง Web app URL ของคุณตรงนี้
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

# ── PAGE CONFIG & STYLE ───────────────────────────────────────────────────────

st.set_page_config(page_title="Medical Physicist Workload", page_icon="⚛️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f2027 0%, #203a43 50%, #2c5364 100%); }
    .section-header { background: linear-gradient(90deg, #0284c7, #0ea5e9); color: white; padding: 10px 18px; border-radius: 8px; margin: 16px 0; font-weight: 700; }
    .fte-box { background: linear-gradient(135deg, #0f2027, #2c5364); color: #bae6fd; padding: 20px; border-radius: 12px; text-align: center; }
    .fte-box span.big { font-size: 2.2rem; color: #38bdf8; font-weight: 700; }
    .success-banner { background: #dcfce7; color: #15803d; border-left: 4px solid #16a34a; padding: 10px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def format_gas_time(time_val):
    """แก้ปัญหาปี 1899: แปลงเวลาจาก GAS ให้เหลือแค่ HH:mm"""
    if not time_val or time_val == "-": return "-"
    time_str = str(time_val)
    if "T" in time_str:
        return time_str.split("T")[1][:5]
    return time_str

@st.cache_data(ttl=60)
def fetch_all_data():
    try:
        r = requests.get(SCRIPT_URL, timeout=15)
        return r.json() if r.status_code == 200 else {"logs": [], "staff": [], "error": "HTTP Error"}
    except Exception as e:
        return {"logs": [], "staff": [], "error": str(e)}

def invalidate_cache():
    fetch_all_data.clear()

def generate_word_report(df_report, report_type, period_text):
    """สร้างไฟล์ Word พร้อมแก้เวลาไทยและล้างปี 1899"""
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Sarabun'
    style.font.size = Pt(14)
    
    heading = doc.add_heading('รายงานสรุปภาระงาน (Workload Report)', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"หน่วยงาน: สาขารังสีวินิจฉัย โรงพยาบาลสงขลานครินทร์")
    doc.add_paragraph(f"ประเภทรายงาน: {report_type}")
    doc.add_paragraph(f"ช่วงเวลาที่รายงาน: {period_text}")
    
    # ปรับเวลาไทย (+7 ชม.)
    thai_now = datetime.now() + timedelta(hours=7)
    doc.add_paragraph(f"วันที่พิมพ์รายงาน: {thai_now.strftime('%d/%m/%Y %H:%M')}")
    
    total_mins = df_report["Minutes"].sum()
    fte = round(total_mins / (ANNUAL_FTE_MINUTES if "ปี" in report_type else MONTHLY_FTE_MINUTES), 2)
    doc.add_paragraph(f"สรุปผลรวม: ใช้เวลาปฏิบัติงานทั้งหมด {total_mins:,.0f} นาที (คิดเป็น {fte} FTE)")
    
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, txt in enumerate(['วันที่', 'เวลา', 'ผู้ปฏิบัติงาน', 'ชื่องาน', 'นาที']):
        hdr_cells[i].text = txt

    for _, row in df_report.sort_values(by="Date").iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = row['Date'].strftime('%d/%m/%Y') if pd.notnull(row['Date']) else '-'
        s_time = format_gas_time(row.get('Start_Time', '-'))
        e_time = format_gas_time(row.get('End_Time', '-'))
        row_cells[1].text = f"{s_time} - {e_time}" if s_time != "-" else "-"
        row_cells[2].text = str(row['Name'])
        row_cells[3].text = f"{row['Task_No']}. {str(row['Task_Name'])[:40]}..."
        row_cells[4].text = f"{row['Minutes']:,}"
        
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ── MAIN APPLICATION ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚛️ Medical Physicist\n### Workload Manager")
    st.markdown("---")
    tab_choice = st.radio("เมนูหลัก", ["📝 บันทึกภาระงาน", "📅 ประวัติงาน", "📊 Dashboard", "⚙️ ออกรายงาน & จัดการข้อมูล"])
    st.markdown("---")
    st.caption("v1.4 — Production Ready")

data = fetch_all_data()
staff_list = data.get("staff", [])
logs_raw = data.get("logs", [])
df = pd.DataFrame(logs_raw)

if not df.empty:
    df["Minutes"] = pd.to_numeric(df["Minutes"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# ── TAB: DATA ENTRY ───────────────────────────────────────────────────────────

if tab_choice == "📝 บันทึกภาระงาน":
    st.markdown('<div class="section-header">📝 บันทึกภาระงานประจำวัน</div>', unsafe_allow_html=True)
    if not staff_list: st.warning("กรุณาเพิ่มชื่อเจ้าหน้าที่ก่อน"); st.stop()

    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            entry_date = st.date_input("วันที่ปฏิบัติงาน", value=date.today())
            entry_name = st.selectbox("ชื่อผู้ปฏิบัติงาน", options=staff_list)
            entry_details = st.text_input("รายละเอียดเพิ่มเติม")
        with c2:
            entry_task = st.selectbox("รายการงาน", options=TASK_LABELS)
            tc1, tc2 = st.columns(2)
            with tc1: s_time = st.time_input("เวลาเริ่ม", value=datetime.strptime("08:30", "%H:%M").time())
            with tc2: e_time = st.time_input("เวลาสิ้นสุด", value=datetime.strptime("09:00", "%H:%M").time())
        
        if st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True, type="primary"):
            dt_s, dt_e = datetime.combine(entry_date, s_time), datetime.combine(entry_date, e_time)
            if dt_e < dt_s: dt_e += timedelta(days=1)
            mins = int((dt_e - dt_s).total_seconds() / 60)
            
            payload = {
                "action": "append_log",
                "data": [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(entry_date), entry_name, 
                         TASK_NO_FROM_LABEL[entry_task], TASKS[TASK_NO_FROM_LABEL[entry_task]], 
                         entry_details, mins, s_time.strftime("%H:%M"), e_time.strftime("%H:%M")]
            }
            if requests.post(SCRIPT_URL, json=payload).status_code in [200, 302]:
                st.success(f"บันทึกสำเร็จ! ใช้เวลา {mins} นาที"); invalidate_cache(); st.rerun()

# ── TAB: HISTORY ──────────────────────────────────────────────────────────────

elif tab_choice == "📅 ประวัติงาน":
    st.markdown('<div class="section-header">📅 รายการภาระงานย้อนหลัง</div>', unsafe_allow_html=True)
    if df.empty: st.info("ยังไม่มีข้อมูล"); st.stop()
    
    # แสดงตาราง
    temp_df = df.copy()
    temp_df["Time"] = temp_df.apply(lambda x: f"{format_gas_time(x.get('Start_Time','-'))} - {format_gas_time(x.get('End_Time','-'))}", axis=1)
    view_df = temp_df[["Date", "Time", "Name", "Task_Name", "Minutes"]]
    st.dataframe(view_df, use_container_width=True)

# ── TAB: DASHBOARD ────────────────────────────────────────────────────────────

elif tab_choice == "📊 Dashboard":
    st.markdown('<div class="section-header">📊 วิเคราะห์ภาพรวมและ FTE</div>', unsafe_allow_html=True)
    if df.empty: st.info("ไม่มีข้อมูล"); st.stop()
    
    m_year = st.selectbox("เลือกปี", sorted(df["Date"].dt.year.unique(), reverse=True))
    m_month = st.selectbox("เลือกเดือน", list(range(1, 13)), format_func=lambda x: THAI_MONTHS[x])
    
    m_df = df[(df["Date"].dt.year == m_year) & (df["Date"].dt.month == m_month)]
    total = m_df["Minutes"].sum()
    fte = round(total/8750, 2)
    
    st.markdown(f'<div class="fte-box">เดือน{THAI_MONTHS[m_month]} : <span class="big">{fte}</span> FTE ({total:,.0f} นาที)</div>', unsafe_allow_html=True)
    
    if not m_df.empty:
        st.plotly_chart(px.bar(m_df.groupby("Name")["Minutes"].sum().reset_index(), x="Name", y="Minutes", title="รายบุคคล"), use_container_width=True)

# ── TAB: EXPORT & SETTINGS ────────────────────────────────────────────────────

elif tab_choice == "⚙️ ออกรายงาน & จัดการข้อมูล":
    st.markdown('<div class="section-header">⚙️ จัดการข้อมูล & ส่งออกรายงาน Word</div>', unsafe_allow_html=True)
    
    # ส่วนเพิ่ม/ลบชื่อ (เหมือนเดิม)
    st.subheader("👤 จัดการรายชื่อ")
    new_n = st.text_input("ชื่อ-นามสกุลใหม่")
    if st.button("เพิ่มชื่อ") and new_n:
        if requests.post(SCRIPT_URL, json={"action": "add_staff", "name": new_n}).status_code in [200, 302]:
            st.success("เพิ่มแล้ว"); invalidate_cache(); st.rerun()

    st.markdown("---")
    
    # ส่วนออกรายงาน Word
    st.subheader("📥 ดาวน์โหลดรายงาน (.docx)")
    rep_type = st.radio("ประเภท:", ["รายสัปดาห์/ระบุช่วงเวลา", "รายเดือน", "รายปี"], horizontal=True)
    
    if not df.empty:
        d_export = pd.DataFrame()
        title, period = "", ""
        
        if "สัปดาห์" in rep_type:
            sd = st.date_input("เริ่ม", value=date.today()-timedelta(7))
            ed = st.date_input("สิ้นสุด", value=date.today())
            d_export = df[(df['Date'].dt.date >= sd) & (df['Date'].dt.date <= ed)]
            title, period = "รายงานรายสัปดาห์", f"{sd.strftime('%d/%m/%Y')} - {ed.strftime('%d/%m/%Y')}"
        elif "เดือน" in rep_type:
            ey = st.selectbox("ปี", sorted(df["Date"].dt.year.unique(), reverse=True), key="ey")
            em = st.selectbox("เดือน", list(range(1,13)), format_func=lambda x: THAI_MONTHS[x], key="em")
            d_export = df[(df['Date'].dt.year == ey) & (df['Date'].dt.month == em)]
            title, period = "รายงานรายเดือน", f"{THAI_MONTHS[em]} {ey}"
        else:
            ey2 = st.selectbox("ปี", sorted(df["Date"].dt.year.unique(), reverse=True), key="ey2")
            d_export = df[df['Date'].dt.year == ey2]
            title, period = "รายงานรายปี", f"พ.ศ. {ey2 + 543}"

        if st.button("📄 สร้างไฟล์ Word"):
            if d_export.empty: st.error("ไม่พบข้อมูลในช่วงที่เลือก")
            else:
                word_file = generate_word_report(d_export, title, period)
                st.download_button("📥 คลิกเพื่อดาวน์โหลดไฟล์ Word", word_file, f"Workload_{period}.docx")
