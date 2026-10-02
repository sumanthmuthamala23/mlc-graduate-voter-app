import streamlit as st
from pypdf import PdfReader
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import hashlib
import re
import os
import base64
from datetime import datetime

st.set_page_config(
    page_title="BRS | Warangal-Khammam-Nalgonda MLC Console",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- EMBEDDED LOGO DATA LOADER ---
def get_logo_path():
    for filename in ["brs_logo.webp", "brs_logo.jpg", "brs_logo.png"]:
        if os.path.exists(filename):
            return filename
    return None

logo_path = get_logo_path()

# --- BRS THEME CLEAN STYLING ---
st.markdown("""
<style>
    .stApp {
        background-color: #FFF6FA !important;
    }

    /* Top Banner Header */
    .brs-banner {
        background: linear-gradient(90deg, #E61A8D 0%, #C2185B 100%);
        color: white !important;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(230, 26, 141, 0.25);
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .brs-car-badge {
        font-size: 34px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 4px 10px;
    }
    .brs-banner h1 {
        color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }
    .brs-banner p {
        color: #FCE4EC !important;
        font-size: 13px !important;
        margin: 2px 0 0 0 !important;
    }

    /* Clean Card Form */
    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #F5B6CE !important;
        border-radius: 14px !important;
        padding: 24px !important;
        box-shadow: 0 8px 24px rgba(230, 26, 141, 0.10) !important;
    }

    /* Inputs */
    .stTextInput input {
        background-color: #FAFAFC !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 8px 12px !important;
    }
    .stTextInput input:focus {
        border-color: #E61A8D !important;
        box-shadow: 0 0 0 2px rgba(230, 26, 141, 0.2) !important;
    }

    /* Primary BRS Button */
    div.stButton > button:first-child, div.stFormSubmitButton > button:first-child {
        background: linear-gradient(90deg, #E61A8D 0%, #D81B60 100%) !important;
        color: white !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 12px rgba(216, 27, 96, 0.3) !important;
    }
    div.stButton > button:first-child:hover, div.stFormSubmitButton > button:first-child:hover {
        background: linear-gradient(90deg, #C2185B 0%, #AD1457 100%) !important;
    }

    /* Info Instructions Box placed cleanly below Sign In */
    .info-card {
        background: #FFFFFF;
        border-left: 4px solid #E61A8D;
        border-radius: 10px;
        padding: 16px 20px;
        margin-top: 20px;
        box-shadow: 0 4px 14px rgba(230, 26, 141, 0.08);
    }
    .info-card h4 {
        color: #C2185B !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        margin: 0 0 6px 0 !important;
    }
    .info-card p {
        color: #334155 !important;
        font-size: 13.5px !important;
        line-height: 1.5 !important;
        margin: 0 0 6px 0 !important;
    }

    /* Tab Highlights */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #64748B !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #E61A8D !important;
        border-bottom: 3px solid #E61A8D !important;
        font-weight: 800 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFF7FA !important;
        border-right: 1.5px solid #F8BBD0 !important;
    }

    /* KPI Metrics */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border-left: 5px solid #E61A8D;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 10px rgba(230, 26, 141, 0.08);
    }
    div[data-testid="stMetricValue"] {
        color: #C2185B !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "mlc_users.db"
SHEET_ID = "1DiP4t2s3aUt_fOLEMjhGCy_nacXUhIfEl-y7kdV3WBU"

HEADERS = [
    "Timestamp", "Application ID", "Applicant Name", "Gender", 
    "Relation Name", "House Number", "Constituency", "Ack District", 
    "Ack Status", "Jurisdiction District", "Mandal", "Revenue Village / Ward", 
    "Reference Name", "Mobile Number", "Remarks", "Operator Username"
]

def render_banner(title="BRS MLC GRADUATE VOTER CONSOLE", sub="Warangal – Khammam – Nalgonda Graduate Constituency Portal | War Room System"):
    st.markdown(f"""
    <div class="brs-banner">
        <div class="brs-car-badge">🚗</div>
        <div>
            <h1>{title}</h1>
            <p>{sub}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- DATABASE SETUP ---
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
        c.execute("INSERT INTO users VALUES ('admin', ?, 'BRS Central War Room', 'Admin', 'Approved')", (pwd_hash,))
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

# --- GOOGLE SHEETS CONNECTOR (LOCAL + CLOUD) ---
def get_worksheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = None
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
    else:
        return None, "Missing credentials file or Streamlit Cloud Secrets."

    try:
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID).sheet1
        rows = sh.get_all_values()
        if not rows or rows[0] != HEADERS:
            if not rows:
                sh.append_row(HEADERS)
            else:
                sh.insert_row(HEADERS, index=1)
        return sh, None
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
        parsed[key] = val.replace("$", "").strip()

    return parsed

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
        return True, "Registration successful! Awaiting War Room approval."
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

# --- AUTH STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.full_name = None

# ==============================================================================
# LOGIN SCREEN: LOGO ON LEFT (CLEAN), FORM & WORDS ON RIGHT
# ==============================================================================
if not st.session_state.logged_in:
    render_banner()

    col_logo, col_form = st.columns([1, 1.25], gap="large")

    with col_logo:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown("<div style='font-size:120px; text-align:center;'>🚗</div>", unsafe_allow_html=True)

    with col_form:
        tab1, tab2 = st.tabs(["🔑 War Room Sign In", "📝 Volunteer Registration"])

        with tab1:
            with st.form("login_form"):
                uname = st.text_input("Username", placeholder="e.g. admin")
                pword = st.text_input("Password", type="password", placeholder="Enter password")
                submit = st.form_submit_button("Sign In to Console", use_container_width=True)
                if submit:
                    user_info = verify_user(uname, pword)
                    if user_info:
                        fname, role, status = user_info
                        if status != "Approved":
                            st.error("⏳ Account pending War Room Admin approval.")
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
                new_name = st.text_input("Full Name", placeholder="Your Full Name")
                new_uname = st.text_input("Desired Username", placeholder="Choose username")
                new_pwd = st.text_input("Password", type="password", placeholder="Create password")
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

        # Clear, formatted text placed directly bottom of the Sign In box
        st.markdown("""
        <div class="info-card">
            <h4>🌸 భారత రాష్ట్ర సమితి (BRS) — War Room Console</h4>
            <p><strong>Warangal – Khammam – Nalgonda Graduate MLC Constituency</strong></p>
            <p style="color: #475569;">
                📌 <strong>Welcome to the Central Voter Intake Portal:</strong><br>
                Authorized War Room Operators and Volunteers can log in to upload CEO Telangana Form-18 verification slips and synchronize voter records directly to the constituency database.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ==============================================================================
# AUTHENTICATED WORKSPACE
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <span style="font-size:24px;">🚗</span>
        <h3 style="margin:0; color:#E61A8D;">BRS War Room</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**Operator:** {st.session_state.full_name}")
    st.markdown(f"**Role:** `{st.session_state.role}`")
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()

    if st.session_state.role == "Admin":
        st.subheader("👥 Volunteer Approvals")
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

render_banner("BRS MLC GRADUATE VOTER CONSOLE", "Consolidating Form-18 Applications | Warangal – Khammam – Nalgonda (కారు గుర్తుకే మన ఓటు)")

if st.session_state.role == "Admin":
    main_tab1, main_tab2 = st.tabs(["📥 Data Ingestion & Form-18 Processing", "📊 War Room Analytics & Mandal Breakdown"])
else:
    main_tab1 = st.container()

# TAB 1: FORM-18 ENTRY
with main_tab1:
    upload_col, data_col = st.columns([1, 1.25], gap="large")

    with upload_col:
        st.markdown("#### 1. Attach Form-18 PDF")
        uploaded_pdf = st.file_uploader("Upload CEO Telangana Form-18 PDF", type=["pdf"])

        extracted = {
            "application_id": "", "applicant_name": "", "gender": "",
            "relation_name": "", "house_number": "", "mlc_constituency": "",
            "district_name": "", "current_status": ""
        }

        if uploaded_pdf is not None:
            extracted = parse_acknowledgement_pdf(uploaded_pdf)
            st.success("✅ Form-18 Slip Extracted Successfully!")

    with data_col:
        st.markdown("#### 2. Review & Tag Jurisdiction Details")

        with st.form("voter_entry_form"):
            st.markdown("##### 👤 Applicant Information")
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
            st.markdown("##### 📍 Tag Jurisdiction (MLC Limits)")
            
            all_districts = list(JURISDICTION_DATA.keys())
            default_dist_idx = all_districts.index(extracted["district_name"]) if extracted["district_name"] in all_districts else 0

            selected_district = st.selectbox("Select District", all_districts, index=default_dist_idx)
            available_mandals = list(JURISDICTION_DATA[selected_district].keys())
            selected_mandal = st.selectbox("Select Mandal", available_mandals)
            
            available_villages = JURISDICTION_DATA[selected_district][selected_mandal] + ["Other / Unlisted"]
            selected_village = st.selectbox("Select Revenue Village / Ward", available_villages)
            final_village = st.text_input("Enter Revenue Village Name") if selected_village == "Other / Unlisted" else selected_village

            st.markdown("---")
            st.markdown("##### 🤝 Party Volunteer & Reference Details")
            r1, r2 = st.columns(2)
            ref_name = r1.text_input("Party Reference / Cadre Name", value="", placeholder="Enter Reference / Mandal Incharge Name")
            mobile_no = r2.text_input("Voter Mobile Number", placeholder="10-digit number")
            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Degree Certificate verified, BRS party supporter")

            save_btn = st.form_submit_button("🚗 Save & Submit to BRS Voter Database", use_container_width=True)

            if save_btn:
                if not app_id or not name:
                    st.error("Application ID and Applicant Name are mandatory.")
                else:
                    ws, err = get_worksheet()
                    if ws is None:
                        st.error(f"Database Connection Failed: {err}")
                    else:
                        try:
                            rows = ws.get_all_values()
                            header_row = rows[0] if rows else HEADERS
                            idx = header_row.index("Application ID") if "Application ID" in header_row else 1
                            existing_ids = [r[idx] for r in rows[1:] if len(r) > idx]

                            if app_id in existing_ids:
                                log_duplicate(app_id, name, st.session_state.username)
                                st.warning(f"⚠️ Duplicate Detected! Application ID {app_id} already exists in database. Logged in audit trail.")
                            else:
                                new_entry = [
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    app_id, name, gender, relation, house_no,
                                    mlc_const, extracted["district_name"], status,
                                    selected_district, selected_mandal, final_village,
                                    ref_name, mobile_no, remarks, st.session_state.username
                                ]
                                ws.append_row(new_entry)
                                st.success(f"🎉 Successfully Ingested: {name} ({app_id}) to BRS Central Records!")
                        except Exception as ex:
                            st.error(f"Error appending row: {ex}")

# TAB 2: WAR ROOM ANALYTICS
if st.session_state.role == "Admin":
    with main_tab2:
        st.markdown("### 📊 Constituency Consolidation Dashboard")

        ws, err = get_worksheet()
        if ws is None:
            st.error(f"Cannot load live analytics: {err}")
        else:
            try:
                sheet_data = ws.get_all_values()
                if len(sheet_data) <= 1:
                    st.info("No applications recorded yet.")
                else:
                    df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

                    conn = sqlite3.connect(DB_FILE)
                    dup_df = pd.read_sql_query("SELECT * FROM duplicate_audit ORDER BY id DESC", conn)
                    conn.close()

                    m1, m2, m3, m4 = st.columns(4)
                    total_votes = len(df)
                    unique_voters = df["Application ID"].nunique() if "Application ID" in df.columns else total_votes
                    duplicate_attempts = len(dup_df)
                    active_operators = df["Operator Username"].nunique() if "Operator Username" in df.columns else 1

                    m1.metric("Total Ingested Votes", f"{total_votes:,}")
                    m2.metric("Unique Verified Voters", f"{unique_voters:,}")
                    m3.metric("Duplicates Filtered", f"{duplicate_attempts:,}")
                    m4.metric("Active War Room Cadre", f"{active_operators}")

                    st.divider()

                    st.subheader("📍 Mandal-Wise Mobilization Breakdown")
                    d_col1, _ = st.columns([1, 2])

                    with d_col1:
                        dist_filter = st.selectbox(
                            "Filter by Revenue District",
                            ["All Districts"] + sorted(list(df["Jurisdiction District"].dropna().unique()))
                        )

                    filtered_df = df if dist_filter == "All Districts" else df[df["Jurisdiction District"] == dist_filter]

                    if "Mandal" in filtered_df.columns and not filtered_df.empty:
                        mandal_counts = filtered_df["Mandal"].value_counts().reset_index()
                        mandal_counts.columns = ["Mandal", "Total Ingested Votes"]

                        t_col, c_col = st.columns([1, 1.4])
                        with t_col:
                            st.write(f"**Mandal Summary ({dist_filter})**")
                            st.dataframe(mandal_counts, use_container_width=True, hide_index=True)
                        with c_col:
                            st.write(f"**Mandal Distribution Chart**")
                            st.bar_chart(mandal_counts.set_index("Mandal"), color="#E61A8D")

                    st.divider()

                    st.subheader("🚨 Live Duplicate Submissions Log")
                    if not dup_df.empty:
                        st.dataframe(
                            dup_df[["timestamp", "application_id", "applicant_name", "operator"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.caption("Zero duplicate attempts recorded so far.")

                    with st.expander("📄 View Latest 50 Ingested Voter Records"):
                        st.dataframe(df.tail(50), use_container_width=True)

            except Exception as e:
                st.error(f"Error computing dashboard analytics: {e}")
