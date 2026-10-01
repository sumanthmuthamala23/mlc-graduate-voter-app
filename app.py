import streamlit as st
from pypdf import PdfReader
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import hashlib
import re
import os
import json
from datetime import datetime

st.set_page_config(page_title="MLC Graduate Voter Console", layout="wide", page_icon="🗳️")

DB_FILE = "mlc_users.db"
SHEET_ID = "1DiP4t2s3aUt_fOLEMjhGCy_nacXUhIfEl-y7kdV3WBU"

HEADERS = [
    "Timestamp", "Application ID", "Applicant Name", "Gender", 
    "Relation Name", "House Number", "Constituency", "Ack District", 
    "Ack Status", "Jurisdiction District", "Mandal", "Revenue Village / Ward", 
    "Reference Name", "Mobile Number", "Remarks", "Operator Username"
]

# --- LOCAL DATABASE & AUDIT LOG ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    full_name TEXT,
                    role TEXT,
                    status TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS duplicate_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    application_id TEXT,
                    applicant_name TEXT,
                    operator TEXT
                )''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        pwd_hash = hashlib.sha256("Admin@123".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES ('admin', ?, 'System Administrator', 'Admin', 'Approved')", (pwd_hash,))
    conn.commit()
    conn.close()

init_db()

# --- JURISDICTION HIERARCHY ---
JURISDICTION_DATA = {
    "Khammam": {
        "Khammam Urban": ["Khammam (M Corp)", "Khanapuram Haveli", "Dhamsalapuram", "Mallemadugu"],
        "Khammam Rural": ["Arempula", "Edulapuram", "Gollapadu", "Theldarupalli", "Maddulapalli"],
        "Kallur": ["Kallur", "Chinnakorukondi", "Peruvancha", "Lokavaram"],
        "Madhira": ["Madhira", "Dendukuru", "Mallaram", "Siripuram"],
        "Wyra": ["Wyra", "Somavaram", "Gannavaram", "Karamthota"],
        "Sathupalli": ["Sathupalli", "Gangaram", "Kistaram", "Rejarla"],
        "Nelakondapalli": ["Nelakondapalli", "Bodulabanda", "Kusumanchi"],
        "Thirumalayapalem": ["Thirumalayapalem", "Sublaid", "Errappaigudem"],
        "Enkoor": ["Enkoor", "Nacharam", "Timmapeta"],
        "Penuballi": ["Penuballi", "Karakavagu", "Lingagudem"]
    },
    "Bhadradri Kothagudem": {
        "Kothagudem": ["Kothagudem (M)", "Chunchupalli", "Garimellapadu"],
        "Palvancha": ["Palvancha (M)", "Ghanpur", "Ulvanuru"],
        "Bhadrachalam": ["Bhadrachalam", "Seethampeta", "Nellipaka"],
        "Manuguru": ["Manuguru", "Samithi Singaram", "Pagideru"],
        "Yellandu": ["Yellandu (M)", "Rompaid", "Sudimalla"],
        "Aswaraopeta": ["Aswaraopeta", "Vinayakapuram", "Gundlapadu"],
        "Burgampahad": ["Burgampahad", "Sarapaka", "Morampalli Banjara"]
    },
    "Nalgonda": {
        "Nalgonda": ["Nalgonda (M)", "Panagallu", "Arjalabavi", "Cherlapally"],
        "Miryalaguda": ["Miryalaguda (M)", "Alagadapa", "Chinthapalli"],
        "Devarakonda": ["Devarakonda", "Tatipole", "Kondabheemanapalli"],
        "Nakrekal": ["Nakrekal", "Chityala", "Nomula"],
        "Munugode": ["Munugode", "Kommaravelli", "Pulipalpula"]
    },
    "Suryapet": {
        "Suryapet": ["Suryapet (M)", "Kudakuda", "Pillalamarri", "Balaemla"],
        "Kodad": ["Kodad (M)", "Thogarrai", "Gudibanda"],
        "Huzurnagar": ["Huzurnagar (M)", "Burugugadda", "Macharam"],
        "Thungathurthi": ["Thungathurthi", "Gotta", "Annaram"]
    },
    "Yadadri Bhuvanagiri": {
        "Bhongir": ["Bhongir (M)", "Rayagiri", "Bolligudem"],
        "Alair": ["Alair", "Kolannur", "Shariefguda"],
        "Choutuppal": ["Choutuppal", "Lingojiguda", "Thallasingaram"],
        "Yadagirigutta": ["Yadagirigutta", "Gundlapally", "Saidapuram"]
    },
    "Hanamkonda": {
        "Hanamkonda": ["Hanamkonda (M Corp)", "Waddepally", "Lashkar Singaram"],
        "Kazipet": ["Kazipet", "Madikonda", "Bheemaram", "Kadipikonda"],
        "Kamalapur": ["Kamalapur", "Uppal", "Madannapet"],
        "Parkal": ["Parkal (M)", "Kammaripalli", "Nagaram"]
    },
    "Warangal": {
        "Warangal": ["Warangal (M Corp)", "Ursu", "Mamnoor", "Gorrekunta"],
        "Wardhannapet": ["Wardhannapet", "Bandautlapally", "Inavolu"],
        "Narsampet": ["Narsampet", "Rajupet", "Maheswaram"],
        "Geesugonda": ["Geesugonda", "Dharmaram", "Gorrekunta"]
    },
    "Jangaon": {
        "Jangaon": ["Jangaon (M)", "Yeshwanthapur", "Chowdaram"],
        "Station Ghanpur": ["Station Ghanpur", "Chagallu", "Shivunipally"],
        "Palakurthi": ["Palakurthi", "Valmidi", "Dharmathanda"]
    },
    "Mahabubabad": {
        "Mahabubabad": ["Mahabubabad (M)", "Bethole", "Kambalapally"],
        "Dornakal": ["Dornakal", "Chilkodu", "Ravigudem"],
        "Maripeda": ["Maripeda", "Neelikurthy", "Yellampeta"],
        "Kesamudram": ["Kesamudram", "Inugurthy", "Korukondapally"]
    },
    "Jayashankar Bhupalpally": {
        "Bhupalpally": ["Bhupalpally (M)", "Kompally", "Gorlaveedu"],
        "Chityal": ["Chityal", "Giddamutharam", "Jadalpalli"],
        "Regonda": ["Regonda", "Roopireddypally", "Kanakapoor"]
    },
    "Mulugu": {
        "Mulugu": ["Mulugu", "Bandaru", "Jaggannapet"],
        "Venkatapur": ["Venkatapur", "Palampet (Ramappa)", "Laxmipuram"],
        "Govindaraopet": ["Govindaraopet", "Pasra", "Chalvai"]
    }
}

# --- DUAL-MODE GOOGLE SHEETS CONNECTOR (LOCAL + STREAMLIT CLOUD) ---
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = None
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
    else:
        return None, "No service account credentials found. Configure service_account.json or Streamlit Secrets."

    try:
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SHEET_ID)
        sheet = spreadsheet.sheet1
        
        # Ensure header row exists
        existing_rows = sheet.get_all_values()
        if not existing_rows or existing_rows[0] != HEADERS:
            if not existing_rows:
                sheet.append_row(HEADERS)
            else:
                sheet.insert_row(HEADERS, index=1)
        return sheet, None
    except Exception as e:
        return None, str(e)

