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

# --- 1. AYARLAR VE TASARIM (DARK MODE) ---
st.set_page_config(
    page_title="AKÇA CRM v4.0 (Full)",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Mode CSS
st.markdown("""
<style>
    .stApp {background-color: #0e1117; color: #fafafa;}
    section[data-testid="stSidebar"] {background-color: #161b22; border-right: 1px solid #30363d;}
    div[data-testid="metric-container"] {
        background-color: #1f2937; border: 1px solid #374151; padding: 15px; border-radius: 8px; color: white;
    }
    div[data-testid="metric-container"] label {color: #9ca3af !important;}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {color: #60a5fa !important;}
    thead tr th {background-color: #1f2937 !important; color: #ffffff !important; border-bottom: 2px solid #374151 !important;}
    tbody tr td {color: #e5e7eb !important; background-color: #0e1117 !important;}
    div.stButton > button {
        background-color: #2563eb; color: white; border: none; border-radius: 6px; padding: 0.5rem 1rem; font-weight: 600;
    }
    div.stButton > button:hover {background-color: #1d4ed8;}
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput, .stMultiSelect {
        background-color: #1f2937 !important; color: white !important; border: 1px solid #374151 !important;
    }
    .stAlert {background-color: #1f2937; color: #e5e7eb; border: 1px solid #374151;}
</style>
""", unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

if 'sepet' not in st.session_state:
    st.session_state.sepet = []

def check_password():
    """Güvenli Giriş"""
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
        st.error("Hatalı giriş.")
        return False
    else:
        return True

def get_google_sheet_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# MAİL GÖNDERME MOTORU
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
    except Exception as e:
        print(e)
        return False

# TEKLİF MAİL ŞABLONU (TABLOLU)
def olustur_profesyonel_teklif_maili(musteri_adi, sepet, ara_toplam, iskonto_orani, iskonto_tutari, kdv_orani, kdv_tutari, genel_toplam, para_birimi, notlar):
    satirlar_html = ""
    for urun in sepet:
        satirlar_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{urun['Urun']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{urun['Adet']}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{urun['Birim Fiyat']:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{urun['Toplam']:,.2f}</td>
        </tr>"""

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; padding: 20px;">
        <div style="border: 1px solid #ddd; padding: 20px; max-width: 700px; margin: auto; background-color: #fff;">
            <h2 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">Fiyat Teklifi</h2>
            <p>Sayın <b>{musteri_adi}</b>,</p>
            <p>Talebiniz üzerine hazırlanan teklif detayları aşağıdadır:</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead style="background-color: #f3f4f6;">
                    <tr>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Ürün</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Adet</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Birim Fiyat</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Tutar</th>
                    </tr>
                </thead>
                <tbody>{satirlar_html}</tbody>
            </table>
            <div style="margin-top: 20px; text-align: right;">
                <p><b>Ara Toplam:</b> {ara_toplam:,.2f} {para_birimi}</p>
                <p style="color: red;"><b>İskonto (%{iskonto_orani}):</b> -{iskonto_tutari:,.2f} {para_birimi}</p>
                <p><b>KDV (%{kdv_orani}):</b> +{kdv_tutari:,.2f} {para_birimi}</p>
                <h3 style="background-color: #2563eb; color: white; padding: 10px; display: inline-block;">GENEL TOPLAM: {genel_toplam:,.2f} {para_birimi}</h3>
            </div>
            <div style="margin-top: 20px; background-color: #f9fafb; padding: 10px; border-left: 4px solid #2563eb;">
                <b>Notlar:</b> {notlar}
            </div>
            <p style="font-size: 12px; color: #777; margin-top: 20px; text-align: center;">Bu mail AKÇA CRM sistemi tarafından otomatik oluşturulmuştur.</p>
        </div>
      </body>
    </html>
    """
    return html

# AI ANALİZ
def yapay_zeka_analizi(df_teklif, df_ziyaret):
    oneri_listesi = []
    bugun = datetime.now()
    if not df_ziyaret.empty and "Tarih" in df_ziyaret.columns:
        df_ziyaret['Tarih'] = pd.to_datetime(df_ziyaret['Tarih'], errors='coerce')
        son_ziyaretler = df_ziyaret.groupby("Firma Adı")['Tarih'].max()
        for firma, tarih in son_ziyaretler.items():
            gecen_gun = (bugun - tarih).days
            if gecen_gun > 45:
                oneri_listesi.append(f"⚠️ **{firma}** ile {gecen_gun} gündür görüşmedin. Bir kahve içmeye git!")
    if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
        ciro = df_teklif['Toplam Tutar'].sum()
        if ciro < 500000: oneri_listesi.append("📉 Hedefin gerisindesin, gaza bas.")
    if not oneri_listesi: oneri_listesi.append("✅ Harikasın, her şey yolunda.")
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
        
        # Temiz Veri Çekme
        if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
             df_teklif['Toplam Tutar'] = pd.to_numeric(df_teklif['Toplam Tutar'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        st.stop()

    with st.sidebar:
        st.title("🦅 AKÇA CRM")
        st.markdown("<span style='color:gray'>Sürüm: 4.0 Full</span>", unsafe_allow_html=True)
        menu = st.radio("Menü", ["🏠 Dashboard", "👥 Müşteriler", "💰 Teklif Oluştur", "📍 Ziyaret Gir", "⚙️ Ayarlar"])
        st.markdown("---")
        st.markdown("### 🤖 AI Asistanı")
        for oneri in yapay_zeka_analizi(df_teklif, df_ziyaret): st.info(oneri)

    # --- 1. DASHBOARD ---
    if menu == "🏠 Dashboard":
        st.markdown("## 🚀 Satış Özeti")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        toplam_ciro = df_teklif['Toplam Tutar'].sum() if not df_teklif.empty else 0
        kpi1.metric("Toplam Ciro", f"{toplam_ciro:,.0f} TL")
        kpi2.metric("Ziyaret", len(df_ziyaret))
        kpi3.metric("Teklif Sayısı", len(df_teklif))
        bekleyen = len(df_teklif[df_teklif['Durum']=='Beklemede']) if not df_teklif.empty and 'Durum' in df_teklif.columns else 0
        kpi4.metric("Bekleyen", bekleyen)
        
        c1, c2 = st.columns(2)
        with c1:
            if not df_teklif.empty and "Durum" in df_teklif.columns:
                st.subheader("Teklif Durumları")
                fig = px.pie(df_teklif, names='Durum', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if not df_teklif.empty and "Tarih" in df_teklif.columns:
                st.subheader("Zaman Çizelgesi")
                df_teklif['Tarih'] = pd.to_datetime(df_teklif['Tarih'], errors='coerce')
                trend = df_teklif.groupby(df_teklif['Tarih'].dt.strftime('%Y-%m'))['Toplam Tutar'].sum().reset_index()
                st.bar_chart(trend.set_index('Tarih'))

    # --- 2. MÜŞTERİLER ---
    elif menu == "👥 Müşteriler":
        st.markdown("## 👥 Müşteri Portföyü")
        musteriler = set()
        if not df_ziyaret.empty and "Firma Adı" in df_ziyaret.columns: musteriler.update(df_ziyaret["Firma Adı"].unique())
        st.dataframe(pd.DataFrame(list(musteriler), columns=["Firma Adı"]), use_container_width=True)

    # --- 3. TEKLİF OLUŞTUR (FULL ÖZELLİK) ---
    elif menu == "💰 Teklif Oluştur":
        st.markdown("## 💰 Profesyonel Teklif Hazırla")
        
        # Müşteri Mail Adresini Bulma
        mail_sozlugu = {}
        if not df_ziyaret.empty and "Firma Adı" in df_ziyaret.columns and "E-Posta" in df_ziyaret.columns:
            for i, row in df_ziyaret.iterrows():
                if row["Firma Adı"]: mail_sozlugu[row["Firma Adı"]] = str(row["E-Posta"])

        with st.container():
            c1, c2, c3 = st.columns(3)
            musteri_list = ["Seçiniz"] + list(df_ziyaret["Firma Adı"].unique()) if not df_ziyaret.empty else []
            secilen_mus = c1.selectbox("Müşteri", musteri_list)
            
            # Otomatik Mail Getirme
            oto_mail = mail_sozlugu.get(secilen_mus, "")
            
            tarih = c2.date_input("Tarih", datetime.today())
            para = c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])

        st.markdown("---")
        
        # Ürün Ekleme
        col_u1, col_u2 = st.columns([3, 1])
        urunler = [""] + df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else []
        u_secim = col_u1.selectbox("Listeden Ürün Seç", urunler)
        u_manuel = col_u1.text_input("Ürün Adı (Düzenle)", value=u_secim)
        
        fiyat_oto = 0.0
        if u_secim and not df_fiyat.empty:
            try: fiyat_oto = float(str(df_fiyat[df_fiyat['Urun Adi']==u_secim].iloc[0]['Birim Fiyat']).replace(",", "."))
            except: pass
            
        adet = col_u2.number_input("Adet", 1, 1000, 1)
        fiyat = col_u2.number_input("Birim Fiyat", value=fiyat_oto)
        
        if st.button("Sepete Ekle ➕"):
            st.session_state.sepet.append({"Urun": u_manuel, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
            st.success("Eklendi")
            
        if st.session_state.sepet:
            st.markdown("### 🛒 Teklif Sepeti")
            st.table(pd.DataFrame(st.session_state.sepet))
            
            # Hesaplamalar
            toplam = sum(x['Toplam'] for x in st.session_state.sepet)
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                iskonto = st.number_input("İskonto (%)", 0, 50, 0)
                kdv = st.selectbox("KDV Oranı", [0, 10, 20], index=2)
            
            iskonto_tutari = toplam * (iskonto/100)
            kdv_tutari = (toplam - iskonto_tutari) * (kdv/100)
            genel_toplam = (toplam - iskonto_tutari) + kdv_tutari
            
            with c_h2:
                st.markdown(f"""
                <div style='background-color:#1f2937; padding:15px; border-radius:10px; text-align:right; color:white;'>
                    <p>Ara Toplam: {toplam:,.2f}</p>
                    <p style='color:#ef4444'>İskonto: -{iskonto_tutari:,.2f}</p>
                    <p>KDV: {kdv_tutari:,.2f}</p>
                    <h3 style='color:#60a5fa'>GENEL TOPLAM: {genel_toplam:,.2f} {para}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            col_m1, col_m2 = st.columns([2, 1])
            mail_adres = col_m1.text_input("Alıcı E-Posta", value=oto_mail)
            notlar = col_m1.text_area("Teklif Notu", "Ödeme peşin, stoktan teslim.")
            mail_at = col_m2.checkbox("✅ Teklifi Kaydederken Mail Gönder", value=True)
            
            if col_m2.button("💾 TEKLİFİ KAYDET"):
                ozet = f"{len(st.session_state.sepet)} Kalem"
                ws_teklif.append_row([str(tarih), secilen_mus, ozet, 1, genel_toplam, genel_toplam, "Beklemede", para])
                st.toast("Teklif Excel'e işlendi.", icon="💾")
                
                if mail_at and mail_adres:
                    with st.spinner("Mail gönderiliyor..."):
                        html_body = olustur_profesyonel_teklif_maili(secilen_mus, st.session_state.sepet, toplam, iskonto, iskonto_tutari, kdv, kdv_tutari, genel_toplam, para, notlar)
                        basari = mail_gonder_generic(mail_adres, f"Fiyat Teklifi: {secilen_mus}", html_body)
                        if basari: st.success("Mail müşteriye iletildi! 📧")
                        else: st.error("Mail gönderilemedi.")
                
                st.session_state.sepet = []

    # --- 4. ZİYARET GİRİŞİ (FULL ÖZELLİK - GERİ GELDİ) ---
    elif menu == "📍 Ziyaret Gir":
        st.markdown("## 📍 Saha Ziyaret Raporu")
        
        with st.form("ziyaret_full"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", datetime.today())
            firma = c1.text_input("Firma Adı")
            kisi = c2.text_input("Görüşülen Kişi")
            email = c2.text_input("E-Posta (Otomatik Teşekkür İçin)")
            
            c3, c4 = st.columns(2)
            durum = c3.selectbox("Sonuç", ["Tanışma", "Teklif Verildi", "Sıcak Satış", "Red"])
            
            # BURASI DÜZELTİLDİ: ARTIK ÇOKLU SEÇİM VAR
            urunler = c4.multiselect("İlgilenilen Ürünler", ["Rulman", "ZKL", "Kinex", "Sensimore", "Hizmet", "Diğer"])
            potansiyel = c4.number_input("Potansiyel Ciro (TL)", step=1000)
            
            notlar = st.text_area("Görüşme Detayları & Notlar")
            mail_at = st.checkbox("Teşekkür Maili Gönder")
            
            if st.form_submit_button("💾 Raporu Kaydet"):
                ws_ziyaret.append_row([str(tarih), firma, "", kisi, "", email, durum, "", ", ".join(urunler), potansiyel, "", "", "", "", notlar])
                st.toast("Ziyaret kaydedildi.", icon="✅")
                
                if mail_at and email:
                    with st.spinner("Mail atılıyor..."):
                        mail_gonder_generic(email, f"Ziyaret Hk. - {firma}", f"<p>Sayın {kisi},</p><p>Bugünkü görüşmemiz için teşekkür ederiz.</p><p>Saygılarımızla,<br>Akça Rulman</p>")
                        st.success("Teşekkür maili gönderildi.")

    # --- 5. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        st.markdown("## ⚙️ Ürün Fiyat Listesi")
        st.dataframe(df_fiyat, use_container_width=True)
        
        with st.expander("➕ Yeni Ürün Ekle"):
            c1, c2, c3 = st.columns(3)
            yk = c1.text_input("Kod")
            ya = c2.text_input("Ad")
            yf = c3.number_input("Fiyat")
            if st.button("Listeye Ekle"):
                ws_fiyat.append_row([yk, ya, yf, "TL"])
                st.success("Ürün eklendi.")
