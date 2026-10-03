import streamlit as st
from pypdf import PdfReader
from PIL import Image, ImageEnhance, ImageOps
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
import urllib.parse
from datetime import datetime

# Fallback local OCR engine
try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

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

# BRS Styling + Discrete Credit Footer
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #FFF0F6 0%, #FFFFFF 50%, #FFEBF2 100%) !important;
        color: #1E293B;
    }

    .main .block-container {
        max-width: 1220px;
        padding-top: 1rem;
        padding-bottom: 3.5rem;
    }

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

    .voter-card-container {
        background: #FFFFFF !important;
        border: 2px solid #F8BBD0 !important;
        border-radius: 16px !important;
        padding: 24px 22px !important;
        box-shadow: 0 10px 28px rgba(230, 26, 141, 0.10) !important;
        margin-bottom: 20px;
    }

    .wa-card {
        background: #E8F5E9;
        border: 2px solid #81C784;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 16px 0;
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

    /* Clean, Non-intrusive Developer Footer */
    .developer-footer {
        text-align: center;
        margin-top: 36px;
        padding-top: 14px;
        border-top: 1px dashed #F8BBD0;
        font-size: 13px;
        color: #880E4F;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .developer-footer span {
        color: #E61A8D;
        font-weight: 800;
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

def render_footer():
    st.markdown("""
    <div class="developer-footer">
        Developed by <span>Sumanth Muthamala</span> | BRS Central War Room Console
    </div>
    """, unsafe_allow_html=True)

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
    c.execute('''CREATE TABLE IF NOT EXISTS local_records (
                    application_id TEXT PRIMARY KEY,
                    applicant_name TEXT,
                    timestamp TEXT
                )''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        pwd_hash = hashlib.sha256("Admin@123".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES ('admin', ?, 'BRS Central War Room', 'Admin', 'Approved')", (pwd_hash,))
    conn.commit()
    conn.close()

init_db()

# Safe Pre-Widget Session Cleanup
if st.session_state.get("clear_form_trigger", False):
    st.session_state["inp_app_id"] = ""
    st.session_state["inp_name"] = ""
    st.session_state["inp_gender"] = ""
    st.session_state["inp_relation"] = ""
    st.session_state["inp_house_no"] = ""
    st.session_state["inp_status"] = "Submitted"
    st.session_state["inp_ref_name"] = ""
    st.session_state["inp_mobile_no"] = ""
    st.session_state["inp_remarks"] = ""
    st.session_state["custom_village_input"] = ""
    st.session_state["last_file_hash"] = ""
    st.session_state["clear_form_trigger"] = False

# ==============================================================================
# OFFICIAL TELANGANA REVENUE JURISDICTION HIERARCHY
# Erstwhile Khammam, Warangal, and Nalgonda (11 Districts, 190+ Mandals)
# ==============================================================================
JURISDICTION_DATA = {
    "Khammam": {
        "Khammam Urban": ["Khammam (M Corp)", "Khanapuram Haveli", "Dhamsalapuram", "Mallemadugu", "Burhanpuram", "Velugumatla", "Polepalli"],
        "Khammam Rural": ["Arempula", "Edulapuram", "Gollapadu", "Theldarupalli", "Maddulapalli", "M.Venkatayapalem", "Gudimalla", "Jalpalli", "Thirthala"],
        "Raghunathapalem": ["Raghunathapalem", "Chimmapudi", "Eerlapudi", "Janakipuram", "Kamanchikal", "Koyachelaka", "Papatpally", "Venkatayapalem"],
        "Kusumanchi": ["Kusumanchi", "Palair", "Jillellapadu", "Kokkireni", "Mallaigudem", "Naikangudem", "Nelapatla", "Perikasingaram", "Pocharam"],
        "Thirumalayapalem": ["Thirumalayapalem", "Sublaid", "Errappaigudem", "Bachodu", "Bandampalli", "Jalpalli", "Kakarkal", "Patharlapadu"],
        "Nelakondapalli": ["Nelakondapalli", "Bodulabanda", "Appalanarasimhapuram", "Banigandlapadu", "Byrannagudem", "Chennaram", "Mandrajpally", "Panigiri"],
        "Mudigonda": ["Mudigonda", "Vallabhi", "Chirumarri", "Gokaraju Palli", "Kattukachavaram", "Madhapuram", "Mallaram", "Medepalli", "Pandillapalli"],
        "Chinthakani": ["Chinthakani", "Jagannadhapuram", "Boppudi", "Chinna Mandava", "Komatlagudem", "Nagulavancha", "Patha Bitragunta", "Thimmaraopeta"],
        "Wyra": ["Wyra", "Somavaram", "Gannavaram", "Karamthota", "Brahmanapalli", "Gollanapadu", "Govindapuram", "Musalimadugu", "Siripuram", "Vallapuram"],
        "Bonakal": ["Bonakal", "Allinagaram", "Brahmanapalli", "Chirunomula", "Choppakatlapalem", "Govindapuram", "Kalakota", "Mustikuntla", "Ravinuthala"],
        "Madhira": ["Madhira (M)", "Dendukuru", "Mallaram", "Siripuram", "Atkur", "Chavatapalli", "Didugupadu", "Rayapatnam", "Rompimalla", "Torraguntapalem"],
        "Yerrupalem": ["Yerrupalem", "Banigandlapadu", "Bheemavaram", "Gosaveedu", "Inagali", "Jamigollepalli", "Kesireddypalli", "Peddagopathi", "Remidicherla"],
        "Sathupalli": ["Sathupalli (M)", "Gangaram", "Kistaram", "Rejarla", "Bethupalli", "Cheruvumadhavaram", "Kakarlapalli", "Narayanapuram", "Rudrakshapalli"],
        "Vemsoor": ["Vemsoor", "Adavimallela", "Berigopala Puram", "Chowdavaram", "Duddepudi", "Kandukur", "Marlapadu", "Paturu", "Venkatapuram"],
        "Penuballi": ["Penuballi", "Karakavagu", "Lingagudem", "Bayyannagudem", "Bhimavaram", "Chinthalagudem", "Gangadevipadu", "Mandalapadu", "V.M.Banjara"],
        "Kallur": ["Kallur", "Chinnakorukondi", "Peruvancha", "Lokavaram", "Chandrugonda", "Chennur", "Gokavaram", "Mucherla", "Payapur", "Pocharam"],
        "Thallada": ["Thallada", "Billupadu", "Guntupalli", "Kalakota", "Kolanupalli", "Kothapeta", "Madhupalli", "Mittapalli", "Ramanagaram"],
        "Enkoor": ["Enkoor", "Nacharam", "Timmapeta", "Bhurhanpur", "Jannaram", "Kolanupalli", "Medepalli", "Rajalingampeta"],
        "Konijerla": ["Konijerla", "Basavapuram", "Ballepalli", "Chinna Gopapalli", "Gundrathimadugu", "Lalapuram", "Pallipadu", "Pedda Gopapalli", "Thanikella"],
        "Singareni": ["Singareni", "Karepalli", "Gate Karepalli", "Madharam", "Manikyanagaram", "Motlagudem", "Perupalli", "Relakayalapalli", "Vishwanathapalli"],
        "Kamepalli": ["Kamepalli", "Adavimallela", "Bada Thanda", "Cheruvumadhavaram", "Garla Vaddigudem", "Jagannadhapuram", "Manikyaram", "Ponnekal"]
    },
    "Bhadradri Kothagudem": {
        "Kothagudem": ["Kothagudem (M)", "Chunchupalli", "Garimellapadu", "Rudrampur", "Babu Camp", "Vidyanagar", "Penugadapa"],
        "Palvancha": ["Palvancha (M)", "Ghanpur", "Ulvanuru", "Karakavagu", "Yanambailu", "Pandurangapuram", "Seetharampuram"],
        "Chunchupalli": ["Chunchupalli", "Vidyanagar", "Penuballi", "Rudrampur", "Gouthampur", "Old Kothagudem"],
        "Laxmidevipalli": ["Laxmidevipalli", "Chatakonda", "Regalla", "Gangaram", "Punukuduchela", "Hemachandrapuram"],
        "Sujathanagar": ["Sujathanagar", "Nayanakonda", "Singabhupalem", "Mangapet", "Komararam", "Vegigudem"],
        "Julurpad": ["Julurpad", "Kakarla", "Padamata Narsapuram", "Kommapalli", "Bheemanapalli", "Vinobanagar"],
        "Chandrugonda": ["Chandrugonda", "Dammapeta", "Pokalagudem", "Thippanapalli", "Gannavaram", "Gurralacheruvu"],
        "Tekulapalli": ["Tekulapalli", "Sulthan Nagar", "Bodu", "Koppurai", "Madharam", "Rollapadu", "Gundepudi"],
        "Yellandu": ["Yellandu (M)", "Rompaid", "Sudimalla", "Komararam", "Mamillagudem", "Manikyaram", "Pocharam"],
        "Allapalli": ["Allapalli", "Markode", "Dhaner", "Gundlapadu", "Kothuru", "Ramanakkapet"],
        "Gundala": ["Gundala", "Allapalli", "Lingagudem", "Muthapuram", "Damaratogu", "Padigapuram", "Zinnelagudem"],
        "Manuguru": ["Manuguru (M)", "Samithi Singaram", "Pagideru", "Kondapuram", "Toggudem", "Koonavaram", "Chinaranagudem"],
        "Aswapuram": ["Aswapuram", "Nellipaka", "Chintiryala", "Gondigudem", "Kondapalli", "Manubothulagudem", "Mamidigudem"],
        "Burgampahad": ["Burgampahad", "Sarapaka", "Morampalli Banjara", "Iravandi", "Nagineniprolu", "Sompalli", "Motugudem"],
        "Pinapaka": ["Pinapaka", "Janampeta", "Bayyaram", "Madagudem", "Uppaka", "Pandillapalli", "Togagudem"],
        "Karakagudem": ["Karakagudem", "Bhatpalli", "Kothaguda", "Raghavapuram", "Motlagudem", "Samatbhatpalli"],
        "Cherla": ["Cherla", "Subbampeta", "Kurnapalli", "Lingapuram", "Moggallapalli", "Rallapuram", "Tepireddipalem"],
        "Dummugudem": ["Dummugudem", "Parnasala", "Sunnambatti", "Kothapalli", "Gowraram", "Marikala", "Pedanallaballi"],
        "Bhadrachalam": ["Bhadrachalam (GP)", "Seethampeta", "Nellipaka", "Kothuru", "Gundala", "Purushothapatnam"],
        "Aswaraopeta": ["Aswaraopeta", "Vinayakapuram", "Gundlapadu", "Achutapuram", "Gummadavalli", "Kavundinya Puram"],
        "Dammapeta": ["Dammapeta", "Apparaopeta", "Mandalapalli", "Nagupalli", "Gandugulapalli", "Katkur", "Patwarigudem"],
        "Mulakalapalli": ["Mulakalapalli", "Madhavaram", "Kamalapuram", "Pogallapalli", "Annaram", "Thimmapuram"],
        "Annapureddypalli": ["Annapureddypalli", "Gumpena", "Namazipeta", "Penugolu", "Peddagopathi", "Tallagudem"]
    },
    "Nalgonda": {
        "Nalgonda": ["Nalgonda (M)", "Panagallu", "Arjalabavi", "Cherlapally", "Appajipeta", "Chityala", "Dandepalli", "Gundlapalli", "Kanchanapalli"],
        "Narketpally": ["Narketpally", "Cheruvugattu", "Bommireddigudem", "Chityala", "Mandra", "Nemmani", "Shali Gouraram", "Thummalaguda"],
        "Chityal": ["Chityal (M)", "Gundrampally", "Vanipakala", "Velminedu", "Aregudem", "Chinna Kaparthy", "Pedda Kaparthy", "Pittampally"],
        "Kattangur": ["Kattangur", "Aitipamula", "Bollepally", "Garikabanda", "Inupamula", "Kalmalla", "Kurumarthy", "Mallaram"],
        "Nakrekal": ["Nakrekal (M)", "Chandampally", "Chityala", "Mangalpally", "Nomula", "Nellibanda", "Thipparthy", "Vallabhapur"],
        "Thipparthy": ["Thipparthy", "Anantharam", "Indloor", "Jungamreddiguda", "Madharam", "Pajjur", "Sarvaram", "Surepally"],
        "Kethepally": ["Kethepally", "Bhimaram", "Cheruvupally", "Gopala Puram", "Inparthi", "Kasarlapahad", "Korlapahad", "Uppalapahad"],
        "Saligouraram": ["Saligouraram", "Aitipamula", "Chitloor", "Madhavaram", "Perkakondaram", "Thakkallapahad", "Utkur"],
        "Munugode": ["Munugode", "Kommaravelli", "Pulipalpula", "Chikkepally", "Gudur", "Kalvakuntla", "Koratikal", "Singaram"],
        "Chandur": ["Chandur (M)", "Gundlepally", "Kasthala", "Nelmari", "Pallepahad", "Sheripally", "Thummalapally"],
        "Marriguda": ["Marriguda", "Dharmapuram", "Laxmidevipally", "Ramireddypally", "Sarampeta", "Sivannaguda", "Vattipally"],
        "Nampally": ["Nampally", "Chalmeda", "Devatpally", "Guntapally", "Mahammadapuram", "Mustipally", "Pasnoor", "Thummalapally"],
        "Gurrampode": ["Gurrampode", "Chamaledu", "Gandhammalla", "Junuthala", "Koppole", "Musalapally", "Nadigadda", "Pogilla"],
        "Kanagal": ["Kanagal", "Bobbilypally", "Cheruvuantharam", "Dorepally", "Gundlapally", "Pagidimarri", "Shabajpally", "Thurpu Pally"],
        "Devarakonda": ["Devarakonda (M)", "Tatipole", "Kondabheemanapalli", "Padamati Pally", "Seripally", "Chinthapally", "Mudigonda"],
        "Kondamallepally": ["Kondamallepally", "Balepally", "Chinthalagudem", "Devaracharla", "Gundlapally", "Kolmunthalapahad"],
        "Gundlapally (Dindi)": ["Dindi", "Gundlapally", "Gokaram", "Kamalapuram", "Kandukur", "Marriguda", "Thogapally"],
        "Chandampet": ["Chandampet", "Gannerlapally", "Kambalapally", "Nerudugommu", "Pedamunigal", "Pogilla", "Yerraguntapally"],
        "Neredugommu": ["Neredugommu", "Bugga Thanda", "Chinna Munigal", "Kacharajupally", "Vakati Thanda", "Yellareddyguda"],
        "Pedda Adiserlapally (P.A. Pally)": ["P.A. Pally", "Angadipeta", "Ghanpur", "Gudipally", "Kondrapole", "Thirumalagiri", "Vaddipatla"],
        "Peddavoora": ["Peddavoora", "Chinthapally", "Nandikonda (M)", "Pothunoor", "Pulicherla", "Sirasanagandla", "Tungathurthy"],
        "Anumula (Haliya)": ["Haliya (M)", "Anumula", "Chinna Anumula", "Ibrahimpet", "Marepally", "Perur", "Rajavaram", "Salkanoor"],
        "Thripuraram": ["Thripuraram", "Anjanapally", "Appalammagudem", "Dharmapuram", "Kampasagar", "Neelayagudem", "Satyanarayanapuram"],
        "Nidamanoor": ["Nidamanoor", "Bommireddyguda", "Chillapally", "Guntipally", "Marriguda", "Thumadam", "Venkateshwarnagar"],
        "Madugulapally": ["Madugulapally", "Chirumarthi", "Garikuntapally", "Kannekal", "Koppole", "Kukudlapally", "Thopicherla"],
        "Miryalaguda": ["Miryalaguda (M)", "Alagadapa", "Chinthapalli", "Gudur", "Keshawapuram", "Rayannaguda", "Thallagadda", "Venkatadripeta"],
        "Vemulapally": ["Vemulapally", "Amanagallu", "Buggalagudem", "Challagariga", "Madharam", "Molka Patnam", "Salakanoor"],
        "Damaracherla": ["Damaracherla", "Adavidevulapally", "Balajinagar", "Kallepally", "Kondrapole", "Narsapur", "Thallaveerappagudem"],
        "Adavidevulapally": ["Adavidevulapally", "Chityala", "Kothanandikonda", "Molakacharla", "Mukkamula", "Subbareddygudem"]
    },
    "Suryapet": {
        "Suryapet": ["Suryapet (M)", "Kudakuda", "Pillalamarri", "Balaemla", "Imampet", "Kesaram", "Pinnaipalem", "Tekumatla"],
        "Chivvemla": ["Chivvemla", "Ailapuram", "Balanayak Thanda", "Gumpula", "Kudakuda", "Thimmapuram", "Undrugonda"],
        "Mothey": ["Mothey", "Annariguda", "Burugugadda", "Mamillagudem", "Raghavapuram", "Sirikonda", "Vibhithapuram"],
        "Jajireddygudem (Arvapally)": ["Arvapally", "Jajireddygudem", "Kandagatla", "Kommala", "Thimmapuram", "Vangamarthy"],
        "Penpahad": ["Penpahad", "Anantharam", "Cheepunuthala", "Gajulmalkapuram", "Macharam", "Singareddypalem", "Thurpu Gudem"],
        "Atmakur (S)": ["Atmakur", "Aregudem", "Enbamula", "Gattusingaram", "Kaparthisingaram", "Nemmikal", "Patha Suryapet"],
        "Kodad": ["Kodad (M)", "Thogarrai", "Gudibanda", "Dora Kunta", "Komarabanda", "Nadigudem", "Tammarabanda"],
        "Chilkur": ["Chilkur", "Bethavolu", "Jerripothulagudem", "Kondapuram", "Mulkanoor", "Ramapuram", "Seetharampuram"],
        "Munagala": ["Munagala", "Barakathgudem", "Kalakova", "Kokkireni", "Madhavaram", "Nelamarri", "Repala", "Tadvai"],
        "Nadigudem": ["Nadigudem", "Chakrirala", "Karivirala", "Ratnavaram", "Siripuram", "Telugurao Peta", "Venkataramapuram"],
        "Ananthagiri": ["Ananthagiri", "Amancharla", "Channaram", "Gongulabanda", "Khanapuram", "Singavaram", "Tripuravaram"],
        "Huzurnagar": ["Huzurnagar (M)", "Burugugadda", "Macharam", "Gopalapuram", "Karakkagudem", "Lingagiri", "Ponugodu"],
        "Mattampally": ["Mattampally", "Alinagar", "Chintalapalem", "Gundlapally", "Mattampalli", "Pedaveedu", "Raghavapuram"],
        "Mellachervu": ["Mellachervu", "Dondapadu", "Kandibanda", "Kothuru", "Ramaswamy Gudem", "Vepalamadhavaram"],
        "Palakeedu": ["Palakeedu", "Alinagar", "Gundepuri", "Janpahad", "Mahankaligudem", "Sajjapuram", "Yellapuram"],
        "Garidepally": ["Garidepally", "Appannapet", "Kalmalacheruvu", "Kutubshapuram", "Ponugodu", "Rayangudem", "Thimmareddygudem"],
        "Nereducharla": ["Nereducharla (M)", "Bodaldinna", "Chilumuntala", "Fatehpur", "Penpahad", "Somavaram", "Yellammagudem"],
        "Thungathurthi": ["Thungathurthi", "Annaram", "Gotta", "Karvirela", "Maddirala", "Pasnoor", "Sangem", "Venkepally"],
        "Maddirala": ["Maddirala", "Chinna Madnoor", "Gorigepally", "Kuntlagudem", "Mamillagudem", "Mukundapuram", "Polumalla"],
        "Nagaram": ["Nagaram", "Etoor", "Mamillapally", "Pasnoor", "Phanigiri", "Pothireddypally", "Vardhapuram"],
        "Noothankal": ["Noothankal", "Bommireddygudem", "Chillapally", "Dirisinacharla", "Gundepuri", "Miryala", "Yellampeta"],
        "Thirumalagiri": ["Thirumalagiri (M)", "Bandapally", "Chinthakunta", "Jalalpuram", "Mamillagudem", "Nelamarri", "Thimmapuram"]
    },
    "Yadadri Bhuvanagiri": {
        "Bhongir": ["Bhongir (M)", "Rayagiri", "Bolligudem", "Anantharam", "Gouse Nagar", "Pagidipalli", "Thukkapur"],
        "Bibinagar": ["Bibinagar", "Gudur", "Jameelapet", "Kondamadugu", "Mahadevpur", "Padamati Somaram", "Raghavapuram"],
        "Bhoodan Pochampally": ["Pochampally (M)", "Bhimanapally", "Deshmukhi", "Jiblakpally", "Mukhtapur", "Revanapally"],
        "Choutuppal": ["Choutuppal (M)", "Lingojiguda", "Thallasingaram", "Dharmojigudem", "Gokaram", "Koyyalagudem", "Panthangi"],
        "Narayanpur": ["Narayanpur", "Chilkapally", "Gudur", "Jannaram", "Kotamarthy", "Pilligundla", "Sarvel", "Vankamamidi"],
        "Ramannapet": ["Ramannapet", "Bogaram", "Janampally", "Kakkerla", "Kommayagudem", "Siripuram", "Thummalaguda"],
        "Valigonda": ["Valigonda", "Arror", "Choutapally", "Golnepally", "Kanchanpally", "Proddutur", "Tekulasomaram", "Vemulakonda"],
        "Yadagirigutta": ["Yadagirigutta (M)", "Gundlapally", "Saidapuram", "Datwarpally", "Gowraipally", "Mallesham Pally", "Vangapally"],
        "Alair": ["Alair (M)", "Kolannur", "Shariefguda", "Bahilampur", "Gundlapally", "Manthapuri", "Tangutoor"],
        "Rajapet": ["Rajapet", "Challur", "Dudvenna", "Kurraram", "Potharam", "Raghavapuram", "Singaram"],
        "Turkapally": ["Turkapally", "Dharmaram", "Gandamalla", "Gopirajpally", "Madhavapur", "Rusthapur", "Venkatapur"],
        "M.Turkapally": ["M.Turkapally", "Chinnaturkapally", "Dharmaram", "Munigadapa", "Peddaturkapally", "Velpu Gonda"],
        "Motakondur": ["Motakondur", "Achanapally", "Chamalapally", "Gopalapuram", "Matedu", "Mutireddygudem"],
        "Atmakur (M)": ["Atmakur", "Kapkarthi", "Koremula", "Modugula", "Pallerla", "Rachapally", "Sarvepally", "Thukkapur"],
        "Gundala": ["Gundala", "Anantharam", "Brahmanapally", "Galanikota", "Sudhanpally", "Thurpu Pally", "Veldevi"],
        "Addagudur": ["Addagudur", "Chinna Padishala", "Chirragudur", "Dharmaram", "Kanchinapally", "Repaka", "Veldevi"],
        "Mothkur": ["Mothkur (M)", "Ammanabolu", "Dattappagudem", "Kondagadapapa", "Musipatla", "Panigiri", "Raghunathapuram"]
    },
    "Hanamkonda": {
        "Hanamkonda": ["Hanamkonda (M Corp)", "Waddepally", "Lashkar Singaram", "Kumarpally", "Nayeemnagar", "Subedari", "Balasamudram"],
        "Kazipet": ["Kazipet (M Corp)", "Madikonda", "Bheemaram", "Kadipikonda", "Somidi", "Tharalapally", "Rampur"],
        "Bheemaram": ["Bheemaram", "Hasanparthy", "Pegadapalli", "Siddapur", "Mupparam", "Vangapahad"],
        "Inavolu": ["Inavolu", "Kakkiralapally", "Kondaparthy", "Panthani", "Punnole", "Singaram", "Vanaparthy"],
        "Hasanparthy": ["Hasanparthy", "Ananthasagar", "Bhimaram", "Devannapet", "Jayagiri", "Nagaram", "Sulthanpur"],
        "Velair": ["Velair", "Ghanpur", "Mallikudurla", "Peechara", "Salarpur", "Veleda", "Yerrabelli"],
        "Dharmasagar": ["Dharmasagar", "Chinthapally", "Devanoor", "Elkurthy", "Kyathampally", "Peddapendyala", "Unikicherla"],
        "Elkathurthy": ["Elkathurthy", "Bhavanipet", "Dandepally", "Jeelugula", "Keshavapur", "Suraram", "Thimmapur"],
        "Bheemadevarpalli": ["Bheemadevarpalli", "Kothakonda", "Manikhyapur", "Mustafapur", "Mulkanoor", "Rampur", "Vangara"],
        "Kamalapur": ["Kamalapur", "Gundlapally", "Madannapet", "Marripellagudem", "Nerella", "Shanigaram", "Uppal"],
        "Parkal": ["Parkal (M)", "Kammaripalli", "Nagaram", "Pocharam", "Rajupet", "Rayaparthy", "Vellampally"],
        "Nadikuda": ["Nadikuda", "Choutapally", "Kowkonda", "Musthyalapally", "Narsakkapally", "Rayapally", "Varikole"],
        "Damera": ["Damera", "Kogilwai", "Ladella", "Orugonda", "Pasargonda", "Puligilla", "Singarajupally"],
        "Shayampet": ["Shayampet", "Gatla Kaniparthy", "Hussainpally", "Kothaguda", "Mylaram", "Neredpally", "Thimmapur"]
    },
    "Warangal": {
        "Warangal": ["Warangal (M Corp)", "Ursu", "Mamnoor", "Gorrekunta", "Deshaipet", "Kashibugga", "Enumamula", "Kareemabad"],
        "Khila Warangal": ["Khila Warangal", "Bollikunta", "Mamnoor", "Nayeemnagar", "Thimmapur", "Vasalamarri", "Alankar"],
        "Geesugonda": ["Geesugonda", "Dharmaram", "Gorrekunta", "Elkurthy", "Komatapally", "Mogilicherla", "Ookal", "Vanchana Giri"],
        "Atmakur": ["Atmakur", "Agarpeta", "Brahmanapally", "Chowdlapally", "Housebujurg", "Neerukulla", "Penchikalpet"],
        "Wardhannapet": ["Wardhannapet (M)", "Bandautlapally", "Dharmaram", "Inavolu", "Kothapally", "Nallabelli", "Upparapally"],
        "Parvathagiri": ["Parvathagiri", "Choutapally", "Enugallu", "Gopapuram", "Kalleda", "Ravichettu Thanda", "Rollakal", "Somaram"],
        "Rayaparthy": ["Rayaparthy", "Burahanpally", "Gannaram", "Jayaramthanda", "Keshavapuram", "Konduru", "Mylaram", "Perika Gudem"],
        "Sangem": ["Sangem", "Ashwaranpally", "Chinthapally", "Gavarigudem", "Kapulakanaparthy", "Laxmipuram", "Mondrai", "Theegarajupally"],
        "Narsampet": ["Narsampet (M)", "Rajupet", "Maheswaram", "Dasaripally", "Itikalpally", "Kammapally", "Madhannapet", "Muthojipet"],
        "Chennaraopet": ["Chennaraopet", "Ameenabad", "Chennapur", "Jhalli", "Lingagiri", "Papaiahpally", "Thimmarainpahad", "Yellareddygudem"],
        "Duggondi": ["Duggondi", "Adaviyangapally", "Chalaparthy", "Girnibavi", "Mandapalli", "Nachinapally", "Ponakallu", "Togarragudem"],
        "Khanapur": ["Khanapur", "Ashoknagar", "Budharaopet", "Dharmaraopet", "Kothur", "Mangapet", "Raghavapuram"],
        "Nekkonda": ["Nekkonda", "Appalraopeta", "Chandrugonda", "Gotlakonda", "Madipally", "Peddakorpole", "Reddial", "Venkatapur"]
    },
    "Jangaon": {
        "Jangaon": ["Jangaon (M)", "Yeshwanthapur", "Chowdaram", "Champak Hills", "Peddapahad", "Siddankigudem", "Venkatigadda"],
        "Lingalaghanpur": ["Lingalaghanpur", "Chetoor", "Ghanpur", "Jeedikallu", "Kallikur", "Kothapally", "Nelapogula", "Vangapally"],
        "Bachannapet": ["Bachannapet", "Alimpur", "Bandanagaram", "Chinnaramcherla", "Itikalpally", "Keshireddypally", "Nagireddypally"],
        "Devaruppula": ["Devaruppula", "Chinna Madnoor", "Kamareddygudem", "Kolukonda", "Manpahad", "Pedda Madnoor", "Singarajupally"],
        "Narmetta": ["Narmetta", "Agapet", "Bommakur", "Gandiramaram", "Hanumanthapur", "Kankalapally", "Malkapur", "Veldanda"],
        "Tharigoppula": ["Tharigoppula", "Akkaraju Pally", "Bonthupally", "Kamalapur", "Mirzapur", "Narsapur", "Solipur"],
        "Raghunathpally": ["Raghunathpally", "Ashwaraopally", "Banjupally", "Fathashapur", "Kalasamudram", "Kanchanpally", "Madharam"],
        "Station Ghanpur": ["Station Ghanpur", "Chagallu", "Shivunipally", "Ippaguda", "Meedidapally", "Raghunathpally", "Venkadath"],
        "Chilpur": ["Chilpur", "Chinnapendyala", "Fatehpur", "Kondapur", "Lingampally", "Mallikadurla", "Nashkal"],
        "Zaffergadh": ["Zaffergadh", "Alimpur", "Appireddypally", "Koonoor", "Raghunathpally", "Suraram", "Thimmapur", "Uppugal"],
        "Palakurthi": ["Palakurthi", "Valmidi", "Dharmathanda", "Chennur", "Gudur", "Kandigatla", "Laxminarayanapuram", "Mutharam"],
        "Kodakandla": ["Kodakandla", "Edunuthula", "Kamepally", "Lakshmakkapally", "Mondrai", "Narsimhulagudem", "Ramavaram"]
    },
    "Mahabubabad": {
        "Mahabubabad": ["Mahabubabad (M)", "Bethole", "Kambalapally", "Anantharam", "Gumdudur", "Jamandlapally", "Musalimadugu", "Shikharam"],
        "Kuravi": ["Kuravi", "Balharshiguda", "Chinna Thanda", "Gundrathimadugu", "Kandalgudem", "Modugulagudem", "Seetarampuram"],
        "Dornakal": ["Dornakal (M)", "Chilkodu", "Ravigudem", "Andanalapadu", "Gollacherla", "Marriguda", "Perumandlagudem", "Vennaram"],
        "Maripeda": ["Maripeda (M)", "Neelikurthy", "Yellampeta", "Abbaipalem", "Dharmaram", "Galivarigudem", "Rampur", "Thanamcherla"],
        "Narsimhulapet": ["Narsimhulapet", "Agapet", "Danthalapalle", "Jayapuram", "Komatlagudem", "Peddanagaram", "Reponi"],
        "Danthalapalle": ["Danthalapalle", "Bommakkapally", "Datla", "Gunturpally", "Kummarigudem", "Peddagopathi", "Vepalasingaram"],
        "Garla": ["Garla", "Budidampadu", "Gopalapuram", "Kalluru", "Mulkanoor", "Muthyalamma Gudem", "Rampur", "Seripuram"],
        "Bayyaram": ["Bayyaram", "Gandampally", "Garla", "Kambalapally", "Kothaguda", "Motlatothapally", "Pandipampula"],
        "Kesamudram": ["Kesamudram", "Inugurthy", "Korukondapally", "Arpanapally", "Berigudem", "Dhanasiri", "Intikanne", "Upparapally"],
        "Inugurthy": ["Inugurthy", "Chinna Mupparam", "Komatlagudem", "Maddulapally", "Pedda Mupparam", "Singaram"],
        "Nellikudur": ["Nellikudur", "Ali Nagar", "Brahmana Kothapally", "Chinna Mupparam", "Erra Cheruvu", "Madharam", "Narsimhulapet"],
        "Gudur": ["Gudur", "Ayodhyapur", "Bhupathipet", "Chinna Gudur", "Kongarigudem", "Matwada", "Narsapur", "Ponugodu"],
        "Kothaguda": ["Kothaguda", "Bavurugonda", "Gangaram", "Gudur", "Komatlagudem", "Musalimadugu", "Pogallapally"],
        "Gangaram": ["Gangaram", "Chintaguda", "Duginepally", "Komaram", "Kothaguda", "Madaguda", "Mamillagudem"],
        "Chinna Gudur": ["Chinna Gudur", "Chinna Nagaram", "Jayaram Thanda", "Kothapally", "Uggampally", "Vidyasagar"],
        "Seerole": ["Seerole", "Komatlagudem", "Madharam", "Malkapur", "Narsimhulapet", "Peddanagaram"]
    },
    "Jayashankar Bhupalpally": {
        "Bhupalpally": ["Bhupalpally (M)", "Kompally", "Gorlaveedu", "Jangadupally", "Kamalapur", "Moranchapally", "Nawabpet", "Pambapur"],
        "Chityal": ["Chityal", "Giddamutharam", "Jadalpalli", "Kailapur", "Mucherla", "Nainpaka", "Peddapur", "Thirumalapur"],
        "Ghanpur (Mulug)": ["Ghanpur", "Appanapally", "Bhudharaopet", "Chelpur", "Gandhinagar", "Kondapur", "Mylaram"],
        "Regonda": ["Regonda", "Roopireddypally", "Kanakapoor", "Chennapur", "Jagannadhpur", "Madathapally", "Repaka", "Sulthanpur"],
        "Mogullapally": ["Mogullapally", "Ankushapur", "Gundlakarthi", "Issipet", "Motlapally", "Mulkalapally", "Peddapur", "Rangapur"],
        "Tekumatla": ["Tekumatla", "Ankushapur", "Dubbagula", "Gaddalapally", "Kundanpally", "Raghavapur", "Venkatraopally"],
        "Malhar Rao": ["Malhar Rao", "Edlapally", "Khammampally", "Kondampet", "Mallaram", "Manthani", "Tadicherla"],
        "Kataram": ["Kataram", "Bayyaram", "Chintakani", "Danthanpally", "Gangaram", "Kothapally", "Medaram", "Sundarajupally"],
        "Mahadevpur": ["Mahadevpur", "Annaram", "Bommepally", "Kaleshwaram", "Medigadda", "Palimela", "Suraram"],
        "Palimela": ["Palimela", "Damarakunta", "Lenkalagadda", "Modumunja", "Pankena", "Sarvaipet"],
        "Mutharam": ["Mutharam", "Adavisrirampur", "Dharmaram", "Khammampally", "Odedu", "Potaram", "Sarvaipet"]
    },
    "Mulugu": {
        "Mulugu": ["Mulugu", "Bandaru", "Jaggannapet", "Incherla", "Kasimdevipeta", "Madhanapally", "Mallampally", "Pathipally"],
        "Venkatapur": ["Venkatapur", "Palampet (Ramappa)", "Laxmipuram", "Appapur", "Chinna Kothapally", "Narsapur", "Ramanakkapet"],
        "Govindaraopet": ["Govindaraopet", "Pasra", "Chalvai", "Garlavoddu", "Laknavaram", "Marlapally", "Rangapur"],
        "Tadvai (Sammakka Sarakka)": ["Tadvai", "Medaram", "Katapur", "Kalvapally", "Narlapur", "Oorattam", "Project Nagar"],
        "Eturnagaram": ["Eturnagaram", "Chinnaboinapally", "Dudekulapally", "Kondai", "Mullakatta", "Ramannagudem", "Roheer"],
        "Mangapet": ["Mangapet", "Akinepally Mallaram", "Brahmanapally", "Cherupally", "Kathigudem", "Komshipally", "Narsimhasagar"],
        "Kannaigudem": ["Kannaigudem", "Bussapur", "Chityala", "Gurrevula", "Muppanapally", "Rajannapet", "Thurpu Gudem"],
        "Wazeed": ["Wazeed", "Arunachalapuram", "Chelluru", "Kongala", "Morammagudem", "Penugolu", "Tekulagudem"],
        "Venkatapuram": ["Venkatapuram", "Alubaka", "Bojjiguppa", "Edira", "Marikala", "Morampally", "Patha Cheruvu"]
    }
}

# High-Speed Cached Google Sheets Connector
@st.cache_resource(ttl=300)
def get_cached_worksheet():
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
        return sh, None
    except Exception as e:
        return None, str(e)

def get_worksheet():
    return get_cached_worksheet()

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
        clean_k = k.strip().replace('"', '').replace("'", "")
        if len(clean_k) > 15 and clean_k not in seen:
            seen.add(clean_k)
            deduped.append(clean_k)
    return deduped

# Automated Fast Image Enhancement Pipeline
def enhance_image_for_ocr(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        if w > 1600 or h > 1600:
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        elif w < 900 or h < 900:
            scale_factor = max(900 / w, 900 / h)
            new_size = (int(w * scale_factor), int(h * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        gray = img.convert('L')
        enhanced_contrast = ImageEnhance.Contrast(gray).enhance(1.8)
        sharpened = ImageEnhance.Sharpness(enhanced_contrast).enhance(2.0)
        
        out_buf = io.BytesIO()
        sharpened.save(out_buf, format="JPEG", quality=85)
        return out_buf.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, "image/jpeg"

# Instant Text Parsing Rules (< 0.001s)
def extract_fields_from_raw_text(text):
    normalized = re.sub(r'[\r\t\f\v]', ' ', text)
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
    return parsed

# Engine 1: Instant Offline Digital PDF Engine (< 0.05s)
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

        parsed = extract_fields_from_raw_text(full_text)
        return parsed, full_text
    except Exception:
        return {}, ""

# Fast JSON parser
def clean_and_parse_json(text_content):
    txt = text_content.strip()
    match = re.search(r'(\{[\s\S]*\})', txt)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    try:
        return json.loads(txt)
    except Exception:
        return extract_fields_from_raw_text(text_content)

# Engine 2: 1-Second Google Lens AI Vision
def parse_with_google_lens(file_bytes, mime_type, api_keys):
    if not api_keys:
        return {}, "", "No API Keys Configured"

    b64_data = base64.b64encode(file_bytes).decode('utf-8')
    prompt_text = """You are an expert Google Lens OCR system scanning a CEO Telangana Form-18 Acknowledgement Slip / Graduate Voter Slip.
Extract these exact fields as JSON:
{
  "application_id": "starts with 'F' and digits, e.g. F180928310521426",
  "applicant_name": "Full Applicant Name",
  "gender": "Male or Female",
  "relation_name": "Father / Husband Name",
  "house_number": "House Number",
  "mlc_constituency": "Warangal-Khammam-Nalgonda",
  "district_name": "District Name",
  "current_status": "Submitted",
  "ocr_full_text": "text preview"
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

    models = ["gemini-1.5-flash", "gemini-2.0-flash"]
    last_err = ""

    for key in api_keys:
        clean_key = key.strip()
        headers = {
            "x-goog-api-key": clean_key,
            "Content-Type": "application/json"
        }

        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    body = res.json()
                    text_content = body["candidates"][0]["content"]["parts"][0]["text"]
                    data = clean_and_parse_json(text_content)
                    
                    st_val = data.get("current_status", "")
                    if "application" in st_val.lower() or "f18" in st_val.lower() or not st_val:
                        data["current_status"] = "Submitted"

                    ocr_raw = data.pop("ocr_full_text", "")
                    return data, ocr_raw, "OK"
                else:
                    last_err = f"API Status {res.status_code}"
            except Exception as e:
                last_err = str(e)
                continue

    return {}, "", last_err

# Engine 3: Local Offline Tesseract OCR Fallback (< 0.8s)
def parse_with_offline_ocr(file_bytes):
    if not HAS_PYTESSERACT:
        return {}, "", "Pytesseract Not Installed"
    try:
        img = Image.open(io.BytesIO(file_bytes))
        raw_text = pytesseract.image_to_string(img)
        if len(raw_text.strip()) > 15:
            data = extract_fields_from_raw_text(raw_text)
            if data.get("application_id") or data.get("applicant_name"):
                return data, raw_text, "OK"
        return {}, raw_text, "No Text Found"
    except Exception as ex:
        return {}, "", str(ex)

# Universal Multi-Device Router
def extract_universal_document(uploaded_file, file_bytes, api_keys):
    filename = uploaded_file.name.lower() if hasattr(uploaded_file, 'name') else "image.jpg"

    if filename.endswith(".pdf"):
        data, raw_txt = parse_acknowledgement_pdf(file_bytes)
        if data.get("application_id") or data.get("applicant_name"):
            return data, raw_txt, "PDF Text Engine", ""

    enhanced_bytes, mime_type = enhance_image_for_ocr(file_bytes)

    lens_data, raw_txt, err_detail = parse_with_google_lens(enhanced_bytes, mime_type, api_keys)
    if lens_data.get("application_id") or lens_data.get("applicant_name"):
        return lens_data, raw_txt, "Google Lens AI", ""

    tess_data, tess_txt, tess_err = parse_with_offline_ocr(enhanced_bytes)
    if tess_data.get("application_id") or tess_data.get("applicant_name"):
        return tess_data, tess_txt, "Offline OCR Engine", ""

    return {}, "", "Failed", err_detail

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

def check_duplicate_local(app_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM local_records WHERE application_id = ?", (app_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def record_local_entry(app_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO local_records VALUES (?, ?, ?)",
              (app_id, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

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

widget_keys = {
    "inp_app_id": "",
    "inp_name": "",
    "inp_gender": "",
    "inp_relation": "",
    "inp_house_no": "",
    "inp_mlc": "Warangal-Khammam-Nalgonda",
    "inp_status": "Submitted",
    "inp_ref_name": "",
    "inp_mobile_no": "",
    "inp_remarks": "",
    "sel_district": "Khammam",
    "sel_mandal": "Khammam Urban",
    "sel_village": "Khammam (M Corp)",
    "custom_village_input": "",
    "last_file_hash": "",
    "lens_detected_raw": "",
    "last_engine": "",
    "last_saved_voter": None,
    "clear_form_trigger": False
}

for k, default_val in widget_keys.items():
    if k not in st.session_state:
        st.session_state[k] = default_val

# Login Screen
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
                🔍 <strong>Fast 1-Second Auto Scanner:</strong><br>
                Upload any Form-18 PDF, WhatsApp screenshot, or phone photo. Data immediately auto-fills into the dialogue boxes.
            </p>
        </div>
        """, unsafe_allow_html=True)

        render_footer()

    st.stop()

# Workspace
configured_keys = get_configured_api_keys()

with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <span style="font-size:24px;">🚗</span>
        <h3 style="margin:0; color:#E61A8D;">BRS War Room</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**Operator:** {st.session_state.full_name}")
    st.markdown(f"**Role:** `{st.session_state.role}`")
    st.caption(f"🔑 Active OCR Engines Loaded: **{len(configured_keys)} Keys**")
    if st.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()

    with st.expander("⚙️ Gemini API Key (For Google Lens)"):
        st.caption("Active keys loaded securely from Streamlit Secrets.")
        custom_k = st.text_input("Add Additional Key", type="password", value=st.session_state.get("custom_gemini_key", ""))
        if custom_k:
            st.session_state["custom_gemini_key"] = custom_k
            configured_keys = get_configured_api_keys()

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
        st.markdown("""
        <div class="lens-header-card">
            <div class="lens-icon-badge">⚡</div>
            <div>
                <div class="lens-title">Instant Form-18 Scanner</div>
                <div class="lens-desc">Ultra-Fast Autofill: PDFs (< 0.1s) & Photos / JPEGs (1s)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        input_choice = st.radio("Choose Input Method:", ["📁 Upload File (Screenshot/JPEG/PDF)", "📷 Live Camera Scan"], horizontal=True)

        target_file_obj = None
        target_bytes = None

        if input_choice == "📁 Upload File (Screenshot/JPEG/PDF)":
            target_file_obj = st.file_uploader(
                "Drop Form-18 Screenshot or Document",
                type=["pdf", "png", "jpg", "jpeg", "webp"],
                key="form18_universal_uploader"
            )
            if target_file_obj:
                target_bytes = target_file_obj.getvalue()
        else:
            cam_pic = st.camera_input("Point camera at Form-18 slip", key="form18_camera_scanner")
            if cam_pic:
                target_file_obj = cam_pic
                target_bytes = cam_pic.getvalue()

        if target_bytes:
            current_hash = hashlib.md5(target_bytes).hexdigest()

            if st.session_state["last_file_hash"] != current_hash:
                with st.spinner("⚡ Extracting data directly to dialogue boxes..."):
                    extracted_info, raw_ocr, engine_used, err_detail = extract_universal_document(target_file_obj, target_bytes, configured_keys)

                    if extracted_info.get("application_id") or extracted_info.get("applicant_name"):
                        st.session_state["inp_app_id"] = str(extracted_info.get("application_id", ""))
                        st.session_state["inp_name"] = str(extracted_info.get("applicant_name", ""))
                        st.session_state["inp_gender"] = str(extracted_info.get("gender", ""))
                        st.session_state["inp_relation"] = str(extracted_info.get("relation_name", ""))
                        st.session_state["inp_house_no"] = str(extracted_info.get("house_number", ""))
                        st.session_state["inp_mlc"] = str(extracted_info.get("mlc_constituency", "")) or "Warangal-Khammam-Nalgonda"
                        st.session_state["inp_status"] = str(extracted_info.get("current_status", "Submitted"))
                        
                        detected_dist = str(extracted_info.get("district_name", "")).strip().lower()
                        for d_name in list(JURISDICTION_DATA.keys()):
                            if d_name.lower() in detected_dist or detected_dist in d_name.lower():
                                st.session_state["sel_district"] = d_name
                                available_m = sorted(list(JURISDICTION_DATA[d_name].keys()))
                                st.session_state["sel_mandal"] = available_m[0]
                                available_v = sorted(JURISDICTION_DATA[d_name][available_m[0]]) + ["Other / Enter Manually"]
                                st.session_state["sel_village"] = available_v[0]
                                break

                        st.session_state["lens_detected_raw"] = raw_ocr
                        st.session_state["last_file_hash"] = current_hash
                        st.session_state["last_engine"] = engine_used
                        st.rerun()
                    else:
                        st.error(f"Could not parse document. {err_detail}")

        if st.session_state["inp_app_id"]:
            engine_label = st.session_state.get("last_engine", "Extracted")
            st.success(f"✅ **{engine_label}**: Autofilled **{st.session_state['inp_name']}** (`{st.session_state['inp_app_id']}`)")
            
            if st.session_state["lens_detected_raw"]:
                with st.expander("📋 Lens Detected Raw Text"):
                    st.text(st.session_state["lens_detected_raw"][:800])

    with data_col:
        st.markdown("#### 2. Review & Tag Jurisdiction Details")

        st.markdown('<div class="voter-card-container">', unsafe_allow_html=True)
        st.markdown("##### 👤 Applicant Information")
        c1, c2 = st.columns(2)
        app_id = c1.text_input("Application ID", key="inp_app_id")
        name = c2.text_input("Applicant Name", key="inp_name")

        c3, c4, c5 = st.columns(3)
        gender = c3.text_input("Gender", key="inp_gender")
        relation = c4.text_input("Relation Name", key="inp_relation")
        house_no = c5.text_input("House Number", key="inp_house_no")

        c6, c7 = st.columns(2)
        mlc_const = c6.text_input("Constituency", key="inp_mlc")
        status = c7.text_input("Status", key="inp_status")

        st.markdown("---")
        st.markdown("##### 📍 Tag Jurisdiction (Instant Sync)")
        
        all_districts = list(JURISDICTION_DATA.keys())
        if st.session_state["sel_district"] not in all_districts:
            st.session_state["sel_district"] = all_districts[0]

        selected_district = st.selectbox(
            "Select District", 
            all_districts, 
            key="sel_district"
        )
        
        available_mandals = sorted(list(JURISDICTION_DATA[selected_district].keys()))
        if st.session_state.get("sel_mandal") not in available_mandals:
            st.session_state["sel_mandal"] = available_mandals[0]

        selected_mandal = st.selectbox(
            "Select Mandal", 
            available_mandals, 
            key="sel_mandal"
        )
        
        village_options = sorted(JURISDICTION_DATA[selected_district][selected_mandal]) + ["Other / Enter Manually"]
        if st.session_state.get("sel_village") not in village_options:
            st.session_state["sel_village"] = village_options[0]

        selected_village = st.selectbox(
            "Select Revenue Village / Ward", 
            village_options, 
            key="sel_village"
        )
        
        if selected_village == "Other / Enter Manually":
            final_village = st.text_input("Enter Revenue Village / Ward / Colony Name", placeholder="Type village or ward name", key="custom_village_input")
        else:
            final_village = selected_village

        st.markdown("---")
        st.markdown("##### 🤝 Party Volunteer & Reference Details")
        r1, r2 = st.columns(2)
        ref_name = r1.text_input("Party Reference / Cadre Name", placeholder="Mandal Incharge / Cadre Name", key="inp_ref_name")
        mobile_no = r2.text_input("Voter Mobile Number", placeholder="10-digit mobile number", key="inp_mobile_no")
        
        clean_mobile = re.sub(r'[^0-9]', '', mobile_no.strip())
        is_mobile_valid = True
        if clean_mobile:
            if not re.match(r'^[6-9]\d{9}$', clean_mobile):
                is_mobile_valid = False
                st.caption("⚠️ Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")

        remarks = st.text_area("Remarks / Notes", placeholder="e.g., Form-18 acknowledged, Degree certificate verified, Supporter", key="inp_remarks")

        save_btn = st.button("🚗 Save & Submit to BRS Voter Database", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 📲 1-Click WhatsApp Voter Confirmation Card
        if st.session_state.get("last_saved_voter"):
            voter = st.session_state["last_saved_voter"]
            v_name = voter.get("name", "")
            v_id = voter.get("app_id", "")
            v_phone = voter.get("mobile", "")
            v_const = voter.get("constituency", "Warangal-Khammam-Nalgonda")

            st.markdown('<div class="wa-card">', unsafe_allow_html=True)
            st.markdown(f"**🎉 Successfully Registered:** `{v_name}` ({v_id})")
            
            if v_phone and re.match(r'^[6-9]\d{9}$', v_phone):
                msg_body = (
                    f"🌸 *భారత రాష్ట్ర సమితి (BRS) — War Room*\n\n"
                    f"నమస్కారం {v_name} గారు,\n"
                    f"మీ MLC గ్రాడ్యుయేట్ ఓటర్ నమోదు (Form-18) దరఖాస్తు విజయవంతంగా BRS War Room రికార్డులలో నమోదయింది.\n\n"
                    f"📌 *Application ID:* {v_id}\n"
                    f"📍 *Constituency:* {v_const}\n\n"
                    f"నల్గొండ - వరంగల్ - ఖమ్మం గ్రాడ్యుయేట్ ఎమ్మెల్సీ ఎన్నికల్లో మన ఓటు — *కారు గుర్తుకే* 🚗"
                )
                encoded_msg = urllib.parse.quote(msg_body)
                wa_url = f"https://wa.me/91{v_phone}?text={encoded_msg}"
                st.link_button(f"📲 Send Instant WhatsApp Confirmation to {v_phone}", wa_url, use_container_width=True)
            else:
                st.caption("ℹ️ Voter mobile number not provided. Record saved to Central Database.")
            st.markdown('</div>', unsafe_allow_html=True)

        if save_btn:
            if not app_id or not name:
                st.error("Application ID and Applicant Name are mandatory.")
            elif clean_mobile and not is_mobile_valid:
                st.error("Please provide a valid 10-digit mobile number or leave it blank.")
            else:
                if check_duplicate_local(app_id):
                    log_duplicate(app_id, name, st.session_state.username)
                    st.warning(f"⚠️ Duplicate Detected! Application ID {app_id} already exists in database. Logged in audit trail.")
                else:
                    ws, err = get_worksheet()
                    if ws is None:
                        st.error(f"Database Connection Failed: {err}")
                    else:
                        try:
                            new_entry = [
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                app_id, name, gender, relation, house_no,
                                mlc_const, selected_district, status,
                                selected_district, selected_mandal, final_village,
                                ref_name, clean_mobile, remarks, st.session_state.username
                            ]
                            ws.append_row(new_entry)
                            record_local_entry(app_id, name)
                            
                            st.session_state["last_saved_voter"] = {
                                "name": name,
                                "app_id": app_id,
                                "mobile": clean_mobile,
                                "constituency": mlc_const
                            }

                            st.success(f"🎉 Successfully Ingested: {name} ({app_id}) to BRS Central Records!")
                            
                            st.session_state["clear_form_trigger"] = True
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error appending row: {ex}")

    render_footer()

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

                    today_str = datetime.now().strftime("%Y-%m-%d")
                    today_votes = df[df["Timestamp"].str.startswith(today_str)].shape[0] if "Timestamp" in df.columns else 0

                    m1, m2, m3, m4, m5 = st.columns(5)
                    total_votes = len(df)
                    unique_voters = df["Application ID"].nunique() if "Application ID" in df.columns else total_votes
                    duplicate_attempts = len(dup_df)
                    active_operators = df["Operator Username"].nunique() if "Operator Username" in df.columns else 1

                    m1.metric("Total Ingested Votes", f"{total_votes:,}")
                    m2.metric("Today's Mobilization", f"{today_votes:,}")
                    m3.metric("Unique Verified Voters", f"{unique_voters:,}")
                    m4.metric("Duplicates Filtered", f"{duplicate_attempts:,}")
                    m5.metric("Active War Room Cadre", f"{active_operators}")

                    st.write("")
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Complete Voter Database (.CSV)",
                        data=csv_bytes,
                        file_name=f"BRS_MLC_Voters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                    st.divider()

                    lead_col1, lead_col2 = st.columns(2)
                    
                    with lead_col1:
                        st.subheader("🏆 Top Operator Leaderboard")
                        if "Operator Username" in df.columns:
                            operator_counts = df["Operator Username"].value_counts().reset_index()
                            operator_counts.columns = ["Operator", "Voters Ingested"]
                            st.dataframe(operator_counts, use_container_width=True, hide_index=True)

                    with lead_col2:
                        st.subheader("🤝 Top Party Reference / Cadre")
                        if "Reference Name" in df.columns:
                            valid_refs = df[df["Reference Name"].str.strip() != ""]
                            if not valid_refs.empty:
                                ref_counts = valid_refs["Reference Name"].value_counts().head(10).reset_index()
                                ref_counts.columns = ["Reference / Cadre", "Total Mobilized"]
                                st.dataframe(ref_counts, use_container_width=True, hide_index=True)
                            else:
                                st.caption("No party references tagged yet.")

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

        render_footer()