# --- PDF PARSING ENGINE ---
def parse_acknowledgement_pdf(file_obj):
    reader = PdfReader(file_obj)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"

    patterns = {
        "application_id": r"Application\s*Id\s*[:\|\-]?\s*([A-Z0-9]+)",
        "applicant_name": r"Applicant\s*Name\s*[:\|\-]?\s*([A-Za-z\s\.]+?)(?=\n|Gender|Relation|$)",
        "gender": r"Gender\s*[:\|\-]?\s*([A-Za-z]+)",
        "relation_name": r"Relation\s*Name\s*[:\|\-]?\s*([A-Za-z\s\.]+?)(?=\n|House|Gender|$)",
        "house_number": r"House\s*Number\s*[:\|\-]?\s*([A-Za-z0-9\-\/\$\s]+?)(?=\n|Mlc|District|$)",
        "mlc_constituency": r"(?:Mlc|Constituency)\s*Name\s*[:\|\-]?\s*([A-Za-z\-\s]+?)(?=\n|District|$)",
        "district_name": r"District\s*Name\s*[:\|\-]?\s*([A-Za-z\s]+?)(?=\n|Current|Status|$)",
        "current_status": r"Current\s*Status\s*[:\|\-]?\s*([A-Za-z0-9\s\.]+?)(?=\n|Print|Exit|$)"
    }

    parsed = {}
    for key, regex in patterns.items():
        match = re.search(regex, text, re.IGNORECASE)
        val = match.group(1).strip() if match else ""
        val = val.replace("$", "").strip()
        parsed[key] = val

    return parsed

