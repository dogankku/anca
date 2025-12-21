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

# --- 1. AYARLAR VE TASARIM (DARK MODE / KOYU TEMA) ---
st.set_page_config(
    page_title="AKÇA CRM v3.1",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Göz Dostu Profesyonel Koyu Tema CSS
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Yan Menü (Sidebar) */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Metrik Kartları (KPI) */
    div[data-testid="metric-container"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 15px;
        border-radius: 8px;
        color: white;
    }
    div[data-testid="metric-container"] label {
        color: #9ca3af !important; /* Gri başlık */
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #60a5fa !important; /* Mavi rakam */
    }
    
    /* Tablo Başlıkları */
    thead tr th {
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border-bottom: 2px solid #374151 !important;
    }
    tbody tr td {
        color: #e5e7eb !important;
        background-color: #0e1117 !important;
    }
    
    /* Butonlar */
    div.stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    /* Input Alanları */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput {
        background-color: #1f2937 !important;
        color: white !important;
        border: 1px solid #374151 !important;
    }
    
    /* AI Asistan Kutusu */
    .stAlert {
        background-color: #1f2937;
        color: #e5e7eb;
        border: 1px solid #374151;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

if 'sepet' not in st.session_state:
    st.session_state.sepet = []

def check_password():
    """Güvenli Giriş Ekranı"""
    def password_entered():
        if (st.session_state["login_user"] in st.secrets["users"] and 
            st.session_state["login_pass"] == st.secrets["users"][st.session_state["login_user"]]):
            st.session_state["password_correct"] = True
            del st.session_state["login_pass"]
            del st.session_state["login_user"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color:#60a5fa;'>🦅 AKÇA CRM</h1>", unsafe_allow_html=True)
            st.text_input("Kullanıcı Adı", key="login_user")
            st.text_input("Şifre", type="password", key="login_pass")
            st.button("Giriş Yap", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Kullanıcı Adı", key="login_user_retry")
        st.text_input("Şifre", type="password", key="login_pass_retry")
        st.button("Giriş Yap", on_click=password_entered)
        st.error("Hatalı giriş.")
        return False
    else:
        return True

def get_google_sheet_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def mail_gonder_generic(alici_email, konu, html_icerik):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["server"]
        smtp_port = st.secrets["email"]["port"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Akça Rulman <{sender_email}>"
        msg['To'] = alici_email
        msg['Subject'] = konu
        msg.attach(MIMEText(html_icerik, 'html'))

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4 
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, alici_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- YAPAY ZEKA SİMÜLASYONU ---
def yapay_zeka_analizi(df_teklif, df_ziyaret):
    oneri_listesi = []
    bugun = datetime.now()
    if not df_ziyaret.empty and "Tarih" in df_ziyaret.columns:
        df_ziyaret['Tarih'] = pd.to_datetime(df_ziyaret['Tarih'], errors='coerce')
        son_ziyaretler = df_ziyaret.groupby("Firma Adı")['Tarih'].max()
        for firma, tarih in son_ziyaretler.items():
            gecen_gun = (bugun - tarih).days
            if gecen_gun > 30:
                oneri_listesi.append(f"⚠️ **{firma}** firmasını {gecen_gun} gündür ziyaret etmedin!")
    
    if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
        ciro = df_teklif['Toplam Tutar'].sum()
        if ciro < 200000: 
            oneri_listesi.append("📉 Bu ay hedefin gerisindesin, teklif sayısını artır.")
        else:
            oneri_listesi.append("🔥 Ciro hedefine yaklaşıyorsun, harika!")
    
    if not oneri_listesi: oneri_listesi.append("✅ Her şey yolunda, iyi çalışmalar!")
    return oneri_listesi

# --- ANA UYGULAMA ---
if check_password():
    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
        ws_ziyaret = sh.worksheet("Ziyaretler")
        ws_teklif = sh.worksheet("Teklifler")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        
        df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
        df_teklif = pd.DataFrame(ws_teklif.get_all_records())
        df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
        
        # Sayısal Dönüşüm (Virgül/Nokta Hatası Önleyici)
        if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
             df_teklif['Toplam Tutar'] = pd.to_numeric(
                 df_teklif['Toplam Tutar'].astype(str).str.replace(r'[^\d.]', '', regex=True), 
                 errors='coerce'
             ).fillna(0)
    except Exception as e:
        st.error(f"Veri Bağlantı Hatası: {e}. Secrets ayarlarını kontrol et.")
        st.stop()

    # --- SIDEBAR MENÜ ---
    with st.sidebar:
        st.title("🦅 AKÇA CRM")
        st.markdown("<span style='color:gray'>Sürüm: 3.1 Dark</span>", unsafe_allow_html=True)
        menu = st.radio("Menü", ["🏠 Dashboard", "👥 Müşteriler", "💰 Teklif Oluştur", "📍 Ziyaret Gir", "⚙️ Ayarlar"])
        st.markdown("---")
        st.markdown("### 🤖 AI Asistanı")
        oneriler = yapay_zeka_analizi(df_teklif, df_ziyaret)
        for oneri in oneriler: st.info(oneri)

    # --- 1. DASHBOARD ---
    if menu == "🏠 Dashboard":
        st.markdown("## 🚀 Satış Performansı")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        toplam_ciro = df_teklif['Toplam Tutar'].sum() if not df_teklif.empty else 0
        bekleyen = len(df_teklif[df_teklif['Durum']=='Beklemede']) if not df_teklif.empty and 'Durum' in df_teklif.columns else 0
        
        kpi1.metric("Toplam Ciro", f"{toplam_ciro:,.0f} TL")
        kpi2.metric("Ziyaret", len(df_ziyaret))
        kpi3.metric("Teklif Sayısı", len(df_teklif))
        kpi4.metric("Bekleyen İşler", bekleyen)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            if not df_teklif.empty and "Durum" in df_teklif.columns:
                st.subheader("Teklif Durumları")
                # HATA DÜZELTİLDİ: px.pie kullanıldı
                fig = px.pie(df_teklif, names='Durum', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Grafik için veri yok.")
                
        with c2:
            if not df_teklif.empty and "Tarih" in df_teklif.columns:
                st.subheader("Aylık Satış Trendi")
                df_teklif['Tarih'] = pd.to_datetime(df_teklif['Tarih'], errors='coerce')
                trend = df_teklif.groupby(df_teklif['Tarih'].dt.strftime('%Y-%m'))['Toplam Tutar'].sum().reset_index()
                st.bar_chart(trend.set_index('Tarih'))
            else:
                st.info("Grafik için veri yok.")

    # --- 2. MÜŞTERİLER ---
    elif menu == "👥 Müşteriler":
        st.markdown("## 👥 Müşteri Listesi")
        musteriler = set()
        if not df_ziyaret.empty and "Firma Adı" in df_ziyaret.columns: musteriler.update(df_ziyaret["Firma Adı"].unique())
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(pd.DataFrame(list(musteriler), columns=["Firma Adı"]), use_container_width=True, height=400)
        with col2:
            st.info("💡 Müşterilerin üzerine tıklayarak detay görebilirsiniz (Yakında eklenecek).")

    # --- 3. TEKLİF OLUŞTUR ---
    elif menu == "💰 Teklif Oluştur":
        st.markdown("## 💰 Profesyonel Teklif Hazırla")
        
        # Müşteri Seçimi Kartı
        with st.container():
            c1, c2, c3 = st.columns(3)
            musteri_list = ["Seçiniz"] + list(df_ziyaret["Firma Adı"].unique()) if not df_ziyaret.empty else []
            secilen_mus = c1.selectbox("Müşteri", musteri_list)
            tarih = c2.date_input("Tarih", datetime.today())
            para = c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])
        
        st.markdown("---")
        
        # Ürün Ekleme Kartı
        col_u1, col_u2 = st.columns([3, 1])
        urunler = [""] + df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else []
        u_secim = col_u1.selectbox("Listeden Ürün Seç", urunler)
        
        # Otomatik Fiyat
        fiyat_oto = 0.0
        if u_secim and not df_fiyat.empty:
            try: fiyat_oto = float(str(df_fiyat[df_fiyat['Urun Adi']==u_secim].iloc[0]['Birim Fiyat']).replace(",", "."))
            except: pass
        
        u_manuel = col_u1.text_input("Ürün Adı (veya Manuel Yaz)", value=u_secim)
        
        adet = col_u2.number_input("Adet", 1, 1000, 1)
        fiyat = col_u2.number_input("Birim Fiyat", value=fiyat_oto)
        
        if st.button("Sepete Ekle 🛒"):
            st.session_state.sepet.append({"Urun": u_manuel, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
            st.success("Ürün eklendi.")
            
        # Sepet Tablosu
        if st.session_state.sepet:
            st.markdown("### 🛒 Sepet Özeti")
            st.table(pd.DataFrame(st.session_state.sepet))
            
            toplam = sum(x['Toplam'] for x in st.session_state.sepet)
            col_b1, col_b2 = st.columns([3, 1])
            with col_b2:
                st.markdown(f"<div style='background-color:#1f2937; padding:10px; border-radius:5px; text-align:center; color:white;'><h3>{toplam:,.2f} {para}</h3>Topam Tutar</div>", unsafe_allow_html=True)
                st.write("")
                if st.button("✅ Teklifi Kaydet"):
                    ozet = f"{len(st.session_state.sepet)} Kalem"
                    ws_teklif.append_row([str(tarih), secilen_mus, ozet, 1, toplam, toplam, "Beklemede", para])
                    st.session_state.sepet = []
                    st.success("Teklif başarıyla kaydedildi!")

    # --- 4. ZİYARET GİRİŞİ ---
    elif menu == "📍 Ziyaret Gir":
        st.markdown("## 📍 Saha Ziyaret Raporu")
        with st.form("ziyaret_form"):
            c1, c2 = st.columns(2)
            f = c1.text_input("Firma Adı")
            k = c2.text_input("Görüşülen Kişi")
            d = c2.selectbox("Sonuç", ["Olumlu", "Teklif Verildi", "Satış", "Red"])
            notlar = st.text_area("Görüşme Notları")
            
            if st.form_submit_button("Raporu Kaydet"):
                ws_ziyaret.append_row([str(datetime.today().date()), f, "", k, "", "", d, "", "", "", "", "", "", "", notlar])
                st.success("Ziyaret sisteme işlendi.")

    # --- 5. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        st.markdown("## ⚙️ Ürün Yönetimi")
        st.dataframe(df_fiyat, use_container_width=True)
        
        with st.expander("➕ Yeni Ürün Ekle"):
            c1, c2, c3 = st.columns(3)
            yk = c1.text_input("Kod")
            ya = c2.text_input("Ad")
            yf = c3.number_input("Fiyat")
            if st.button("Listeye Ekle"):
                ws_fiyat.append_row([yk, ya, yf, "TL"])
                st.success("Ürün eklendi.")
