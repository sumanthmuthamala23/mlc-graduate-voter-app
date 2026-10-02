import streamlit as st
from pypdf import PdfReader
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlite3
import hashlib
import re
import os
import io
import json
import base64
import requests
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

# BRS & Google Lens Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #FFF0F6 0%, #FFFFFF 50%, #FFEBF2 100%) !important;
        color: #1E293B;
    }

    .main .block-container {
        max-width: 1180px;
        padding-top: 1rem;
        padding-bottom: 2.5rem;
    }

    /* Google Lens Scanner Card */
    .lens-header-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #FFF5F9 100%);
        border: 2px solid #F48FB1;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 4px 14px rgba(230, 26, 141, 0.08);
    }
    .lens-icon-badge {
        font-size: 28px;
        background: linear-gradient(135deg, #E61A8D 0%, #C2185B 100%);
        color: white;
        border-radius: 10px;
        padding: 6px 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .lens-title {
        font-size: 16px;
        font-weight: 800;
        color: #880E4F;
        margin: 0;
    }
    .lens-desc {
        font-size: 12.5px;
        color: #64748B;
        margin: 2px 0 0 0;
    }

    /* Card Forms */
    [data-testid="stForm"] {
        background: #FFFFFF !important;
        border: 2px solid #F8BBD0 !important;
        border-radius: 16px !important;
        padding: 24px 22px !important;
        box-shadow: 0 10px 28px rgba(230, 26, 141, 0.10) !important;
    }

    label[data-testid="stWidgetLabel"] p {
        font-size: 14.5px !important;
        font-weight: 700 !important;
        color: #880E4F !important;
        margin-bottom: 4px !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #FFF9FB !important;
        border: 1.5px solid #F48FB1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
    }

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

# Jurisdiction Hierarchy
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

# Multi-Key Rotation Pool Retriever
def get_configured_api_keys():
    keys = []
    if st.session_state.get("custom_gemini_key", "").strip():
        keys.append(st.session_state["custom_gemini_key"].strip())

    try:
        if "GEMINI_API_KEYS" in st.secrets:
            val = st.secrets["GEMINI_API_KEYS"]
            if isinstance(val, list):
                keys.extend([str(k).strip() for k in val if str(k).strip()])
            elif isinstance(val, str):
                cleaned = val.replace('"', '').replace("'", "").replace('[', '').replace(']', '')
                for piece in cleaned.split(","):
                    if piece.strip():
                        keys.append(piece.strip())
        elif "GEMINI_API_KEY" in st.secrets:
            keys.append(str(st.secrets["GEMINI_API_KEY"]).strip())
    except Exception:
        pass

    for env_k in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        if os.environ.get(env_k):
            keys.append(os.environ[env_k].strip())

    seen = set()
    deduped = []
    for k in keys:
        if len(k) > 15 and k not in seen:
            seen.add(k)
            deduped.append(k)
    return deduped

# Image Enhancement Engine for Unclear, Low-Contrast, or Blurry Photos
def enhance_image_for_ocr(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Auto-orient based on EXIF tag
        img = ImageOps.exif_transpose(img)
        
        # If dimensions are small (like a mobile thumbnail), upscale with high quality
        w, h = img.size
        if w < 1200 or h < 1200:
            scale_factor = max(1200 / w, 1200 / h)
            new_size = (int(w * scale_factor), int(h * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to Grayscale to strip distracting color compression artifacts
        gray = img.convert('L')
        
        # Boost Contrast (makes faint gray text dark and clear)
        contrast_enhancer = ImageEnhance.Contrast(gray)
        enhanced_contrast = contrast_enhancer.enhance(1.8)
        
        # Boost Sharpness (crisp edges around letters & numbers)
        sharp_enhancer = ImageEnhance.Sharpness(enhanced_contrast)
        sharpened = sharp_enhancer.enhance(2.0)
        
        # Export as high-quality PNG bytes
        out_buf = io.BytesIO()
        sharpened.save(out_buf, format="PNG")
        return out_buf.getvalue(), "image/png"
    except Exception:
        return image_bytes, "image/jpeg"

# Engine 1: Pure Offline PDF Text Extraction
def parse_acknowledgement_pdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                full_text += extracted + "\n"

        if len(full_text.strip()) < 15:
            return {}, ""

        normalized = re.sub(r'[\r\t\f\v]', ' ', full_text)
        normalized = re.sub(r'[ \xa0]+', ' ', normalized)

        def search_value(regex_list):
            for pattern in regex_list:
                match = re.search(pattern, normalized, re.IGNORECASE)
                if match:
                    val = match.group(1).strip().replace("$", "").strip()
                    if val:
                        return val
            return ""

        parsed = {}
        parsed["application_id"] = search_value([
            r"Application\s*(?:Id|ID|No|Number)?\s*[:\-\|]?\s*([A-Z0-9]{8,25})",
            r"\b(F\d{10,20})\b",
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

        status_match = search_value([
            r"Current\s*Status\s*[:\-\|]?\s*(Submitted|Pending|Approved|Rejected|Verified|In\s*Process)",
            r"Status\s*[:\-\|]?\s*(Submitted|Pending|Approved|Rejected|Verified|In\s*Process)",
            r"\b(Submitted|Pending|Approved|Rejected|Verified)\b"
        ])
        if not status_match or "application" in status_match.lower() or "f18" in status_match.lower():
            status_match = "Submitted"

        parsed["current_status"] = status_match
        return parsed, normalized
    except Exception:
        return {}, ""

# Engine 2: Google Lens Multi-Key Vision Model with Text Fallback & Image Enhancement
def parse_with_google_lens(file_bytes, mime_type, api_keys):
    if not api_keys:
        return {}, ""

    b64_data = base64.b64encode(file_bytes).decode('utf-8')
    prompt_text = """You are an expert Google Lens OCR system scanning a CEO Telangana Form-18 Acknowledgement Slip / Graduate Voter Slip.
Even if the image is blurry, low contrast, cropped, or slightly tilted:
1. Locate the 'Application Id' (starts with 'F' followed by 10-15 digits, like F180928310521426).
2. Locate 'Applicant Name' (in English capital letters).
3. Locate 'Gender' (Male / Female).
4. Locate 'Relation Name' (Father / Husband name).
5. Locate 'House Number' (e.g. 7-3-410/6).
6. Locate 'Mlc Name' / 'Constituency' (e.g. Warangal-Khammam-Nalgonda).
7. Locate 'District Name' (e.g. Khammam, Nalgonda, Warangal, Suryapet).
8. Status is strictly 'Submitted'. Do NOT copy the Application ID into status.

Return ONLY a valid JSON object matching this schema:
{
  "application_id": "...",
  "applicant_name": "...",
  "gender": "...",
  "relation_name": "...",
  "house_number": "...",
  "mlc_constituency": "...",
  "district_name": "...",
  "current_status": "Submitted",
  "ocr_full_text": "all readable text"
}"""

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                {"text": prompt_text}
            ]
        }],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    for key in api_keys:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                res = requests.post(url, json=payload, timeout=28)
                if res.status_code == 200:
                    body = res.json()
                    text_content = body["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Clean markdown fence tags if returned
                    clean_json_str = re.sub(r'^```json\s*', '', text_content.strip(), flags=re.MULTILINE)
                    clean_json_str = re.sub(r'^
