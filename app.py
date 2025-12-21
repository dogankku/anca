import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import time

# --- 1. AYARLAR VE TASARIM (PREMIUM DARK) ---
st.set_page_config(
    page_title="AKÇA CRM Pro",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {background-color: #0e1117; color: #f0f2f6;}
    section[data-testid="stSidebar"] {background-color: #161b22;}
    div[data-testid="metric-container"] {
        background-color: #262730; border: 1px solid #41424b; padding: 15px; border-radius: 8px;
    }
    div[data-testid="metric-container"] label {color: #a3a8b8;}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {color: #4da6ff;}
    thead tr th {background-color: #1f2937 !important; color: #4da6ff !important;}
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput, .stTextArea textarea {
        background-color: #1c1f26 !important; color: white !important; border: 1px solid #41424b !important;
    }
    div.stButton > button {
        background-color: #238636; color: white; border-radius: 6px; width: 100%; font-weight: bold;
    }
    div.stButton > button:hover {background-color: #2ea043;}
</style>
""", unsafe_allow_html=True)

# --- 2. BAĞLANTILAR VE FONKSİYONLAR ---

if 'sepet' not in st.session_state: st.session_state.sepet = []

def check_password():
    def password_entered():
        if (st.session_state["login_user"] in st.secrets["users"] and 
            st.session_state["login_pass"] == st.secrets["users"][st.session_state["login_user"]]):
            st.session_state["password_correct"] = True
            del st.session_state["login_pass"]
            del st.session_state["login_user"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<h1 style='text-align:center; color:#4da6ff;'>🦅 AKÇA CRM</h1>", unsafe_allow_html=True)
            st.text_input("Kullanıcı", key="login_user")
            st.text_input("Şifre", type="password", key="login_pass")
            st.button("Giriş Yap", on_click=password_entered)
        return False
    return True

def get_google_sheet_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- CACHE SİSTEMİ (HIZ LİMİTİ HATASINI ÇÖZEN KISIM) ---
# Bu fonksiyon veriyi çeker ve 5 dakika (300 saniye) boyunca hafızada tutar.
# Böylece her tıklamada Google'a gidip kota harcamaz.
@st.cache_data(ttl=300)
def verileri_yukle():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("Satis_Raporlari")
        
        # Sayfaları açmayı dene, yoksa oluştur (Hata önleyici)
        try: ws_musteri = sh.worksheet("Musteriler")
        except: 
            ws_musteri = sh.add_worksheet(title="Musteriler", rows="1000", cols="10")
            ws_musteri.append_row(["Firma Adı", "Yetkili", "Unvan", "Telefon", "Email", "Adres", "Konum", "Kayit Tarihi"])

        ws_ziyaret = sh.worksheet("Ziyaretler")
        ws_teklif = sh.worksheet("Teklifler")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")

        # Verileri Oku
        d_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
        d_teklif = pd.DataFrame(ws_teklif.get_all_records())
        d_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
        d_musteri = pd.DataFrame(ws_musteri.get_all_records())
        
        # Sayısal düzeltmeler
        if not d_teklif.empty and "Toplam Tutar" in d_teklif.columns:
             d_teklif['Toplam Tutar'] = pd.to_numeric(d_teklif['Toplam Tutar'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

        return d_musteri, d_ziyaret, d_teklif, d_fiyat
    except Exception as e:
        return None, None, None, None

def mail_gonder(alici, konu, html):
    try:
        sender = st.secrets["email"]["sender"]
        password = st.secrets["email"]["password"]
        msg = MIMEMultipart()
        msg['From'] = f"Akca Rulman Satis <{sender}>"
        msg['To'] = alici
        msg['Subject'] = konu
        msg.attach(MIMEText(html, 'html'))
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4
        
        server = smtplib.SMTP_SSL(st.secrets["email"]["server"], st.secrets["email"]["port"], context=ctx)
        server.login(sender, password)
        server.sendmail(sender, alici, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(e)
        return False

def teklif_html_olustur(musteri, sepet, top, isk, isk_tut, kdv, kdv_tut, gen_top, para, notlar):
    satirlar = ""
    for u in sepet:
        satirlar += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #ddd;">{u['Urun']}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd; text-align:center;">{u['Adet']}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd; text-align:right;">{u['Birim Fiyat']:,.2f}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd; text-align:right;">{u['Toplam']:,.2f}</td>
        </tr>"""
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 700px; margin: auto; padding: 20px; border: 1px solid #eee;">
            <div style="border-bottom: 3px solid #0056b3; padding-bottom: 10px; margin-bottom: 20px;">
                <h2 style="color: #0056b3; margin: 0;">AKÇA RULMAN</h2>
                <span style="font-size: 12px; color: #666;">Rulman & Güç Aktarım Sistemleri</span>
            </div>
            <p>Sayın <b>{musteri}</b> Yetkilisi,</p>
            <p>İlgilendiğiniz ürünler için hazırladığımız özel fiyat teklifi aşağıdadır.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr style="background-color: #f8f9fa; color: #0056b3;">
                    <th style="padding: 10px; text-align: left;">Ürün</th>
                    <th style="padding: 10px; text-align: center;">Miktar</th>
                    <th style="padding: 10px; text-align: right;">Birim</th>
                    <th style="padding: 10px; text-align: right;">Tutar</th>
                </tr>
                {satirlar}
            </table>
            
            <div style="margin-top: 20px; text-align: right;">
                <p>Ara Toplam: <b>{top:,.2f} {para}</b></p>
                <p style="color:red;">İskonto (%{isk}): -{isk_tut:,.2f} {para}</p>
                <p>KDV (%{kdv}): +{kdv_tut:,.2f} {para}</p>
                <div style="background-color: #0056b3; color: white; padding: 10px; display: inline-block; border-radius: 5px;">
                    GENEL TOPLAM: {gen_top:,.2f} {para}
                </div>
            </div>
            
            <div style="margin-top: 30px; background-color: #f1f1f1; padding: 15px; font-size: 12px;">
                <strong>Teklif Şartları
