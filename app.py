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

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Satış CRM Sistemi", page_icon="🏢", layout="wide")

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
        st.text_input("Kullanıcı Adı", key="username")
        st.text_input("Şifre", type="password", key="password")
        st.button("Giriş Yap", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Kullanıcı Adı", key="username")
        st.text_input("Şifre", type="password", key="password")
        st.button("Giriş Yap", on_click=password_entered)
        st.error("😕 Hatalı giriş.")
        return False
    else:
        return True

def get_google_sheet_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- MAIL ---
def mail_gonder_generic(alici_email, konu, html_icerik):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["server"]
        smtp_port = st.secrets["email"]["port"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Satis Departmani <{sender_email}>"
        msg['To'] = alici_email
        msg['Subject'] = konu
        msg.attach(MIMEText(html_icerik, 'html'))

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4 
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, alici_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail hatası: {e}")
        return False

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
      <body style="font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;">
        <div style="background-color: #fff; border: 1px solid #ddd; padding: 30px; max-width: 700px; margin: auto;">
            <h2 style="color: #2c3e50;">Fiyat Teklifi</h2>
            <p>Sayın <b>{musteri_adi}</b> Yetkilisi,</p>
            <p>Talep ettiğiniz ürünler için teklifimiz aşağıdadır.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background-color: #34495e; color: white;">
                    <th style="padding: 8px;">Ürün</th><th style="padding: 8px;">Miktar</th><th style="padding: 8px;">Birim Fiyat</th><th style="padding: 8px;">Tutar</th>
                </tr>
                {satirlar_html}
            </table>
            <div style="margin-top: 20px; text-align: right;">
                <p><b>Ara Toplam:</b> {ara_toplam:,.2f} {para_birimi}</p>
                <p style="color: red;"><b>İskonto (%{iskonto_orani}):</b> -{iskonto_tutari:,.2f} {para_birimi}</p>
                <p><b>KDV (%{kdv_orani}):</b> {kdv_tutari:,.2f} {para_birimi}</p>
                <h3 style="color: #2c3e50;">GENEL TOPLAM: {genel_toplam:,.2f} {para_birimi}</h3>
            </div>
            <hr>
            <p>Notlar: {notlar}</p>
        </div>
      </body>
    </html>
    """
    return html

# --- ANA UYGULAMA ---
if check_password():
    st.sidebar.title("CRM Menüsü")
    menu = st.sidebar.radio("Seçiniz:", ["👥 Müşteri Yönetimi", "📍 Ziyaret Girişi", "💰 Teklif Robotu", "📋 Fiyat Listesi", "📊 Patron Ekranı"])

    client = get_google_sheet_client()
    try:
        sh = client.open("Satis_Raporlari")
    except:
        st.error("Dosya bulunamadı.")
        st.stop()

    # --- 1. MODÜL: MÜŞTERİ YÖNETİMİ ---
    if menu == "👥 Müşteri Yönetimi":
        st.header("👥 Müşteri Kartı ve Listesi")
        ws_musteri = sh.worksheet("Musteriler")
        ws_ziyaret = sh.worksheet("Ziyaretler")

        tab1, tab2, tab3 = st.tabs(["➕ Yeni Müşteri Ekle", "📂 Müşteri Listesi & Analiz", "📥 Ziyaretlerden Aktar (B Seçeneği)"])

        with tab1:
            with st.form("musteri_kayit_formu", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    f_ad = st.text_input("Firma Adı (Zorunlu)")
                    f_yetkili = st.text_input("Yetkili Kişi")
                    f_tel = st.text_input("Telefon")
                    f_email = st.text_input("E-Posta Adresi")
                with c2:
                    f_sektor = st.selectbox("Sektör", ["Demir Çelik", "Makine İmalat", "Gıda", "Otomotiv", "Tekstil", "Madencilik", "Diğer"])
                    f_adres = st.text_area("Adres", height=100)
                    f_not = st.text_area("Özel Notlar")
                
                if st.form_submit_button("Müşteriyi Kaydet"):
                    if f_ad:
                        ws_musteri.append_row([str(datetime.today().date()), f_ad, f_yetkili, f_tel, f_email, f_sektor, f_adres, f_not])
                        st.success(f"✅ {f_ad} eklendi!")
                    else:
                        st.warning("Firma adı giriniz.")

        with tab2:
            data = ws_musteri.get_all_records()
            df_musteri = pd.DataFrame(data)
            if not df_musteri.empty:
                arama = st.text_input("🔍 Firma Ara")
                if arama:
                    df_musteri = df_musteri[df_musteri['Firma Adi'].str.contains(arama, case=False, na=False)]
                st.dataframe(df_musteri, use_container_width=True)
            else:
                st.info("Liste boş.")
        
        # --- B SEÇENEĞİ: ZİYARETLERDEN OTOMATİK AKTAR ---
        with tab3:
            st.subheader("📥 Eski Kayıtları İçeri Al")
            st.info("Bu özellik, 'Ziyaretler' sayfasındaki tüm firmaları tarar ve Müşteri Listesi'ne otomatik ekler.")
            
            if st.button("🚀 Ziyaretlerden Müşterileri Çek ve Kaydet"):
                try:
                    df_ziyaret = pd.DataFrame(ws_ziyaret.get_all_records())
                    df_musteri = pd.DataFrame(ws_musteri.get_all_records())
                    
                    if not df_ziyaret.empty:
                        # Ziyaretlerdeki benzersiz firmaları bul
                        if 'Firma Adı' in df_ziyaret.columns:
                            ziyaret_firmalari = df_ziyaret[['Firma Adı', 'E-Posta']].drop_duplicates(subset=['Firma Adı'])
                            
                            # Zaten kayıtlı olanları bul
                            kayitli_firmalar = []
                            if not df_musteri.empty and 'Firma Adi' in df_musteri.columns:
                                kayitli_firmalar = df_musteri['Firma Adi'].tolist()
                            
                            eklenen_sayisi = 0
                            for index, row in ziyaret_firmalari.iterrows():
                                firma_adi = row['Firma Adı']
                                email = row['E-Posta']
                                
                                # Eğer listede yoksa ekle
                                if firma_adi and firma_adi not in kayitli_firmalar:
                                    ws_musteri.append_row([
                                        str(datetime.today().date()), 
                                        firma_adi, 
                                        "", # Yetkili (Bilinmiyor)
                                        "", # Telefon
                                        email, 
                                        "Diğer", # Sektör
                                        "", # Adres
                                        "Otomatik aktarıldı"
                                    ])
                                    eklenen_sayisi += 1
                                    kayitli_firmalar.append(firma_adi)
                            
                            if eklenen_sayisi > 0:
                                st.success(f"🎉 {eklenen_sayisi} adet yeni firma Müşteri Listesi'ne eklendi!")
                            else:
                                st.warning("Yeni firma bulunamadı, hepsi zaten kayıtlı.")
                        else:
                            st.error("Ziyaretler sayfasında 'Firma Adı' sütunu bulunamadı.")
                except Exception as e:
                    st.error(f"Hata: {e}")

    # --- 2. MODÜL: ZİYARET GİRİŞİ ---
    elif menu == "📍 Ziyaret Girişi":
        st.header("📍 Ziyaret Girişi")
        ws_ziyaret = sh.worksheet("Ziyaretler")
        ws_musteri = sh.worksheet("Musteriler")
        
        df_m = pd.DataFrame(ws_musteri.get_all_records())
        musteri_listesi = df_m['Firma Adi'].tolist() if not df_m.empty and 'Firma Adi' in df_m.columns else []
        musteri_listesi.sort()
        musteri_listesi.insert(0, "") 

        with st.form("ziyaret_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                tarih = st.date_input("Tarih", datetime.today())
                firma_secim = st.selectbox("Firma Seçiniz", musteri_listesi)
                firma_manuel = st.text_input("Veya Yeni Firma Adı")
                firma = firma_manuel if firma_manuel else firma_secim
            
            with c2:
                kisi = st.text_input("Görüşülen Kişi")
                email_giriş = st.text_input("E-Posta")
            with c3:
                durum = st.selectbox("Durum", ["Tanışma", "Teklif", "Sıcak Satış", "Satış Kapandı"])
                urunler = st.multiselect("Ürünler", ["Rulman", "ZKL", "Kinex", "Sensimore", "Hizmet"])
                potansiyel = st.number_input("Potansiyel (TL)", step=1000)

            notlar = st.text_area("Notlar")
            mail_at = st.checkbox("Teşekkür Maili Gönder")
            
            if st.form_submit_button("Kaydet"):
                if firma:
                    ws_ziyaret.append_row([str(tarih), firma, "", kisi, "", email_giriş, durum, ", ".join(urunler), potansiyel, "", "", "", "", notlar, str(datetime.now())])
                    st.success("Kaydedildi.")
                    if mail_at and email_giriş:
                        mail_gonder_generic(email_giriş, f"Ziyaret Hk. - {firma}", f"Sayın {kisi}, ilginiz için teşekkürler.")
                        st.success("Mail gönderildi.")
                else:
                    st.warning("Firma seçiniz.")

    # --- 3. MODÜL: PROFESYONEL TEKLİF ---
    elif menu == "💰 Teklif Robotu":
        st.header("💰 Teklif Hazırla")
        try:
            ws_fiyat = sh.worksheet("Fiyat_Listesi")
            ws_teklif = sh.worksheet("Teklifler")
            ws_musteri = sh.worksheet("Musteriler")
            
            df_fiyat = pd.DataFrame(ws_fiyat.get_all_records())
            df_musteri = pd.DataFrame(ws_musteri.get_all_records())
            
            musteri_listesi = [""]
            mail_sozlugu = {}
            if not df_musteri.empty:
                df_musteri.columns = df_musteri.columns.str.strip()
                if 'Firma Adi' in df_musteri.columns:
                    musteri_listesi += df_musteri['Firma Adi'].tolist()
                    for i, row in df_musteri.iterrows():
                        mail_sozlugu[row['Firma Adi']] = str(row.get('E-Posta', ''))
        except:
            st.error("Veri okuma hatası.")
            st.stop()

        col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
        with col_m1:
            secilen_musteri = st.selectbox("Müşteri Seç", musteri_listesi)
            otomatik_mail = mail_sozlugu.get(secilen_musteri, "")
        with col_m2:
            tarih = st.date_input("Teklif Tarihi", datetime.today())
        with col_m3:
            para_birimi = st.selectbox("Para Birimi", ["TL", "USD", "EUR"])

        st.markdown("---")
        st.subheader("🛒 Ürün Ekle")
        
        c_u1, c_u2, c_u3, c_u4 = st.columns([3, 1, 1, 1])
        urun_liste = [""] + (df_fiyat['Urun Adi'].tolist() if not df_fiyat.empty else [])
        
        with c_u1:
            u_secim = st.selectbox("Ürün Seç", urun_liste)
            u_fiyat = 0.0
            if u_secim and not df_fiyat.empty:
                try:
                    satir = df_fiyat[df_fiyat['Urun Adi'] == u_secim].iloc[0]
                    u_fiyat = float(str(satir['Birim Fiyat']).replace(",","."))
                except: pass
            final_urun = st.text_input("Ürün Adı", value=u_secim if u_secim else "")
        
        with c_u2: adet = st.number_input("Adet", 1)
        with c_u3: b_fiyat = st.number_input("Birim Fiyat", value=u_fiyat)
        with c_u4:
            st.write("##")
            if st.button("➕ Ekle"):
                st.session_state.sepet.append({"Urun": final_urun, "Adet": adet, "Birim Fiyat": b_fiyat, "Toplam": adet*b_fiyat})

        if st.session_state.sepet:
            st.table(pd.DataFrame(st.session_state.sepet))
            if st.button("🗑️ Sepeti Temizle"):
                st.session_state.sepet = []
                st.rerun()

            st.subheader("Hesaplama")
            col_h1, col_h2 = st.columns(2)
            ara_toplam = sum(i['Toplam'] for i in st.session_state.sepet)
            with col_h1:
                iskonto = st.number_input("İskonto (%)", 0.0)
                kdv = st.number_input("KDV (%)", 20.0)
            
            i_tutar = ara_toplam * (iskonto/100)
            k_tutar = (ara_toplam - i_tutar) * (kdv/100)
            genel_toplam = (ara_toplam - i_tutar) + k_tutar
            
            with col_h2:
                st.metric("Genel Toplam", f"{genel_toplam:,.2f} {para_birimi}")

            alici_mail = st.text_input("Alıcı E-Posta", value=otomatik_mail)
            notlar = st.text_area("Notlar")
            mail_gonder = st.checkbox("Teklif Maili Gönder", value=True)

            if st.button("✅ Teklifi Kaydet", type="primary"):
                ozet = ", ".join([i['Urun'] for i in st.session_state.sepet])
                ws_teklif.append_row([str(tarih), secilen_musteri, ozet, "1", genel_toplam, genel_toplam, "Beklemede", para_birimi])
                st.success("Kaydedildi!")
                if mail_gonder and alici_mail:
                    html = olustur_profesyonel_teklif_maili(secilen_musteri, st.session_state.sepet, ara_toplam, iskonto, i_tutar, kdv, k_tutar, genel_toplam, para_birimi, notlar)
                    mail_gonder_generic(alici_mail, f"Teklif - {secilen_musteri}", html)
                    st.success("Mail Gönderildi!")
                    st.session_state.sepet = []

    # --- 4. MODÜL: FİYAT LİSTESİ ---
    elif menu == "📋 Fiyat Listesi":
        st.header("📋 Ürün Listesi")
        ws_fiyat = sh.worksheet("Fiyat_Listesi")
        st.dataframe(pd.DataFrame(ws_fiyat.get_all_records()), use_container_width=True)
        with st.expander("Yeni Ürün Ekle"):
            c1, c2, c3 = st.columns(3)
            uk = c1.text_input("Kod")
            ua = c2.text_input("Ad")
            uf = c3.number_input("Fiyat")
            if st.button("Ekle"):
                ws_fiyat.append_row([uk, ua, uf, "TL"])
                st.success("Eklendi.")

    # --- 5. MODÜL: DASHBOARD ---
    elif menu == "📊 Patron Ekranı":
        st.header("📊 Genel Durum")
        try:
            df_m = pd.DataFrame(sh.worksheet("Musteriler").get_all_records())
            df_t = pd.DataFrame(sh.worksheet("Teklifler").get_all_records())
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Müşteri", len(df_m))
            c2.metric("Verilen Teklif Sayısı", len(df_t))
            if not df_t.empty and 'Toplam Tutar' in df_t.columns:
                df_t['Toplam Tutar'] = pd.to_numeric(df_t['Toplam Tutar'], errors='coerce').fillna(0)
                c3.metric("Toplam Teklif Hacmi", f"{df_t['Toplam Tutar'].sum():,.0f}")
            if not df_m.empty and 'Sektor' in df_m.columns:
                st.subheader("Sektör Dağılımı")
                fig = px.pie(df_m, names='Sektor')
                st.plotly_chart(fig)
        except:
            st.info("Veri bekleniyor...")
