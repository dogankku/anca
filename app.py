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

# --- CACHE SİSTEMİ ---
@st.cache_data(ttl=300)
def verileri_yukle():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("Satis_Raporlari")
        
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
                <strong>Teklif Şartları & Notlar:</strong><br>{notlar}
            </div>
        </div>
    </body>
    </html>
    """

# --- ANA UYGULAMA ---
if check_password():
    df_musteri, df_ziyaret, df_teklif, df_fiyat = verileri_yukle()
    
    if df_musteri is None:
        st.error("Veri hatası! Lütfen 'Manage App' bölümünden Secrets ayarlarını ve interneti kontrol edin.")
        st.stop()

    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
        ws_mus = sh.worksheet("Musteriler")
        ws_ziy = sh.worksheet("Ziyaretler")
        ws_tek = sh.worksheet("Teklifler")
        ws_fiy = sh.worksheet("Fiyat_Listesi")
    except:
        pass

    with st.sidebar:
        st.title("🦅 AKÇA CRM")
        st.caption("Platinum Edition")
        menu = st.radio("Menü", ["🏠 Dashboard", "📇 Müşteri Kartları", "📍 Ziyaret Girişi", "💰 Teklif Hazırla", "⚙️ Fiyat Listesi"])
        st.markdown("---")
        if not df_teklif.empty:
            ciro = df_teklif['Toplam Tutar'].sum()
            st.info(f"💡 Aylık Ciro: {ciro:,.0f} TL")
            if ciro > 100:
                st.progress(min(ciro / 500000, 1.0))

    # --- 1. DASHBOARD ---
    if menu == "🏠 Dashboard":
        st.markdown("## 🚀 Satış Genel Bakış")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Toplam Ciro", f"{df_teklif['Toplam Tutar'].sum():,.0f} TL" if not df_teklif.empty else "0 TL")
        k2.metric("Müşteri Sayısı", len(df_musteri))
        k3.metric("Bu Ay Ziyaret", len(df_ziyaret))
        k4.metric("Bekleyen Teklif", len(df_teklif[df_teklif['Durum']=='Beklemede']) if not df_teklif.empty else 0)
        
        c1, c2 = st.columns(2)
        with c1:
            if not df_teklif.empty:
                st.subheader("Teklif Durumları")
                fig = px.pie(df_teklif, names='Durum', hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Son Aktiviteler")
            if not df_ziyaret.empty:
                st.dataframe(df_ziyaret.tail(5)[['Firma', 'Kisi', 'Durum']], hide_index=True, use_container_width=True)

    # --- 2. MÜŞTERİ KARTLARI ---
    elif menu == "📇 Müşteri Kartları":
        st.markdown("## 📇 Müşteri Yönetimi")
        tab1, tab2 = st.tabs(["📋 Liste", "➕ Yeni Ekle"])
        
        with tab1:
            if not df_musteri.empty:
                secilen_firma = st.selectbox("Detay için Firma Seç:", ["Seçiniz..."] + df_musteri["Firma Adı"].tolist())
                if secilen_firma != "Seçiniz...":
                    m = df_musteri[df_musteri["Firma Adı"] == secilen_firma].iloc[0]
                    st.markdown(f"""
                    <div style="background-color:#262730; padding:20px; border-radius:10px;">
                        <h3 style="color:#4da6ff">{m['Firma Adı']}</h3>
                        <p>👤 <b>Yetkili:</b> {m.get('Yetkili','-')} ({m.get('Unvan','-')})</p>
                        <p>📞 <b>Tel:</b> {m.get('Telefon','-')} | 📧 <b>Email:</b> {m.get('Email','-')}</p>
                        <p>📍 <b>Adres:</b> {m.get('Adres','-')}</p>
                    </div>""", unsafe_allow_html=True)
                    
                    st.write("#### 📅 Ziyaret Geçmişi")
                    if not df_ziyaret.empty:
                        gecmis = df_ziyaret[df_ziyaret['Firma'] == secilen_firma]
                        st.dataframe(gecmis, use_container_width=True)
                else:
                    st.dataframe(df_musteri, use_container_width=True)
            else:
                st.info("Kayıtlı müşteri yok.")

        with tab2:
            with st.form("yeni_mus"):
                c1, c2 = st.columns(2)
                f_ad = c1.text_input("Firma Adı")
                f_yet = c2.text_input("Yetkili Adı")
                f_unv = c1.text_input("Ünvan")
                f_tel = c2.text_input("Telefon")
                f_mail = c1.text_input("E-Posta")
                f_adr = c2.text_area("Adres")
                f_kon = c1.text_input("Konum Linki")
                if st.form_submit_button("Kaydet"):
                    ws_mus.append_row([f_ad, f_yet, f_unv, f_tel, f_mail, f_adr, f_kon, str(datetime.today().date())])
                    st.success("Eklendi!")
                    st.cache_data.clear()

    # --- 3. ZİYARET GİRİŞİ ---
    elif menu == "📍 Ziyaret Girişi":
        st.markdown("## 📍 Ziyaret Raporu")
        m_list = ["Seçiniz..."] + df_musteri["Firma Adı"].tolist() if not df_musteri.empty else []
        
        with st.form("ziyaret_pro"):
            secilen = st.selectbox("Müşteri Seç (Otomatik Doldurur)", m_list)
            o_kis, o_unv, o_adr, o_mai = "", "", "", ""
            if secilen != "Seçiniz...":
                x = df_musteri[df_musteri["Firma Adı"] == secilen].iloc[0]
                o_kis, o_unv, o_adr, o_mai = x.get("Yetkili",""), x.get("Unvan",""), x.get("Adres",""), x.get("Email","")
            
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", datetime.today())
            firma = c2.text_input("Firma", value=secilen if secilen!="Seçiniz..." else "")
            
            c3, c4 = st.columns(2)
            kisi = c3.text_input("Kişi", value=o_kis)
            unvan = c4.text_input("Ünvan", value=o_unv)
            adres = st.text_input("Konum / Adres", value=o_adr)
            
            c5, c6 = st.columns(2)
            durum = c5.selectbox("Sonuç", ["Tanışma", "Teklif", "Satış", "Red"])
            urunler = c6.multiselect("Ürünler", ["Rulman", "ZKL", "Kinex", "Kayış", "Hizmet"])
            
            notlar = st.text_area("Görüşme Notları")
            potansiyel = st.number_input("Potansiyel (TL)", step=1000)
            mail_at = st.checkbox("Teşekkür Maili Gönder")
            email_val = st.text_input("Mail Adresi", value=o_mai)
            
            if st.form_submit_button("Kaydet"):
                ws_ziy.append_row([str(tarih), firma, kisi, unvan, adres, durum, ", ".join(urunler), potansiyel, notlar])
                st.success("Kaydedildi.")
                if mail_at and email_val:
                    mail_gonder(email_val, f"Ziyaret Hk - {firma}", f"Sayın {kisi},<br>Ziyaret için teşekkürler.<br>Akça Rulman")
                    st.success("Mail atıldı.")
                st.cache_data.clear()

    # --- 4. TEKLİF ---
    elif menu == "💰 Teklif Hazırla":
        st.markdown("## 💰 Teklif Robotu")
        with st.container():
            c1, c2, c3 = st.columns(3)
            m_list = ["Seçiniz"] + df_musteri["Firma Adı"].tolist() if not df_musteri.empty else []
            secilen_m = c1.selectbox("Müşteri", m_list)
            oto_mail = ""
            if secilen_m != "Seçiniz":
                bul = df_musteri[df_musteri["Firma Adı"] == secilen_m]
                if not bul.empty: oto_mail = bul.iloc[0].get("Email", "")
            
            tarih = c2.date_input("Tarih", datetime.today())
            para = c3.selectbox("Para", ["TL", "USD", "EUR"])

        st.markdown("---")
        c_u1, c_u2 = st.columns([3, 1])
        u_list = [""] + df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else []
        u_sec = c_u1.selectbox("Ürün Seç", u_list)
        u_ad = c_u1.text_input("Açıklama", value=u_sec)
        
        f_oto = 0.0
        if u_sec and not df_fiyat.empty:
            try: f_oto = float(str(df_fiyat[df_fiyat['Urun Adi']==u_sec].iloc[0]['Birim Fiyat']).replace(",", "."))
            except: pass
            
        adet = c_u2.number_input("Miktar", 1, 10000, 1)
        fiyat = c_u2.number_input("Birim Fiyat", value=f_oto)
        
        if st.button("Ekle ➕"):
            st.session_state.sepet.append({"Urun": u_ad, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
        
        if st.session_state.sepet:
            st.table(st.session_state.sepet)
            toplam = sum(x['Toplam'] for x in st.session_state.sepet)
            
            c_calc1, c_calc2 = st.columns(2)
            with c_calc1:
                isk = st.number_input("İskonto %", 0, 100, 0)
                kdv = st.selectbox("KDV %", [0, 10, 20], index=2)
            
            isk_tut = toplam * (isk/100)
            kdv_tut = (toplam - isk_tut) * (kdv/100)
            genel = (toplam - isk_tut) + kdv_tut
            
            with c_calc2:
                st.markdown(f"<h3 style='text-align:right; color:#4da6ff'>{genel:,.2f} {para}</h3>", unsafe_allow_html=True)
            
            c_m1, c_m2 = st.columns([2, 1])
            mail_inp = c_m1.text_input("Alıcı Mail", value=oto_mail)
            not_inp = c_m1.text_area("Notlar", "Ödeme peşin.")
            mail_chk = c_m2.checkbox("Mail Gönder", value=True)
            
            if c_m2.button("KAYDET"):
                ws_tek.append_row([str(tarih), secilen_m, f"{len(st.session_state.sepet)} Kalem", 1, genel, genel, "Beklemede", para])
                st.success("Kaydedildi!")
                if mail_chk and mail_inp:
                    html = teklif_html_olustur(secilen_m, st.session_state.sepet, toplam, isk, isk_tut, kdv, kdv_tut, genel, para, not_inp)
                    mail_gonder(mail_inp, f"Teklif: {secilen_m}", html)
                    st.success("Mail gitti!")
                st.session_state.sepet = []
                st.cache_data.clear()

    # --- 5. FİYAT LİSTESİ ---
    elif menu == "⚙️ Fiyat Listesi":
        st.dataframe(df_fiyat, use_container_width=True)
        with st.expander("Yeni Ekle"):
            c1, c2, c3 = st.columns(3)
            if st.button("Ekle"): 
                ws_fiy.append_row([c1.text_input("Kod"), c2.text_input("Ad"), c3.number_input("Fiyat"), "TL"])
                st.success("Eklendi.")
                st.cache_data.clear()
