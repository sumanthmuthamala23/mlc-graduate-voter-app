import streamlit as st
from pypdf import PdfReader
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import hashlib
import re
import os
import io
from datetime import datetime

st.set_page_config(
    page_title="BRS | Warangal-Khammam-Nalgonda MLC Console",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Locate poster image if available
def get_banner_image():
    for filename in ["brs_banner_bg.png", "1461945.png", "brs_banner_bg.jpg", "brs_logo.webp", "brs_logo.jpg"]:
        if os.path.exists(filename):
            return filename
    return None

banner_img_path = get_banner_image()

# Clean BRS Styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #FFF0F6 0%, #FFFFFF 50%, #FFEBF2 100%) !important;
        color: #1E293B;
    }

    .main .block-container {
        max-width: 1150px;
        padding-top: 1rem;
        padding-bottom: 2.5rem;
    }

    /* Card Forms */
    [data-testid="stForm"] {
        background: #FFFFFF !important;
        border: 2px solid #F8BBD0 !important;
        border-radius: 16px !important;
        padding: 24px 22px !important;
        box-shadow: 0 10px 28px rgba(230, 26, 141, 0.10) !important;
    }

    /* Input Field Labels */
    label[data-testid="stWidgetLabel"] p {
        font-size: 14.5px !important;
        font-weight: 700 !important;
        color: #880E4F !important;
        margin-bottom: 4px !important;
    }

    /* Input Boxes */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #FFF9FB !important;
        border: 1.5px solid #F48FB1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
    }

    /* Submit Button */
    div.stButton > button:first-child, div.stFormSubmitButton > button:first-child {
        background: linear-gradient(90deg, #E61A8D 0%, #D81B60 100%) !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 12px 24px !important;
        box-shadow: 0 6px 18px rgba(230, 26, 141, 0.38) !important;
        margin-top: 10px !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:first-child:hover, div.stFormSubmitButton > button:first-child:hover {
        background: linear-gradient(90deg, #C2185B 0%, #880E4F 100%) !important;
        box-shadow: 0 8px 24px rgba(230, 26, 141, 0.50) !important;
        transform: translateY(-2px);
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] {
        font-weight: 700 !important;
        font-size: 14.5px !important;
        color: #64748B !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #E61A8D !important;
        border-bottom: 3px solid #E61A8D !important;
        font-weight: 800 !important;
    }

    .portal-info-box {
        background: #FFFFFF;
        border-left: 5px solid #E61A8D;
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 18px;
        box-shadow: 0 4px 16px rgba(230, 26, 141, 0.08);
        border: 1px solid #FCE4EC;
    }
    .portal-info-box h4 {
        color: #AD1457 !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        margin: 0 0 6px 0 !important;
    }
    .portal-info-box p {
        color: #334155 !important;
        font-size: 13.5px !important;
        line-height: 1.5 !important;
        margin: 0 !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFF7FA !important;
        border-right: 1.5px solid #F8BBD0 !important;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border-left: 5px solid #E61A8D;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(230, 26, 141, 0.10);
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

def render_top_poster():
    if banner_img_path:
        st.image(banner_img_path, use_container_width=True)

# Database Setup
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

# Jurisdiction Data
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

# Google Sheets Connector
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

# Robust, Universal PDF Parsing Function
def parse_acknowledgement_pdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                full_text += extracted + "\n"

        # Normalize spaces and invisible unicode whitespace
        normalized = re.sub(r'[\r\t\f\v]', ' ', full_text)
        normalized = re.sub(r'[ \xa0]+', ' ', normalized)

        def search_value(regex_list):
            for pattern in regex_list:
                match = re.search(pattern, normalized, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    val = val.replace("$", "").strip()
                    if val:
                        return val
            return ""

        parsed = {}
        parsed["application_id"] = search_value([
            r"Application\s*(?:Id|ID|No|Number)?\s*[:\-\|]?\s*([A-Z0-9]{8,25})",
            r"(F\d{10,20})",
            r"App\s*Id\s*[:\-\|]?\s*([A-Z0-9]+)"
        ])

        parsed["applicant_name"] = search_value([
            r"Applicant\s*Name\s*[:\-\|]?\s*([A-Za-z\s\.]+?)(?=\s*Gender|\s*Relation|\s*Father|\s*Husband|\n|$)",
            r"Name\s*of\s*Applicant\s*[:\-\|]?\s*([A-Za-z\s\.]+?)(?=\s*Gender|\s*Relation|\n|$)",
            r"Applicant\s*[:\-\|]?\s*([A-Za-z\s\.]+?)(?=\s*Gender|\n|$)"
        ])

        parsed["gender"] = search_value([
            r"Gender\s*[:\-\|]?\s*([A-Za-z]+)",
            r"\b(Male|Female|Transgender)\b"
        ])

        parsed["relation_name"] = search_value([
            r"Relation\s*Name\s*[:\-\|]?\s*([A-Za-z\s\.]+?)(?=\s*House|\s*Gender|\s*Address|\n|$)",
            r"(?:Father|Husband|Mother)\s*(?:Name)?\s*[:\-\|]?\s*([A-Za-z\s\.]+?)(?=\s*House|\n|$)"
        ])

        parsed["house_number"] = search_value([
            r"House\s*Number\s*[:\-\|]?\s*([A-Za-z0-9\-\/\s]+?)(?=\s*Mlc|\s*District|\s*Constituency|\n|$)",
            r"H\.?\s*No\.?\s*[:\-\|]?\s*([A-Za-z0-9\-\/\s]+?)(?=\s*Mlc|\s*District|\n|$)"
        ])

        parsed["mlc_constituency"] = search_value([
            r"(?:Mlc|Constituency)\s*Name\s*[:\-\|]?\s*([A-Za-z\-\s]+?)(?=\s*District|\s*Status|\n|$)",
            r"Constituency\s*[:\-\|]?\s*([A-Za-z\-\s]+?)(?=\s*District|\n|$)"
        ])

        parsed["district_name"] = search_value([
            r"District\s*Name\s*[:\-\|]?\s*([A-Za-z\s]+?)(?=\s*Current|\s*Status|\s*Ack|\n|$)",
            r"District\s*[:\-\|]?\s*([A-Za-z\s]+?)(?=\s*Current|\s*Status|\n|$)"
        ])

        parsed["current_status"] = search_value([
            r"Current\s*Status\s*[:\-\|]?\s*([A-Za-z0-9\s\.]+?)(?=\s*Print|\s*Exit|\n|$)",
            r"Status\s*[:\-\|]?\s*([A-Za-z0-9\s\.]+?)(?=\s*Print|\n|$)"
        ])

        return parsed
    except Exception as e:
        return {}

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

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.full_name = None

# Input field session keys to guarantee multi-device updates
form_fields = [
    "field_app_id", "field_applicant_name", "field_gender",
    "field_relation_name", "field_house_no", "field_constituency",
    "field_ack_status", "field_ack_district", "last_uploaded_file_name"
]
for f in form_fields:
    if f not in st.session_state:
        st.session_state[f] = ""

# Authentication Interface
if not st.session_state.logged_in:
    render_top_poster()

    _, col_form, _ = st.columns([1, 1.8, 1])

    with col_form:
        tab1, tab2 = st.tabs(["🔑 War Room Sign In", "📝 Volunteer Registration"])

        with tab1:
            with st.form("login_form"):
                uname = st.text_input("Username", placeholder="e.g. admin")
                pword = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("🚀 Sign In to Console", use_container_width=True)
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

        st.markdown("""
        <div class="portal-info-box">
            <h4>🌸 భారత రాష్ట్ర సమితి (BRS) — War Room Console</h4>
            <p><strong>Warangal – Khammam – Nalgonda Graduate MLC Constituency</strong></p>
            <p style="margin-top: 6px; color: #475569;">
                📌 <strong>Central Voter Consolidation Desk:</strong><br>
                Authorized operators and volunteers can upload Form-18 slips to verify duplicates and sync voter records directly with Google Sheets.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# Authenticated Workspace
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

render_top_poster()

if st.session_state.role == "Admin":
    main_tab1, main_tab2 = st.tabs(["📥 Data Ingestion & Form-18 Processing", "📊 War Room Analytics & Mandal Breakdown"])
else:
    main_tab1 = st.container()

# TAB 1: FORM-18 ENTRY
with main_tab1:
    upload_col, data_col = st.columns([1, 1.25], gap="large")

    with upload_col:
        st.markdown("#### 1. Attach Form-18 PDF")
        uploaded_pdf = st.file_uploader("Upload CEO Telangana Form-18 PDF", type=["pdf"], key="form18_uploader")

        # Parse and sync to session state immediately upon upload
        if uploaded_pdf is not None:
            if st.session_state["last_uploaded_file_name"] != uploaded_pdf.name:
                pdf_bytes = uploaded_pdf.read()
                parsed_data = parse_acknowledgement_pdf(pdf_bytes)

                if parsed_data.get("application_id") or parsed_data.get("applicant_name"):
                    st.session_state["field_app_id"] = parsed_data.get("application_id", "")
                    st.session_state["field_applicant_name"] = parsed_data.get("applicant_name", "")
                    st.session_state["field_gender"] = parsed_data.get("gender", "")
                    st.session_state["field_relation_name"] = parsed_data.get("relation_name", "")
                    st.session_state["field_house_no"] = parsed_data.get("house_number", "")
                    st.session_state["field_constituency"] = parsed_data.get("mlc_constituency", "") or "Warangal-Khammam-Nalgonda"
                    st.session_state["field_ack_status"] = parsed_data.get("current_status", "")
                    st.session_state["field_ack_district"] = parsed_data.get("district_name", "")
                    st.session_state["last_uploaded_file_name"] = uploaded_pdf.name
                    st.rerun()

        if st.session_state["field_app_id"]:
            st.success(f"✅ Extracted: **{st.session_state['field_applicant_name']}** (`{st.session_state['field_app_id']}`)")

    with data_col:
        st.markdown("#### 2. Review & Tag Jurisdiction Details")

        with st.form("voter_entry_form"):
            st.markdown("##### 👤 Applicant Information")
            c1, c2 = st.columns(2)
            app_id = c1.text_input("Application ID", value=st.session_state["field_app_id"])
            name = c2.text_input("Applicant Name", value=st.session_state["field_applicant_name"])

            c3, c4, c5 = st.columns(3)
            gender = c3.text_input("Gender", value=st.session_state["field_gender"])
            relation = c4.text_input("Relation Name", value=st.session_state["field_relation_name"])
            house_no = c5.text_input("House Number", value=st.session_state["field_house_no"])

            c6, c7 = st.columns(2)
            mlc_const = c6.text_input("Constituency", value=st.session_state["field_constituency"] or "Warangal-Khammam-Nalgonda")
            status = c7.text_input("Status", value=st.session_state["field_ack_status"])

            st.markdown("---")
            st.markdown("##### 📍 Tag Jurisdiction (MLC Limits)")
            
            all_districts = list(JURISDICTION_DATA.keys())
            
            # Select matching default district if detected
            default_dist_idx = 0
            detected_district = st.session_state["field_ack_district"].strip().title()
            for idx, d_name in enumerate(all_districts):
                if d_name.lower() in detected_district.lower() or detected_district.lower() in d_name.lower():
                    default_dist_idx = idx
                    break

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
            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Degree Certificate verified, BRS supporter")

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
                                st.warning(f"⚠️️ Duplicate Detected! Application ID {app_id} already exists in database. Logged in audit trail.")
                            else:
                                new_entry = [
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    app_id, name, gender, relation, house_no,
                                    mlc_const, st.session_state["field_ack_district"], status,
                                    selected_district, selected_mandal, final_village,
                                    ref_name, mobile_no, remarks, st.session_state.username
                                ]
                                ws.append_row(new_entry)
                                st.success(f"🎉 Successfully Ingested: {name} ({app_id}) to BRS Central Records!")
                                
                                # Clear session fields for subsequent slip entry
                                for f in form_fields:
                                    st.session_state[f] = ""
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