# --- USER AUTHENTICATION HELPERS ---
def verify_user(username, password):
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT full_name, role, status FROM users WHERE username = ? AND password_hash = ?", (username, pwd_hash))
    user = c.fetchone()
    conn.close()
    return user

def register_user(username, password, full_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, 'Staff', 'Pending')", (username, pwd_hash, full_name))
        conn.commit()
        conn.close()
        return True, "Registration successful! Awaiting Admin approval."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists."

def log_duplicate(app_id, name, operator):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO duplicate_audit (timestamp, application_id, applicant_name, operator) VALUES (?, ?, ?, ?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app_id, name, operator))
    conn.commit()
    conn.close()

# --- SESSION INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.full_name = None

if not st.session_state.logged_in:
    st.title("🗳️ MLC Graduate Applications Desk")
    st.caption("Warangal–Khammam–Nalgonda Graduate Constituency Portal")
    
    tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Staff Registration"])
    
    with tab1:
        with st.form("login_form"):
            uname = st.text_input("Username")
            pword = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In", use_container_width=True)
            if submit:
                user_info = verify_user(uname, pword)
                if user_info:
                    fname, role, status = user_info
                    if status != "Approved":
                        st.error("⏳ Account is pending approval by the Admin.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.username = uname
                        st.session_state.role = role
                        st.session_state.full_name = fname
                        st.rerun()
                else:
                    st.error("Invalid Username or Password.")

    with tab2:
        with st.form("register_form"):
            new_name = st.text_input("Full Name")
            new_uname = st.text_input("Desired Username")
            new_pwd = st.text_input("Password", type="password")
            reg_submit = st.form_submit_button("Submit Registration", use_container_width=True)
            if reg_submit:
                if not new_uname or not new_pwd or not new_name:
                    st.warning("All fields are required.")
                else:
                    ok, msg = register_user(new_uname, new_pwd, new_name)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()

# --- SIDEBAR & USER CONTROLS ---
with st.sidebar:
    st.markdown(f"**Operator:** {st.session_state.full_name}")
    st.markdown(f"**Role:** `{st.session_state.role}`")
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()

    if st.session_state.role == "Admin":
        st.subheader("👥 User Approvals")
        conn = sqlite3.connect(DB_FILE)
        users_df = pd.read_sql_query("SELECT username, full_name, role, status FROM users", conn)
        conn.close()
        
        pending_users = users_df[users_df["status"] == "Pending"]
        if not pending_users.empty:
            for _, row in pending_users.iterrows():
                col1, col2 = st.columns([2, 1])
                col1.caption(f"{row['full_name']} (`{row['username']}`)")
                if col2.button("Approve", key=f"app_{row['username']}"):
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("UPDATE users SET status = 'Approved' WHERE username = ?", (row['username'],))
                    conn.commit()
                    conn.close()
                    st.rerun()
        else:
            st.caption("No pending registrations.")

# --- NAVIGATION TABS ---
if st.session_state.role == "Admin":
    main_tab1, main_tab2 = st.tabs(["📥 Data Entry & PDF Consolidation", "📊 Admin Analytics & Mandal Breakdown"])
else:
    main_tab1 = st.container()

# ==============================================================================
# TAB 1: FORM-18 ENTRY
# ==============================================================================
with main_tab1:
    st.title("Consolidate Form-18 Graduate Votes")
    upload_col, data_col = st.columns([1, 1.2], gap="large")

    with upload_col:
        st.subheader("1. Attach Form-18 Slip")
        uploaded_pdf = st.file_uploader("Upload CEO Telangana Form-18 PDF", type=["pdf"])

        extracted = {
            "application_id": "", "applicant_name": "", "gender": "",
            "relation_name": "", "house_number": "", "mlc_constituency": "",
            "district_name": "", "current_status": ""
        }

        if uploaded_pdf is not None:
            extracted = parse_acknowledgement_pdf(uploaded_pdf)
            st.success("✅ Acknowledgment Form parsed successfully!")

    with data_col:
        st.subheader("2. Review & Tag Jurisdiction Details")

        with st.form("voter_entry_form"):
            st.markdown("##### Extracted Voter Details")
            c1, c2 = st.columns(2)
            app_id = c1.text_input("Application ID", value=extracted["application_id"])
            name = c2.text_input("Applicant Name", value=extracted["applicant_name"])

            c3, c4, c5 = st.columns(3)
            gender = c3.text_input("Gender", value=extracted["gender"])
            relation = c4.text_input("Relation Name", value=extracted["relation_name"])
            house_no = c5.text_input("House Number", value=extracted["house_number"])

            c6, c7 = st.columns(2)
            mlc_const = c6.text_input("Constituency", value=extracted["mlc_constituency"] or "Warangal-Khammam-Nalgonda")
            status = c7.text_input("Status", value=extracted["current_status"])

            st.markdown("---")
            st.markdown("##### Ordinary Residence Jurisdiction (MLC Limits)")
            
            all_districts = list(JURISDICTION_DATA.keys())
            default_dist_idx = all_districts.index(extracted["district_name"]) if extracted["district_name"] in all_districts else 0

            selected_district = st.selectbox("Select District", all_districts, index=default_dist_idx)
            available_mandals = list(JURISDICTION_DATA[selected_district].keys())
            selected_mandal = st.selectbox("Select Mandal", available_mandals)
            
            available_villages = JURISDICTION_DATA[selected_district][selected_mandal] + ["Other / Unlisted"]
            selected_village = st.selectbox("Select Revenue Village / Ward", available_villages)
            
            if selected_village == "Other / Unlisted":
                final_village = st.text_input("Enter Revenue Village Name")
            else:
                final_village = selected_village

            st.markdown("---")
            st.markdown("##### Reference & Contact Details")
            r1, r2 = st.columns(2)
            ref_name = r1.text_input("Reference Name", value="Sumanth Muthamala", placeholder="e.g., Local Leader / Volunteer")
            mobile_no = r2.text_input("Mobile Number", placeholder="10-digit number")
            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Certificate verified, Ward 4 booth")

            save_btn = st.form_submit_button("💾 Save & Feed to Google Sheet", use_container_width=True)

            if save_btn:
                if not app_id or not name:
                    st.error("Application ID and Applicant Name are mandatory.")
                else:
                    ws, err = get_worksheet()
                    if ws is None:
                        st.error(f"Google Sheet Connection Failed: {err}")
                    else:
                        try:
                            rows = ws.get_all_values()
                            header_row = rows[0] if rows else HEADERS
                            idx = header_row.index("Application ID") if "Application ID" in header_row else 1
                            existing_ids = [r[idx] for r in rows[1:] if len(r) > idx]

                            if app_id in existing_ids:
                                log_duplicate(app_id, name, st.session_state.username)
                                st.warning(f"⚠️ Application ID {app_id} already exists in Google Sheet. Submission blocked and recorded in duplicate counter.")
                            else:
                                new_entry = [
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    app_id, name, gender, relation, house_no,
                                    mlc_const, extracted["district_name"], status,
                                    selected_district, selected_mandal, final_village,
                                    ref_name, mobile_no, remarks, st.session_state.username
                                ]
                                ws.append_row(new_entry)
                                st.success(f"🎉 Successfully saved record for {name} ({app_id}) to Google Sheet!")
                        except Exception as ex:
                            st.error(f"Error appending row: {ex}")

# ==============================================================================
# TAB 2: ADMIN ANALYTICS & MANDAL-WISE BREAKDOWN
# ==============================================================================
if st.session_state.role == "Admin":
    with main_tab2:
        st.title("📊 MLC Graduate Ingestion Dashboard")
        st.caption("Consolidated analytics from Google Sheets and live duplicate counter")

        ws, err = get_worksheet()
        if ws is None:
            st.error(f"Cannot load live analytics: {err}")
        else:
            try:
                sheet_data = ws.get_all_values()
                if len(sheet_data) <= 1:
                    st.info("No applications recorded in Google Sheets yet.")
                else:
                    df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

                    # Fetch Duplicate Log
                    conn = sqlite3.connect(DB_FILE)
                    dup_df = pd.read_sql_query("SELECT * FROM duplicate_audit ORDER BY id DESC", conn)
                    conn.close()

                    # Top KPI Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    total_votes = len(df)
                    unique_voters = df["Application ID"].nunique() if "Application ID" in df.columns else total_votes
                    duplicate_attempts = len(dup_df)
                    active_operators = df["Operator Username"].nunique() if "Operator Username" in df.columns else 1

                    m1.metric("Total Votes Ingested", f"{total_votes:,}")
                    m2.metric("Unique Voters", f"{unique_voters:,}")
                    m3.metric("Duplicates Prevented", f"{duplicate_attempts:,}")
                    m4.metric("Active Operators", f"{active_operators}")

                    st.divider()

                    # Mandal Breakdown Controls
                    st.subheader("📍 Jurisdiction Breakdown")
                    d_col1, d_col2 = st.columns([1, 2])

                    with d_col1:
                        dist_filter = st.selectbox(
                            "Filter by Tagged District",
                            ["All Districts"] + sorted(list(df["Jurisdiction District"].dropna().unique()))
                        )

                    filtered_df = df if dist_filter == "All Districts" else df[df["Jurisdiction District"] == dist_filter]

                    if "Mandal" in filtered_df.columns and not filtered_df.empty:
                        mandal_counts = filtered_df["Mandal"].value_counts().reset_index()
                        mandal_counts.columns = ["Mandal", "Total Votes Ingested"]

                        t_col, c_col = st.columns([1, 1.4])
                        with t_col:
                            st.write(f"**Mandal Summary ({dist_filter})**")
                            st.dataframe(mandal_counts, use_container_width=True, hide_index=True)
                        with c_col:
                            st.write(f"**Vote Distribution by Mandal**")
                            st.bar_chart(mandal_counts.set_index("Mandal"))

                    st.divider()

                    # Duplicate Audit Log
                    st.subheader("🚨 Live Duplicate Counter & Audit Trail")
                    if not dup_df.empty:
                        st.dataframe(
                            dup_df[["timestamp", "application_id", "applicant_name", "operator"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.caption("No duplicate entry attempts logged yet.")

                    # Recent Submissions Viewer
                    with st.expander("📄 View Latest 50 Ingested Records"):
                        st.dataframe(df.tail(50), use_container_width=True)

            except Exception as e:
                st.error(f"Error computing dashboard analytics: {e}")
