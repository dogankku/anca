import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

# --- 1. AYARLAR VE TASARIM (PREMIUM UI) ---
st.set_page_config(
    page_title="AKÇA CRM v3.0",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS ile Profesyonel Görünüm
st.markdown("""
<style>
    /* Ana Arka Plan ve Fontlar */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Metrik Kartları (KPI) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: #2e86de;
    }
    
    /* Butonlar */
    div.stButton > button {
        background: linear-gradient(90deg, #2e86de 0%, #0984e3 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        width: 100%;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #0984e3 0%, #74b9ff 100%);
        box-shadow: 0 4px 12px rgba(46, 134, 222, 0.4);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
    }
    section[data-testid="stSidebar"] h1, h2, h3, p, span, div {
        color: #ecf0f1 !important;
    }
    
    /* Tablo Başlıkları */
    thead tr th {
        background-color: #2e86de !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

if 'sepet' not in st.session_state:
    st.session_state.sepet = []

def check_password():
    """Güvenli Giriş Ekranı"""
    def password_entered():
        if (st.session_state["username"] in st.secrets["users"] and 
            st.session_state["password"] == st.secrets["users"][st.session_state["username"]]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color:#2e86de;'>💎 AKÇA CRM</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color:gray;'>Profesyonel Satış Yönetimi</p>", unsafe_allow_html=True)
            st.text_input("Kullanıcı Adı", key="login_user")
            st.text_input("Şifre", type="password", key="login_pass")
            st.button("Giriş Yap", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
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

# --- YAPAY ZEKA SİMÜLASYONU (ANALİZ MOTORU) ---
def yapay_zeka_analizi(df_teklif, df_ziyaret):
    oneri_listesi = []
    
    # 1. Kayıp Müşteri Analizi
    bugun = datetime.now()
    if not df_ziyaret.empty and "Tarih" in df_ziyaret.columns:
        df_ziyaret['Tarih'] = pd.to_datetime(df_ziyaret['Tarih'], errors='coerce')
        son_ziyaretler = df_ziyaret.groupby("Firma Adı")['Tarih'].max()
        for firma, tarih in son_ziyaretler.items():
            gecen_gun = (bugun - tarih).days
            if gecen_gun > 30:
                oneri_listesi.append(f"⚠️ **{firma}** firmasını {gecen_gun} gündür ziyaret etmedin. Kendini hatırlat!")

    # 2. Satış Performansı
    if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
        ciro = df_teklif['Toplam Tutar'].sum()
        hedef = 1000000
        if ciro < hedef * 0.2:
            oneri_listesi.append("📉 Ayın başındayız, teklif sayısını artırman lazım.")
        elif ciro > hedef * 0.8:
            oneri_listesi.append("🔥 Harikasın! Hedefe çok yakınsın.")

    # 3. Ürün Trendi
    if not df_teklif.empty and "Urun" in df_teklif.columns:
        populer = df_teklif['Urun'].mode()
        if not populer.empty:
            oneri_listesi.append(f"⭐ Bu ara en çok **{populer[0]}** satılıyor. Stokları kontrol et.")

    if not oneri_listesi:
        oneri_listesi.append("✅ Şu an her şey yolunda görünüyor. Sahaya devam!")
        
    return oneri_listesi

# --- ANA UYGULAMA ---
if check_password():
    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
        # Sayfalar
        ws_ziyaret = sh.worksheet("Ziyaretler")
        ws_teklif = sh.worksheet("Teklifler")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        
        # Verileri DataFrame'e Çek
        df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
        df_teklif = pd.DataFrame(ws_teklif.get_all_records())
        df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())

        # Sayısal Dönüşümler (Hata Önleyici)
        if not df_teklif.empty:
            if "Toplam Tutar" in df_teklif.columns:
                df_teklif['Toplam Tutar'] = pd.to_numeric(df_teklif['Toplam Tutar'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        st.stop()

    # --- SIDEBAR (SOL MENÜ) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("AKÇA RULMAN")
        st.markdown("---")
        menu = st.radio("Menü", ["🏠 Dashboard", "👥 Müşteriler (CRM)", "💰 Teklif Oluştur", "📍 Ziyaret Gir", "⚙️ Ayarlar"])
        
        st.markdown("### 🤖 AI Asistanı")
        oneriler = yapay_zeka_analizi(df_teklif, df_ziyaret)
        for oneri in oneriler:
            st.info(oneri)
        
        st.markdown("---")
        st.caption("v3.0 Premium")

    # --- 1. DASHBOARD (PATRON EKRANI) ---
    if menu == "🏠 Dashboard":
        st.markdown("## 🚀 Satış Performans Paneli")
        st.markdown("İşlerin genel durumunu buradan takip edebilirsin.")
        
        # KPI KARTLARI
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        toplam_ciro = df_teklif['Toplam Tutar'].sum() if not df_teklif.empty else 0
        ziyaret_sayisi = len(df_ziyaret)
        teklif_sayisi = len(df_teklif)
        bekleyen_teklif = len(df_teklif[df_teklif['Durum'] == 'Beklemede']) if not df_teklif.empty and "Durum" in df_teklif.columns else 0

        kpi1.metric("💰 Toplam Ciro", f"{toplam_ciro:,.0f} TL", "+12%")
        kpi2.metric("📍 Toplam Ziyaret", ziyaret_sayisi, "+5")
        kpi3.metric("📝 Verilen Teklif", teklif_sayisi, "Adet")
        kpi4.metric("⏳ Bekleyen İşler", bekleyen_teklif, "Adet")
        
        st.markdown("---")
        
        # GRAFİKLER
        c_graf1, c_graf2 = st.columns([2,1])
        
        with c_graf1:
            st.subheader("📈 Aylık Satış Trendi")
            if not df_teklif.empty and "Tarih" in df_teklif.columns:
                df_teklif['Tarih'] = pd.to_datetime(df_teklif['Tarih'], errors='coerce')
                trend = df_teklif.groupby(df_teklif['Tarih'].dt.strftime('%Y-%m'))['Toplam Tutar'].sum().reset_index()
                fig_trend = px.area(trend, x='Tarih', y='Toplam Tutar', color_discrete_sequence=['#2e86de'])
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Grafik için yeterli veri yok.")

        with c_graf2:
            st.subheader("🍩 Teklif Dağılımı")
            if not df_teklif.empty and "Durum" in df_teklif.columns:
                fig_pie = px.donut(df_teklif, names='Durum', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Veri yok.")

    # --- 2. MÜŞTERİLER (CRM) ---
    elif menu == "👥 Müşteriler (CRM)":
        st.markdown("## 👥 Müşteri Yönetimi")
        
        # Müşteri listesini Ziyaretlerden ve Tekliflerden çıkar
        musteriler = set()
        if not df_ziyaret.empty and "Firma Adı" in df_ziyaret.columns:
            musteriler.update(df_ziyaret["Firma Adı"].unique())
        if not df_teklif.empty and "Musteri" in df_teklif.columns:
            musteriler.update(df_teklif["Musteri"].unique())
        
        musteri_df = pd.DataFrame(list(musteriler), columns=["Firma Adı"])
        
        # Tab 
        tab1, tab2 = st.tabs(["📋 Müşteri Listesi", "➕ Yeni Müşteri Ekle"])
        
        with tab1:
            st.dataframe(musteri_df, use_container_width=True, hide_index=True)
            
        with tab2:
            col1, col2 = st.columns(2)
            yeni_firma = col1.text_input("Firma Adı")
            yeni_yetkili = col2.text_input("Yetkili Kişi")
            yeni_tel = col1.text_input("Telefon")
            yeni_email = col2.text_input("E-Posta")
            
            if st.button("Müşteriyi Kaydet"):
                # Ziyaretlere boş bir kayıt atarak müşteriyi sisteme tanıtıyoruz
                ws_ziyaret.append_row([str(datetime.today().date()), yeni_firma, "", yeni_yetkili, "", yeni_email, "Tanımlama", str(yeni_tel), "", "", "", ""])
                st.success(f"{yeni_firma} sisteme eklendi!")

    # --- 3. TEKLİF OLUŞTUR (MODERN) ---
    elif menu == "💰 Teklif Oluştur":
        st.markdown("## 💰 Profesyonel Teklif Hazırlama")
        
        # Müşteri Seçimi
        musteri_listesi = ["Seçiniz..."] + list(df_ziyaret["Firma Adı"].unique()) if not df_ziyaret.empty else []
        
        with st.container():
            c1, c2, c3 = st.columns([2,1,1])
            secilen_musteri = c1.selectbox("Müşteri Seç", musteri_listesi, key="crm_musteri_sec")
            tarih = c2.date_input("Tarih", datetime.today())
            para_birimi = c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])

        st.markdown("---")
        
        # Ürün Ekleme Kartı
        col_urun1, col_urun2 = st.columns([3, 1])
        
        with col_urun1:
            urunler = [""] + df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else []
            secilen_urun = st.selectbox("Ürün Listesi", urunler)
            
            # Otomatik Fiyat
            oto_fiyat = 0.0
            if secilen_urun and not df_fiyat.empty:
                try:
                    satir = df_fiyat[df_fiyat['Urun Adi'] == secilen_urun].iloc[0]
                    oto_fiyat = float(str(satir['Birim Fiyat']).replace(",", "."))
                except: pass
            
            manuel_urun = st.text_input("Ürün Adı (Düzenle)", value=secilen_urun)

        with col_urun2:
            adet = st.number_input("Adet", 1, 1000, 1)
            fiyat = st.number_input("Birim Fiyat", value=oto_fiyat)
            if st.button("Sepete Ekle 🛒", use_container_width=True):
                st.session_state.sepet.append({"Urun": manuel_urun, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
                st.success("Eklendi")

        # Sepet Görüntüleme
        if st.session_state.sepet:
            st.markdown("### 🛒 Sepetiniz")
            st.table(pd.DataFrame(st.session_state.sepet))
            
            # Alt Hesaplamalar
            toplam = sum(item['Toplam'] for item in st.session_state.sepet)
            col_ozet1, col_ozet2 = st.columns(2)
            
            with col_ozet1:
                iskonto = st.slider("İskonto Oranı (%)", 0, 50, 0)
                kdv = st.selectbox("KDV Oranı", [0, 10, 20], index=2)
            
            iskonto_tutari = toplam * (iskonto/100)
            kdv_tutari = (toplam - iskonto_tutari) * (kdv/100)
            genel_toplam = (toplam - iskonto_tutari) + kdv_tutari
            
            with col_ozet2:
                st.markdown(f"""
                <div style='background-color:#e1f5fe; padding:15px; border-radius:10px; text-align:right;'>
                    <h4>Genel Toplam: {genel_toplam:,.2f} {para_birimi}</h4>
                    <small>KDV Dahil</small>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("✅ Teklifi Kaydet ve Bitir", type="primary", use_container_width=True):
                 ozet = f"{len(st.session_state.sepet)} Kalem Ürün"
                 ws_teklif.append_row([str(tarih), secilen_musteri, ozet, 1, genel_toplam, genel_toplam, "Beklemede", para_birimi])
                 st.session_state.sepet = []
                 st.balloons()
                 st.success("Teklif başarıyla oluşturuldu!")

    # --- 4. ZİYARET GİRİŞİ ---
    elif menu == "📍 Ziyaret Gir":
        st.markdown("## 📍 Saha Ziyaret Raporu")
        with st.form("ziyaret_form_new"):
            c1, c2 = st.columns(2)
            firma = c1.text_input("Firma Adı")
            kisi = c2.text_input("Görüşülen Kişi")
            konum = c1.text_input("Konum / Adres")
            sonuc = c2.selectbox("Görüşme Sonucu", ["Olumlu", "Teklif İstedi", "Satış", "Red"])
            
            notlar = st.text_area("Görüşme Detayları")
            
            if st.form_submit_button("Raporu Kaydet"):
                ws_ziyaret.append_row([str(datetime.today().date()), firma, konum, kisi, "", "", sonuc, "", "", "", "", "", "", "", notlar])
                st.success("Ziyaret kaydedildi.")

    # --- 5. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        st.header("⚙️ Sistem Ayarları")
        st.info("Bu alanda ürün ekleme, kullanıcı yetkileri ve Excel bağlantı ayarları yapılır.")
        
        with st.expander("Ürün Ekle / Düzenle"):
            st.dataframe(df_fiyat)
            c1, c2, c3 = st.columns(3)
            y_kod = c1.text_input("Yeni Kod")
            y_ad = c2.text_input("Yeni Ürün Adı")
            y_fiyat = c3.number_input("Fiyat")
            if st.button("Listeye Ekle"):
                ws_fiyat.append_row([y_kod, y_ad, y_fiyat, "TL"])
                st.success("Ürün eklendi.")
