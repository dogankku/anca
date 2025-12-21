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

# --- 1. AYARLAR VE TASARIM (PREMIUM DARK) ---
st.set_page_config(page_title="AKÇA CRM Pro", page_icon="🦅", layout="wide", initial_sidebar_state="expanded")

# Profesyonel CSS
st.markdown("""
<style>
    .stApp {background-color: #0e1117; color: #f0f2f6;}
    section[data-testid="stSidebar"] {background-color: #161b22;}
    
    /* Kartlar */
    div[data-testid="metric-container"] {
        background-color: #262730; border: 1px solid #41424b; padding: 15px; border-radius: 8px;
    }
    div[data-testid="metric-container"] label {color: #a3a8b8;}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {color: #4da6ff;}
    
    /* Tablolar */
    thead tr th {background-color: #1f2937 !important; color: #4da6ff !important;}
    
    /* Form Alanları */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput, .stTextArea textarea {
        background-color: #1c1f26 !important; color: white !important; border: 1px solid #41424b !important;
    }
    
    /* Butonlar */
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

def get_google_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

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
    try:
        client = get_google_sheet()
        sh = client.open("Satis_Raporlari")
        # Sayfalar (Eğer yoksa hata verir, lütfen Excel'de açtığından emin ol)
        ws_ziyaret = sh.worksheet("Ziyaretler")
        ws_teklif = sh.worksheet("Teklifler")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        
        # Müşteriler sayfası yoksa hata vermesin diye kontrol
        try:
            ws_musteri = sh.worksheet("Musteriler")
        except:
            ws_musteri = sh.add_worksheet(title="Musteriler", rows="1000", cols="10")
            ws_musteri.append_row(["Firma Adı", "Yetkili", "Unvan", "Telefon", "Email", "Adres", "Konum", "Kayit Tarihi"])

        # Verileri Çek
        df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
        df_teklif = pd.DataFrame(ws_teklif.get_all_records())
        df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
        df_musteri = pd.DataFrame(ws_musteri.get_all_records())

        # Sayısal Dönüşümler
        if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
             df_teklif['Toplam Tutar'] = pd.to_numeric(df_teklif['Toplam Tutar'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}. Lütfen Excel sayfalarını (Musteriler, Ziyaretler, vb.) kontrol et.")
        st.stop()

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🦅 AKÇA CRM")
        st.caption("Professional Edition")
        menu = st.radio("Menü", ["🏠 Dashboard", "📇 Müşteri Kartları", "📍 Ziyaret Girişi", "💰 Teklif Hazırla", "⚙️ Fiyat Listesi"])
        st.markdown("---")
        # Basit AI Analiz
        if not df_teklif.empty:
            ciro = df_teklif['Toplam Tutar'].sum()
            st.info(f"💡 Bu ayki toplam ciro: {ciro:,.0f} TL. Hedefin %{(ciro/500000)*100:.1f}'indesin.")

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
            st.subheader("Son 5 Ziyaret")
            if not df_ziyaret.empty:
                st.dataframe(df_ziyaret.tail(5)[['Firma', 'Kisi', 'Durum']], hide_index=True, use_container_width=True)

    # --- 2. MÜŞTERİ KARTLARI (YENİ VE DETAYLI) ---
    elif menu == "📇 Müşteri Kartları":
        st.markdown("## 📇 Müşteri Yönetimi")
        
        tab1, tab2 = st.tabs(["📋 Müşteri Listesi", "➕ Yeni Müşteri Ekle"])
        
        with tab1:
            if not df_musteri.empty:
                secilen_firma = st.selectbox("Detaylarını Görüntülemek İçin Firma Seç:", ["Seçiniz..."] + df_musteri["Firma Adı"].tolist())
                if secilen_firma != "Seçiniz...":
                    m = df_musteri[df_musteri["Firma Adı"] == secilen_firma].iloc[0]
                    st.markdown(f"""
                    <div style="background-color:#262730; padding:20px; border-radius:10px;">
                        <h3 style="color:#4da6ff">{m['Firma Adı']}</h3>
                        <p>👤 <b>Yetkili:</b> {m['Yetkili']} ({m['Unvan']})</p>
                        <p>📞 <b>Telefon:</b> {m['Telefon']} | 📧 <b>Email:</b> {m['Email']}</p>
                        <p>📍 <b>Adres:</b> {m['Adres']}</p>
                        <p>🌍 <b>Konum:</b> {m['Konum']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("#### 📜 Geçmiş Hareketler")
                    if not df_ziyaret.empty:
                        gecmis = df_ziyaret[df_ziyaret['Firma'] == secilen_firma]
                        st.dataframe(gecmis, use_container_width=True)
                else:
                    st.dataframe(df_musteri, use_container_width=True)
            else:
                st.info("Henüz kayıtlı müşteri yok. 'Yeni Müşteri Ekle' sekmesinden ekleyin.")

        with tab2:
            with st.form("yeni_musteri_form"):
                c1, c2 = st.columns(2)
                f_ad = c1.text_input("Firma Adı (Zorunlu)")
                f_yet = c2.text_input("Yetkili Adı Soyadı")
                f_unv = c1.text_input("Yetkili Ünvanı (Örn: Satınalma Müdürü)")
                f_tel = c2.text_input("Telefon")
                f_mail = c1.text_input("E-Posta")
                f_adr = c2.text_area("Açık Adres")
                f_kon = c1.text_input("Konum Linki (Google Maps)")
                
                if st.form_submit_button("💾 Müşteriyi Kaydet"):
                    if f_ad:
                        ws_musteri.append_row([f_ad, f_yet, f_unv, f_tel, f_mail, f_adr, f_kon, str(datetime.today().date())])
                        st.success(f"{f_ad} başarıyla eklendi!")
                    else:
                        st.error("Firma adı boş olamaz.")

    # --- 3. ZİYARET GİRİŞİ (DETAYLI) ---
    elif menu == "📍 Ziyaret Girişi":
        st.markdown("## 📍 Saha Ziyaret Raporu")
        
        # Müşterileri Listeden Çek
        musteri_listesi = ["Listeden Seçiniz..."] + df_musteri["Firma Adı"].tolist() if not df_musteri.empty else []
        
        with st.form("ziyaret_form_pro"):
            st.info("Müşteri seçerseniz bilgiler otomatik gelir.")
            secilen = st.selectbox("Müşteri", musteri_listesi)
            
            # Otomatik Doldurma Mantığı
            oto_kisi, oto_unvan, oto_adres, oto_mail = "", "", "", ""
            if secilen != "Listeden Seçiniz...":
                m_bilgi = df_musteri[df_musteri["Firma Adı"] == secilen].iloc[0]
                oto_kisi = m_bilgi.get("Yetkili", "")
                oto_unvan = m_bilgi.get("Unvan", "")
                oto_adres = m_bilgi.get("Adres", "")
                oto_mail = m_bilgi.get("Email", "")

            c1, c2 = st.columns(2)
            tarih = c1.date_input("Ziyaret Tarihi", datetime.today())
            firma = c2.text_input("Firma Adı", value=secilen if secilen != "Listeden Seçiniz..." else "")
            
            c3, c4 = st.columns(2)
            kisi = c3.text_input("Görüşülen Kişi", value=oto_kisi)
            unvan = c4.text_input("Kişi Ünvanı", value=oto_unvan)
            
            adres = st.text_input("Ziyaret Adresi / Konum", value=oto_adres)
            
            c5, c6 = st.columns(2)
            durum = c5.selectbox("Ziyaret Sonucu", ["Tanışma", "Teklif Verilecek", "Sıcak Satış", "Reddedildi", "Rutin Ziyaret"])
            urunler = c6.multiselect("İlgilenilen Ürünler", ["Rulman", "ZKL", "Kinex", "CTS", "Sensimore", "Hizmet"])
            
            notlar = st.text_area("Görüşme Notları & Rakip Bilgisi")
            potansiyel = st.number_input("Tahmini Yıllık Ciro Potansiyeli (TL)", step=50000)
            
            mail_at = st.checkbox("Müşteriye otomatik teşekkür maili gönder")
            email_input = st.text_input("Mail Adresi", value=oto_mail)

            if st.form_submit_button("✅ Ziyareti Kaydet"):
                ws_ziyaret.append_row([str(tarih), firma, kisi, unvan, adres, durum, ", ".join(urunler), potansiyel, notlar])
                st.success("Ziyaret kaydedildi.")
                if mail_at and email_input:
                    html_icerik = f"<p>Sayın {kisi},</p><p>Bugünkü ziyaret ve görüşmemiz için teşekkür ederiz.</p><p>Saygılarımızla,<br>Akça Rulman</p>"
                    mail_gonder(email_input, f"Ziyaret Hk. - {firma}", html_icerik)
                    st.success("Mail gönderildi.")

    # --- 4. TEKLİF HAZIRLA (PROFESYONEL) ---
    elif menu == "💰 Teklif Hazırla":
        st.markdown("## 💰 Profesyonel Teklif Robotu")
        
        with st.container():
            c1, c2, c3 = st.columns(3)
            # Müşterileri Listeden Getir
            m_list = ["Seçiniz"] + df_musteri["Firma Adı"].tolist() if not df_musteri.empty else []
            secilen_m = c1.selectbox("Müşteri Seç", m_list)
            
            # Mail Bul
            oto_mail = ""
            if secilen_m != "Seçiniz":
                bul = df_musteri[df_musteri["Firma Adı"] == secilen_m]
                if not bul.empty: oto_mail = bul.iloc[0].get("Email", "")
            
            tarih = c2.date_input("Teklif Tarihi", datetime.today())
            para = c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])

        st.markdown("---")
        
        # Ürün Ekleme
        c_u1, c_u2 = st.columns([3, 1])
        urun_liste = [""] + df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else []
        u_sec = c_u1.selectbox("Ürün Seç", urun_liste)
        
        # Fiyat Getir
        fiyat_oto = 0.0
        if u_sec and not df_fiyat.empty:
            try: fiyat_oto = float(str(df_fiyat[df_fiyat['Urun Adi']==u_sec].iloc[0]['Birim Fiyat']).replace(",", "."))
            except: pass
            
        u_ad = c_u1.text_input("Ürün Açıklaması (Düzenlenebilir)", value=u_sec)
        adet = c_u2.number_input("Miktar", 1, 10000, 1)
        fiyat = c_u2.number_input("Birim Fiyat", value=fiyat_oto)
        
        if st.button("Sepete Ekle 🛒"):
            st.session_state.sepet.append({"Urun": u_ad, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
            st.success("Eklendi")

        # Sepet & Hesaplama
        if st.session_state.sepet:
            st.table(pd.DataFrame(st.session_state.sepet))
            
            toplam = sum(x['Toplam'] for x in st.session_state.sepet)
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                iskonto = st.number_input("İskonto (%)", 0, 100, 0)
                kdv = st.selectbox("KDV Oranı", [0, 10, 20], index=2)
            
            isk_tut = toplam * (iskonto/100)
            kdv_tut = (toplam - isk_tut) * (kdv/100)
            genel_top = (toplam - isk_tut) + kdv_tut
            
            with col_calc2:
                st.markdown(f"""
                <div style='text-align:right; background-color:#262730; padding:15px; border-radius:8px;'>
                    <p>Ara Toplam: {toplam:,.2f}</p>
                    <p style='color:#ff4d4d'>İskonto: -{isk_tut:,.2f}</p>
                    <p>KDV: {kdv_tut:,.2f}</p>
                    <h3 style='color:#4da6ff'>GENEL: {genel_top:,.2f} {para}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            c_mail1, c_mail2 = st.columns([2, 1])
            alici_mail = c_mail1.text_input("Alıcı Mail Adresi", value=oto_mail)
            notlar = c_mail1.text_area("Teklif Notları (Ödeme, Teslimat vb.)", "Ödeme peşin. Teslimat stoktan hemen yapılır.")
            gonder = c_mail2.checkbox("Müşteriye Mail Gönder", value=True)
            
            if c_mail2.button("✅ Teklifi Tamamla"):
                # Excel'e Kayıt
                ws_teklif.append_row([str(tarih), secilen_m, f"{len(st.session_state.sepet)} Kalem Ürün", 1, genel_top, genel_top, "Beklemede", para])
                st.success("Teklif kaydedildi!")
                
                # Mail Gönderimi
                if gonder and alici_mail:
                    html = teklif_html_olustur(secilen_m, st.session_state.sepet, toplam, iskonto, isk_tut, kdv, kdv_tut, genel_top, para, notlar)
                    mail_gonder(alici_mail, f"Fiyat Teklifi: {secilen_m}", html)
                    st.success("Mail gönderildi!")
                
                st.session_state.sepet = []

    # --- 5. FİYAT LİSTESİ ---
    elif menu == "⚙️ Fiyat Listesi":
        st.markdown("## ⚙️ Ürün Yönetimi")
        st.dataframe(df_fiyat, use_container_width=True)
        with st.expander("➕ Yeni Ürün Ekle"):
            c1, c2, c3 = st.columns(3)
            kod = c1.text_input("Kod")
            ad = c2.text_input("Ad")
            fiy = c3.number_input("Fiyat")
            if st.button("Kaydet"):
                ws_fiyat.append_row([kod, ad, fiy, "TL"])
                st.success("Eklendi")
