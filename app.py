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

# --- SAYFA AYARLARI (GÖRSEL DÜZENLEME) ---
st.set_page_config(
    page_title="AKÇA RULMAN - Satış Yönetim",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TASARIM İÇİN CSS (Renklendirme ve Düzen) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #2e86de;
    }
    div.stButton > button:first-child {
        background-color: #2e86de;
        color: white;
        border-radius: 10px;
    }
    div.block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'sepet' not in st.session_state:
    st.session_state.sepet = []

# --- GÜVENLİK ---
def check_password():
    def password_entered():
        if (st.session_state["username"] in st.secrets["users"] and 
            st.session_state["password"] == st.secrets["users"][st.session_state["username"]]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #2e86de;'>AKÇA RULMAN CRM</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.text_input("Kullanıcı Adı", key="login_user")
            st.text_input("Şifre", type="password", key="login_pass")
            st.button("Giriş Yap", on_click=password_entered, use_container_width=True)
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

# --- MAİL FONKSİYONU ---
def mail_gonder_generic(alici_email, konu, html_icerik):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["server"]
        smtp_port = st.secrets["email"]["port"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Akça Rulman Satış <{sender_email}>"
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
        st.error(f"Mail hatası: {e}")
        return False

def olustur_profesyonel_teklif_maili(musteri_adi, sepet, ara_toplam, iskonto_orani, iskonto_tutari, kdv_orani, kdv_tutari, genel_toplam, para_birimi, notlar):
    satirlar_html = ""
    for urun in sepet:
        satirlar_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px;">{urun['Urun']}</td>
            <td style="padding: 10px; text-align: center;">{urun['Adet']}</td>
            <td style="padding: 10px; text-align: right;">{urun['Birim Fiyat']:,.2f}</td>
            <td style="padding: 10px; text-align: right;">{urun['Toplam']:,.2f}</td>
        </tr>"""

    html = f"""
    <html>
      <body style="font-family: 'Helvetica', sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="background-color: #fff; padding: 30px; max-width: 600px; margin: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <div style="border-bottom: 2px solid #2e86de; padding-bottom: 10px; margin-bottom: 20px;">
                <h2 style="color: #2e86de; margin: 0;">Fiyat Teklifi</h2>
                <span style="font-size: 12px; color: #777;">Tarih: {datetime.now().strftime('%d-%m-%Y')}</span>
            </div>
            <p>Sayın <b>{musteri_adi}</b>,</p>
            <p>Talebiniz üzerine hazırlanan teklifimiz aşağıdadır:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;">
                <thead style="background-color: #f8f9fa;">
                    <tr>
                        <th style="padding: 10px; text-align: left;">Ürün</th>
                        <th style="padding: 10px; text-align: center;">Miktar</th>
                        <th style="padding: 10px; text-align: right;">Birim</th>
                        <th style="padding: 10px; text-align: right;">Tutar</th>
                    </tr>
                </thead>
                <tbody>{satirlar_html}</tbody>
            </table>
            
            <div style="margin-top: 20px; text-align: right; font-size: 14px;">
                <p style="margin: 5px 0;">Ara Toplam: {ara_toplam:,.2f} {para_birimi}</p>
                {f'<p style="margin: 5px 0; color: #e74c3c;">İskonto (%{iskonto_orani}): -{iskonto_tutari:,.2f} {para_birimi}</p>' if iskonto_tutari > 0 else ''}
                <p style="margin: 5px 0;">KDV (%{kdv_orani}): +{kdv_tutari:,.2f} {para_birimi}</p>
                <div style="background-color: #2e86de; color: white; padding: 10px; display: inline-block; border-radius: 5px; margin-top: 10px;">
                    <strong style="font-size: 16px;">TOPLAM: {genel_toplam:,.2f} {para_birimi}</strong>
                </div>
            </div>
            
            <div style="margin-top: 30px; background-color: #eaf2f8; padding: 15px; border-radius: 5px; font-size: 13px;">
                <strong>Notlar:</strong> {notlar}
            </div>
            <br>
            <p style="text-align: center; font-size: 12px; color: #aaa;">AKÇA RULMAN ve GÜÇ SİSTEMLERİ<br>Otomatik Teklif Sistemi</p>
        </div>
      </body>
    </html>
    """
    return html

# --- ANA UYGULAMA ---
if check_password():
    # Kenar Çubuğu Tasarımı
    with st.sidebar:
        st.markdown("### 🦅 Akça Rulman")
        menu = st.radio("Menü", ["📊 Patron Ekranı", "💰 Teklif Robotu", "📍 Ziyaret Girişi", "📋 Ürün Listesi"])
        st.markdown("---")
        st.caption("v2.1 - Görsel Sürüm")

    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
    except:
        st.error("Veritabanı bağlantı hatası!")
        st.stop()

    # --- MODÜL 1: PATRON EKRANI (DASHBOARD) - YENİ VE GÖRSEL ---
    if menu == "📊 Patron Ekranı":
        st.markdown("## 📊 Genel Durum ve Hedefler")
        
        # Verileri Çek
        try:
            df_teklif = pd.DataFrame(sh.worksheet("Teklifler").get_all_records())
            df_ziyaret = pd.DataFrame(sh.worksheet("Ziyaretler").get_all_records())
        except:
            st.warning("Henüz yeterli veri yok.")
            st.stop()
            
        # Temel Metrikler (KPI)
        col1, col2, col3, col4 = st.columns(4)
        
        toplam_teklif_sayisi = len(df_teklif)
        toplam_ziyaret = len(df_ziyaret)
        
        # Ciro Hesabı (Hata önleyici dönüşüm)
        ciro = 0
        if not df_teklif.empty and "Toplam Tutar" in df_teklif.columns:
            # Virgülleri noktaya çevirip sayıya dönüştürme
            df_teklif['Toplam Tutar'] = df_teklif['Toplam Tutar'].astype(str).str.replace('.', '').str.replace(',', '.').replace('', '0')
            df_teklif['Toplam Tutar'] = pd.to_numeric(df_teklif['Toplam Tutar'], errors='coerce').fillna(0)
            ciro = df_teklif['Toplam Tutar'].sum()

        with col1:
            st.metric("Toplam Teklif Tutarı", f"{ciro:,.0f} TL", "Bu Ay")
        with col2:
            st.metric("Verilen Teklif Adedi", f"{toplam_teklif_sayisi}", "+2")
        with col3:
            st.metric("Ziyaret Sayısı", f"{toplam_ziyaret}", "Sahada")
        with col4:
            hedef = 1000000 # Örnek Hedef 1 Milyon
            yuzde = min((ciro / hedef), 1.0)
            st.write(f"**Aylık Hedef:** %{int(yuzde*100)}")
            st.progress(yuzde)

        st.markdown("---")
        
        # Grafikler Alanı
        g1, g2 = st.columns(2)
        
        with g1:
            st.subheader("📋 Teklif Durumları")
            if not df_teklif.empty and "Durum" in df_teklif.columns:
                fig_pie = px.pie(df_teklif, names='Durum', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Veri yok.")

        with g2:
            st.subheader("🏆 Potansiyel Müşteriler (Top 5)")
            if not df_teklif.empty and "Musteri" in df_teklif.columns:
                top_musteri = df_teklif.groupby("Musteri")["Toplam Tutar"].sum().sort_values(ascending=False).head(5).reset_index()
                fig_bar = px.bar(top_musteri, x="Musteri", y="Toplam Tutar", text="Toplam Tutar", color="Toplam Tutar")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Veri yok.")

        # Son Hareketler Tablosu
        st.subheader("🕒 Son Eklenen Teklifler")
        st.dataframe(df_teklif.tail(5), use_container_width=True)

    # --- MODÜL 2: TEKLİF ROBOTU ---
    elif menu == "💰 Teklif Robotu":
        st.markdown("## 💰 Profesyonel Teklif Robotu")
        
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        ws_teklif = sh.worksheet("Teklifler")
        ws_ziyaret = sh.worksheet("Ziyaretler")
        
        df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
        df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
        
        # Müşteri Listesi
        musteri_listesi = ["➕ Yeni Müşteri Ekle"]
        mail_sozlugu = {}
        if not df_ziyaret.empty:
             df_ziyaret.columns = df_ziyaret.columns.str.strip()
             if "Firma Adı" in df_ziyaret.columns:
                 firmalar = [x for x in df_ziyaret["Firma Adı"].unique() if x]
                 firmalar.sort()
                 musteri_listesi += firmalar
                 for i, row in df_ziyaret.iterrows():
                    if row["Firma Adı"]: mail_sozlugu[row["Firma Adı"]] = str(row["E-Posta"])

        # Üst Panel
        with st.container():
            c1, c2, c3 = st.columns([2,1,1])
            with c1:
                secilen_musteri = st.selectbox("Müşteri Seçiniz", musteri_listesi, key="musteri_secim")
                if secilen_musteri == "➕ Yeni Müşteri Ekle":
                    final_musteri = st.text_input("Firma Ünvanı", key="yeni_musteri")
                    otomatik_mail = ""
                else:
                    final_musteri = secilen_musteri
                    otomatik_mail = mail_sozlugu.get(final_musteri, "")
            with c2:
                tarih = st.date_input("Tarih", datetime.today())
            with c3:
                para = st.selectbox("Döviz", ["TL", "USD", "EUR"], key="para_birimi")

        st.markdown("---")
        
        # Ürün Ekleme (Renkli Alan)
        with st.container(border=True):
            st.markdown("##### 🛒 Ürün Sepeti")
            c_u1, c_u2, c_u3, c_u4 = st.columns([3, 1, 1, 1])
            
            urunler = [""] + df_fiyat['Urun Adi'].tolist()
            secilen_urun = c_u1.selectbox("Ürün Listesi", urunler, key="urun_listesi")
            
            # Otomatik Fiyat Getirme
            oto_fiyat = 0.0
            if secilen_urun:
                try:
                    satir = df_fiyat[df_fiyat['Urun Adi'] == secilen_urun].iloc[0]
                    oto_fiyat = float(str(satir['Birim Fiyat']).replace(",", "."))
                except: pass
            
            manuel_ad = c_u1.text_input("Ürün Adı (Düzenlenebilir)", value=secilen_urun, key="urun_adi")
            adet = c_u2.number_input("Adet", min_value=1, value=1, key="adet")
            fiyat = c_u3.number_input("Birim Fiyat", value=oto_fiyat, format="%.2f", key="fiyat")
            
            if c_u4.button("Ekle ➕", use_container_width=True):
                st.session_state.sepet.append({"Urun": manuel_ad, "Adet": adet, "Birim Fiyat": fiyat, "Toplam": adet*fiyat})
                st.success("Eklendi")

        # Sepet Tablosu
        if st.session_state.sepet:
            st.table(pd.DataFrame(st.session_state.sepet))
            if st.button("Son Ekleneni Sil 🗑️"):
                st.session_state.sepet.pop()
                st.rerun()
            
            # Hesaplamalar
            toplam = sum(x['Toplam'] for x in st.session_state.sepet)
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                iskonto = st.number_input("İskonto (%)", 0, 100, 0)
                kdv = st.number_input("KDV (%)", 0, 100, 20)
            
            iskonto_tutari = toplam * (iskonto/100)
            kdv_tutari = (toplam - iskonto_tutari) * (kdv/100)
            genel_toplam = (toplam - iskonto_tutari) + kdv_tutari
            
            with col_h2:
                st.markdown(f"""
                <div style='text-align: right; background-color: #f0f2f6; padding: 15px; border-radius: 10px;'>
                    <p>Ara Toplam: <b>{toplam:,.2f}</b></p>
                    <p style='color:red'>İskonto: <b>-{iskonto_tutari:,.2f}</b></p>
                    <p>KDV: <b>{kdv_tutari:,.2f}</b></p>
                    <h3 style='color:#2e86de'>GENEL TOPLAM: {genel_toplam:,.2f} {para}</h3>
                </div>
                """, unsafe_allow_html=True)

            # Kaydet Butonları
            col_b1, col_b2 = st.columns([2,1])
            alic_mail = col_b1.text_input("Alıcı Mail", value=otomatik_mail)
            notlar = col_b1.text_area("Teklif Notu", "Ödeme peşin, stoktan teslim.")
            mail_gonder = col_b2.checkbox("Mail Gönder", value=True)
            
            if col_b2.button("✅ TEKLİFİ ONAYLA", type="primary", use_container_width=True):
                ozet = f"{len(st.session_state.sepet)} Çeşit Ürün"
                ws_teklif.append_row([str(tarih), final_musteri, ozet, 1, genel_toplam, genel_toplam, "Beklemede", para])
                st.toast("Teklif Başarıyla Kaydedildi!", icon="🎉")
                
                if mail_gonder and alic_mail:
                    html = olustur_profesyonel_teklif_maili(final_musteri, st.session_state.sepet, toplam, iskonto, iskonto_tutari, kdv, kdv_tutari, genel_toplam, para, notlar)
                    mail_gonder_generic(alic_mail, f"Fiyat Teklifi: {final_musteri}", html)
                    st.toast("Mail Gönderildi!", icon="📧")
                
                st.session_state.sepet = []
                # st.rerun() # İstersen temizledikten sonra yenile

    # --- MODÜL 3: ZİYARET GİRİŞİ ---
    elif menu == "📍 Ziyaret Girişi":
        st.markdown("## 📍 Saha Ziyaret Raporu")
        ws_ziyaret = sh.worksheet("Ziyaretler")
        
        with st.form("ziyaret_formu"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Ziyaret Tarihi")
            firma = c1.text_input("Firma Adı")
            kisi = c2.text_input("Görüşülen Yetkili")
            durum = c2.selectbox("Sonuç", ["Tanışma", "Teklif", "Sıcak Satış", "Red"])
            
            urunler = st.multiselect("İlgilenilen Ürünler", ["Rulman", "ZKL", "Kinex", "Kayış", "Hizmet"])
            notlar = st.text_area("Görüşme Notları")
            
            if st.form_submit_button("💾 Kaydet", type="primary"):
                ws_ziyaret.append_row([str(tarih), firma, "", kisi, "", "", durum, "", ", ".join(urunler), 0, "", "", "", "", notlar, str(datetime.now())])
                st.success("Ziyaret sisteme işlendi.")

    # --- MODÜL 4: ÜRÜN LİSTESİ ---
    elif menu == "📋 Ürün Listesi":
        st.markdown("## 📋 Fiyat Listesi Yönetimi")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        df = pd.DataFrame(ws_fiyat.get_all_records())
        st.dataframe(df, use_container_width=True)
        
        with st.expander("➕ Yeni Ürün Ekle"):
            c1, c2, c3 = st.columns(3)
            kod = c1.text_input("Kod")
            ad = c2.text_input("Ürün Adı")
            fiyat = c3.number_input("Fiyat", min_value=0.0)
            if st.button("Listeye Ekle"):
                ws_fiyat.append_row([kod, ad, fiyat, "TL"])
                st.success("Ürün eklendi!")
